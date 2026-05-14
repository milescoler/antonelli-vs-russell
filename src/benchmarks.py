"""
Teammate comparison orchestration: ties loaders + segments together and adds
the interpretive layer (segment categories, Q-session derivation, metadata).
"""

from __future__ import annotations
from typing import Optional

import numpy as np
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

# Corner-signature analysis (apex speed + brake / throttle timing).
BRAKE_LOOKBACK_M = 250.0
THROTTLE_LOOKAHEAD_M = 250.0
THROTTLE_FULL_PCT = 99.0

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


def _corner_brake_throttle(tel: pd.DataFrame, corner_distance: float) -> tuple:
    """For one corner at `corner_distance` (meters), return
    (brake_on_distance, throttle_full_distance) for this driver:

      brake_on_distance: how many meters BEFORE the apex this driver started
        braking. Larger = brakes earlier; smaller = brakes later.
      throttle_full_distance: how many meters AFTER the apex this driver
        first reaches THROTTLE_FULL_PCT (99%). Larger = slower to full
        throttle; smaller = back on it sooner.

    Returns NaN values if there isn't enough telemetry in the lookback /
    lookahead window for a meaningful read. Returns 0.0 for brake_on if
    no braking is detected within the window (a flat-out corner).
    """
    d = tel['Distance'].values
    brake = tel['Brake'].values
    throttle = tel['Throttle'].values
    is_brake = brake.astype(float) > 0

    back_mask = (d < corner_distance) & (d > corner_distance - BRAKE_LOOKBACK_M)
    if back_mask.sum() < 5:
        brake_on = float('nan')
    else:
        on_idx = np.where(is_brake[back_mask])[0]
        brake_on = 0.0 if len(on_idx) == 0 else corner_distance - d[back_mask][on_idx[0]]

    fwd_mask = (d >= corner_distance) & (d < corner_distance + THROTTLE_LOOKAHEAD_M)
    if fwd_mask.sum() < 5:
        throttle_full = float('nan')
    else:
        full_idx = np.where(throttle[fwd_mask] >= THROTTLE_FULL_PCT)[0]
        if len(full_idx) == 0:
            throttle_full = THROTTLE_LOOKAHEAD_M
        else:
            throttle_full = d[fwd_mask][full_idx[0]] - corner_distance

    return brake_on, throttle_full


def compute_corner_signatures(
    year: int,
    round_or_name,
    drv_a: str = 'ANT',
    drv_b: str = 'RUS',
) -> pd.DataFrame:
    """For each circuit-info corner in a qualifying session, compute:

      - mean apex speed (kph) across the two drivers, plus per-driver apex speeds
      - apex_delta_kph = ANT_apex - RUS_apex (positive = ANT carries more speed)
      - brake_on_a, brake_on_b: meters before apex where each driver started braking
      - brake_on_delta = ANT - RUS  (NEGATIVE = ANT brakes LATER)
      - throttle_full_a, throttle_full_b: meters after apex to reach 99% throttle
      - throttle_full_delta = ANT - RUS  (NEGATIVE = ANT to full throttle SOONER)
      - sensor_ok: True if neither driver's telemetry is freeze-flagged at this
        corner's apex Distance (and the corner is within both drivers' max distance)

    Returns one DataFrame row per corner.
    """
    session = load_qualifying_session(year, round_or_name)
    lap_a = get_fastest_valid_lap(session, drv_a)
    lap_b = get_fastest_valid_lap(session, drv_b)
    tel_a = get_lap_telemetry(lap_a).sort_values('Distance').drop_duplicates(subset='Distance')
    tel_b = get_lap_telemetry(lap_b).sort_values('Distance').drop_duplicates(subset='Distance')
    freeze_a = _find_freeze_distance_ranges(tel_a)
    freeze_b = _find_freeze_distance_ranges(tel_b)
    corners = session.get_circuit_info().corners

    max_d_a = float(tel_a['Distance'].max())
    max_d_b = float(tel_b['Distance'].max())

    rows = []
    for c in corners.itertuples():
        d = float(c.Distance)
        in_range = (d <= max_d_a) and (d <= max_d_b)
        in_freeze = (
            any(fs <= d <= fe for fs, fe in freeze_a) or
            any(fs <= d <= fe for fs, fe in freeze_b)
        )
        sensor_ok = in_range and not in_freeze

        sp_a = float(np.interp(d, tel_a['Distance'], tel_a['Speed']))
        sp_b = float(np.interp(d, tel_b['Distance'], tel_b['Speed']))
        b_on_a, t_full_a = _corner_brake_throttle(tel_a, d)
        b_on_b, t_full_b = _corner_brake_throttle(tel_b, d)

        letter = c.Letter if isinstance(c.Letter, str) and c.Letter.strip() else ''
        rows.append({
            'race': str(session.event['EventName']),
            'corner': f'T{c.Number}{letter}',
            'distance_m': d,
            'apex_a_kph': sp_a,
            'apex_b_kph': sp_b,
            'mean_apex_kph': (sp_a + sp_b) / 2.0,
            'apex_delta_kph': sp_a - sp_b,
            'brake_on_a': b_on_a,
            'brake_on_b': b_on_b,
            'brake_on_delta': (b_on_a - b_on_b) if not (np.isnan(b_on_a) or np.isnan(b_on_b)) else float('nan'),
            'throttle_full_a': t_full_a,
            'throttle_full_b': t_full_b,
            'throttle_full_delta': (t_full_a - t_full_b) if not (np.isnan(t_full_a) or np.isnan(t_full_b)) else float('nan'),
            'sensor_ok': sensor_ok,
        })

    return pd.DataFrame(rows)
