"""
Teammate comparison orchestration: ties loaders + segments together and adds
the interpretive layer (segment categories, Q-session derivation, metadata).
"""

from __future__ import annotations
from typing import Optional

import pandas as pd

from src.loaders import (
    load_qualifying_session,
    get_fastest_valid_lap,
    get_lap_telemetry,
)
from src.segments import (
    resample_to_distance_grid,
    build_segments_from_corners,
    compute_segment_times,
    compute_segment_deltas,
)

SLOW_CORNER_MAX_KPH = 130.0
FAST_CORNER_MIN_KPH = 200.0

# Sensor-freeze detection. Two failure modes are guarded against:
#   1. Stuck Speed channel — the sensor reports only a handful of unique values
#      across many samples. Detected with a sliding 20-sample window so the
#      check fires even when a segment has a healthy entry and only the
#      latter portion is frozen.
#   2. Truncated telemetry — the driver's reported `Distance.max()` falls short
#      of the segment's `end_m` by more than EDGE_TOL_M. The segment-time
#      computation then sees only a fraction of the segment, producing wildly
#      distorted per-segment deltas.
# In both cases, lap-level and sector-level time deltas remain valid because
# they come from FastF1's `Time` channel and timing-line measurements, which
# are independent of the car telemetry.
SENSOR_FREEZE_WINDOW = 50
SENSOR_FREEZE_MAX_UNIQUE = 5
SENSOR_FREEZE_MIN_DISTANCE_M = 300.0
SENSOR_FREEZE_EDGE_TOL_M = 50.0


def _find_freeze_distance_ranges(tel: pd.DataFrame) -> list:
    """Return (start_d, end_d) ranges where Speed shows <= 5 unique values
    across any 50-sample window, AND the contiguous flagged region spans
    >= 300 m of distance. The distance gate prevents false positives at
    natural slow-corner apexes and at top-speed cruising sections, where
    speed can be locally near-constant but only over short distances."""
    speed = tel['Speed'].values
    distance = tel['Distance'].values
    n = len(speed)
    if n < SENSOR_FREEZE_WINDOW:
        return []
    frozen_idx = set()
    for i in range(n - SENSOR_FREEZE_WINDOW + 1):
        if pd.Series(speed[i:i + SENSOR_FREEZE_WINDOW]).nunique() <= SENSOR_FREEZE_MAX_UNIQUE:
            frozen_idx.update(range(i, i + SENSOR_FREEZE_WINDOW))
    if not frozen_idx:
        return []
    sorted_idx = sorted(frozen_idx)
    ranges = []
    start = sorted_idx[0]
    prev = sorted_idx[0]
    for i in sorted_idx[1:]:
        if i - prev > 1:
            if distance[prev] - distance[start] >= SENSOR_FREEZE_MIN_DISTANCE_M:
                ranges.append((float(distance[start]), float(distance[prev])))
            start = i
        prev = i
    if distance[prev] - distance[start] >= SENSOR_FREEZE_MIN_DISTANCE_M:
        ranges.append((float(distance[start]), float(distance[prev])))
    return ranges


def _detect_sensor_freeze(tel: pd.DataFrame, segments: pd.DataFrame) -> list:
    """Per-segment: True if this driver's telemetry looks usable in that
    segment, False if either the sensor is frozen or the segment extends
    past the driver's reported telemetry distance."""
    max_d = float(tel['Distance'].max())
    freeze_ranges = _find_freeze_distance_ranges(tel)
    flags = []
    for row in segments.itertuples():
        if row.end_m > max_d + SENSOR_FREEZE_EDGE_TOL_M:
            flags.append(False)
            continue
        overlaps_freeze = any(
            row.start_m < fr_end and row.end_m > fr_start
            for fr_start, fr_end in freeze_ranges
        )
        flags.append(not overlaps_freeze)
    return flags


def _derive_q_session(session, lap) -> Optional[int]:
    """
    Determine which Q-segment (1, 2, or 3) a given lap belongs to.

    Strategy:
      1. Preferred: use session.session_status to find the 'Started' transitions
         for each Q-segment and bucket lap.LapStartTime accordingly.
      2. Fallback: cluster all drivers' LapStartTimes and split on the two
         largest gaps (the Q1->Q2 and Q2->Q3 breaks).

    Returns:
        1, 2, or 3 if derivation succeeds; None if neither strategy works.
    """
    lap_start = lap.get('LapStartTime')
    if pd.isna(lap_start):
        return None

    # Strategy 1: session.session_status transitions.
    try:
        status = session.session_status
        if status is not None and len(status) > 0 and 'Status' in status.columns:
            starts = status[status['Status'].astype(str).str.lower().eq('started')]
            if len(starts) >= 3:
                boundaries = sorted(starts['Time'].iloc[:3].tolist())
                # boundaries[0] = Q1 start, [1] = Q2 start, [2] = Q3 start
                if lap_start >= boundaries[2]:
                    return 3
                if lap_start >= boundaries[1]:
                    return 2
                if lap_start >= boundaries[0]:
                    return 1
    except Exception:
        pass

    # Strategy 2: cluster all lap start times, split on the two biggest gaps.
    try:
        all_starts = session.laps['LapStartTime'].dropna().sort_values().tolist()
        if len(all_starts) < 3:
            return None
        gaps = [(all_starts[i+1] - all_starts[i], i) for i in range(len(all_starts)-1)]
        gaps.sort(reverse=True, key=lambda x: x[0])
        # Two biggest gaps mark Q1->Q2 and Q2->Q3 boundaries.
        cut_idxs = sorted(idx for _, idx in gaps[:2])
        q2_start = all_starts[cut_idxs[0] + 1]
        q3_start = all_starts[cut_idxs[1] + 1]
        if lap_start >= q3_start:
            return 3
        if lap_start >= q2_start:
            return 2
        return 1
    except Exception:
        return None


def _classify_segment(kind: str, min_speed: float) -> str:
    """Map (kind, min_speed) -> category. See spec §4 for thresholds."""
    if kind == 'straight':
        return 'straight'
    if pd.isna(min_speed):
        return 'unknown'
    if min_speed < SLOW_CORNER_MAX_KPH:
        return 'slow_corner'
    if min_speed < FAST_CORNER_MIN_KPH:
        return 'medium_corner'
    return 'fast_corner'


def compare_teammates(
    year: int,
    round_or_name,
    drv_a: str = 'ANT',
    drv_b: str = 'RUS',
    threshold_m: float = 250.0,
) -> dict:
    """
    End-to-end teammate comparison for one qualifying session.

    Returns:
        {
          "segments": DataFrame with columns
              [Segment, kind, start_m, end_m, min_speed,
               time_a_s, time_b_s, delta_s, category],
          "meta": {
              "year", "round", "event_name",
              "lap_time_a_s", "lap_time_b_s", "lap_delta_s",
              "q_session_a", "q_session_b", "q_mismatch",
          },
        }

    Sign convention: delta_s = time_b_s - time_a_s, so POSITIVE = drv_a faster.

    Category thresholds (fixed, not per-circuit):
      slow_corner   < 130 kph min_speed
      medium_corner   130–200 kph min_speed
      fast_corner  >= 200 kph min_speed
      straight      regardless of speed
    """
    session = load_qualifying_session(year, round_or_name)
    lap_a = get_fastest_valid_lap(session, drv_a)
    lap_b = get_fastest_valid_lap(session, drv_b)
    tel_a = get_lap_telemetry(lap_a)
    tel_b = get_lap_telemetry(lap_b)

    # Shared segments built from circuit info; use the longer of the two
    # telemetry distances as the lap length.
    lap_distance_m = max(tel_a['Distance'].max(), tel_b['Distance'].max())
    segs = build_segments_from_corners(
        session.get_circuit_info(),
        lap_distance_m=lap_distance_m,
        threshold_m=threshold_m,
    )

    resampled_a = resample_to_distance_grid(tel_a)
    resampled_b = resample_to_distance_grid(tel_b)
    times_a = compute_segment_times(resampled_a, segs)
    times_b = compute_segment_times(resampled_b, segs)
    deltas = compute_segment_deltas(times_a, times_b)
    deltas['category'] = [
        _classify_segment(k, m) for k, m in zip(deltas['kind'], deltas['min_speed'])
    ]

    # Flag segments where either driver's speed sensor looks frozen — in those
    # segments min_speed is unreliable and the category label may be wrong
    # (the time delta itself is still reliable, since Time is independent).
    ok_a = _detect_sensor_freeze(tel_a, deltas)
    ok_b = _detect_sensor_freeze(tel_b, deltas)
    deltas['sensor_ok'] = [a and b for a, b in zip(ok_a, ok_b)]

    q_a = _derive_q_session(session, lap_a)
    q_b = _derive_q_session(session, lap_b)
    q_mismatch = (q_a is not None) and (q_b is not None) and (q_a != q_b)

    lap_time_a_s = lap_a['LapTime'].total_seconds()
    lap_time_b_s = lap_b['LapTime'].total_seconds()

    meta = {
        'year': year,
        'round': int(session.event['RoundNumber']),
        'event_name': str(session.event['EventName']),
        'lap_time_a_s': lap_time_a_s,
        'lap_time_b_s': lap_time_b_s,
        'lap_delta_s': lap_time_b_s - lap_time_a_s,
        'q_session_a': q_a,
        'q_session_b': q_b,
        'q_mismatch': q_mismatch,
    }
    return {'segments': deltas, 'meta': meta}
