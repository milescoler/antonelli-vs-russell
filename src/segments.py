"""
Circuit segmentation and per-segment time-delta computation.
"""

# Imports
import numpy as np
import pandas as pd

# Constants
DEFAULT_GRID_STEP_M = 5.0
DEFAULT_CORNER_GROUP_THRESHOLD_M = 250.0
MIN_STRAIGHT_LENGTH_M = 100.0


def resample_to_distance_grid(
    telemetry: pd.DataFrame,
    step_m: float = DEFAULT_GRID_STEP_M,
    channels: list = None,
) -> pd.DataFrame:
    """
    Resample lap telemetry from time-indexed to a uniform distance grid.

    Args:
        telemetry: DataFrame from FastF1's get_telemetry(), with a Distance column.
        step_m: distance grid spacing in meters.
        channels: which columns to interpolate. Defaults to Speed, Time, Throttle, Brake, X, Y.
            Time is converted to seconds-as-float before interpolation so the output
            DataFrame has a float Time column (not a Timedelta).

    Returns:
        DataFrame with uniform Distance column and interpolated channels.
    """
    if channels is None:
        channels = ['Speed', 'Time', 'Throttle', 'Brake', 'X', 'Y']

    telem_clean = telemetry.sort_values('Distance').drop_duplicates(subset='Distance')
    telem_clean = telem_clean[telem_clean['Distance'] >= 0]
    target_distance = np.arange(0, telem_clean['Distance'].max(), step_m)
    out = {'Distance': target_distance}

    for channel in channels:
        if channel not in telem_clean.columns:
            continue
        source = telem_clean[channel]
        if channel == 'Time':
            source_values = source.dt.total_seconds().values
        else:
            source_values = source.values
        out[channel] = np.interp(target_distance, telem_clean['Distance'].values, source_values)

    return pd.DataFrame(out)

def build_segments_from_corners(
    circuit_info,
    lap_distance_m: float,
    threshold_m: float = DEFAULT_CORNER_GROUP_THRESHOLD_M,
) -> pd.DataFrame:
    """
    Build a DataFrame of track segments by clustering corners and filling the
    straights between them.

    Args:
        circuit_info: FastF1 CircuitInfo object (has a `corners` DataFrame with
            a `Distance` column).
        lap_distance_m: Total lap distance in meters.
        threshold_m: Corners within this distance of each other are merged into
            a single segment.

    Returns:
        DataFrame with columns:
          - Segment: label (e.g. 'C1', 'S2')
          - start_m, end_m: segment bounds in meters
          - kind: 'corner' or 'straight'
        Sorted by start_m.
    """
    corners = circuit_info.corners.sort_values('Distance').reset_index(drop=True)
    groups = []
    current_group = [corners.iloc[0]['Distance']]

    for row in corners.iloc[1:].itertuples():
        d = row.Distance
        if (d - current_group[-1]) <= threshold_m:
            current_group.append(d)
        else:
            groups.append(current_group)
            current_group = [d]
    groups.append(current_group)
    
    rows = []
    for (i, group) in enumerate(groups):
        seg_start = max(0, min(group) - 50)
        seg_end = min(lap_distance_m, max(group) + 50)

        rows.append({
            'Segment': f'C{i+1}',
            'start_m': seg_start,
            'end_m': seg_end,
            'kind': 'corner'
        })
    
    corner_rows = sorted(rows, key=lambda r: r['start_m'])

    prev_end = 0.0
    straight_counter = 1
    straight_rows = []

    for corner in corner_rows:
        if corner['start_m'] - prev_end > MIN_STRAIGHT_LENGTH_M:
            straight_rows.append({
                'Segment': f'S{straight_counter}',
                'start_m': prev_end,
                'end_m': corner['start_m'],
                'kind': 'straight'
            })
            straight_counter += 1
        prev_end = corner['end_m']

    if lap_distance_m - prev_end > MIN_STRAIGHT_LENGTH_M:
        straight_rows.append({
            'Segment': f'S{straight_counter}',
            'start_m': prev_end,
            'end_m': lap_distance_m,
            'kind': 'straight'
        })

    combined_rows = corner_rows + straight_rows
    segments_df = pd.DataFrame(combined_rows)
    segments_df = segments_df.sort_values('start_m').reset_index(drop=True)
    return segments_df


def compute_segment_times(
    telem_resampled: pd.DataFrame,
    segments: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute per-segment time and min-speed from resampled telemetry.

    Uses the telemetry's Time channel directly: per-segment time is
    Time[last_step_in_segment] - Time[first_step_in_segment]. This avoids
    the accumulated error of integrating speed over distance.

    Args:
        telem_resampled: output of resample_to_distance_grid; must have
            Distance (meters), Speed (kph), and Time (seconds as float —
            resample_to_distance_grid converts Timedelta -> seconds for us).
        segments: output of build_segments_from_corners; must have
            Segment, start_m, end_m, kind.

    Returns:
        The input `segments` frame with two added columns:
          - min_speed (kph): min of Speed within [start_m, end_m).
          - time_s (seconds): Time[end] - Time[start] over the grid steps in segment.
        If a segment has fewer than 2 grid steps inside it, time_s is set to 0.0
        and min_speed to NaN.
    """
    distance = telem_resampled['Distance'].values
    speed_kph = telem_resampled['Speed'].values
    time_s = telem_resampled['Time'].values

    min_speeds = []
    times = []
    for row in segments.itertuples():
        mask = (distance >= row.start_m) & (distance < row.end_m)
        if mask.sum() < 2:
            min_speeds.append(float('nan'))
            times.append(0.0)
            continue
        seg_time_values = time_s[mask]
        min_speeds.append(float(speed_kph[mask].min()))
        times.append(float(seg_time_values[-1] - seg_time_values[0]))

    out = segments.copy()
    out['min_speed'] = min_speeds
    out['time_s'] = times
    return out


def compute_segment_deltas(
    times_a: pd.DataFrame,
    times_b: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute per-segment time delta between two drivers.

    Args:
        times_a: output of compute_segment_times for driver A.
        times_b: output of compute_segment_times for driver B.
            Both must have the same Segment values in the same order.

    Returns:
        DataFrame with columns:
          Segment, kind, start_m, end_m, min_speed, time_a_s, time_b_s, delta_s
        where:
          - min_speed = elementwise min(times_a.min_speed, times_b.min_speed)
            (the deeper of the two; used for category classification).
          - delta_s = time_b_s - time_a_s.
            POSITIVE = driver A faster than driver B.
    """
    if not (times_a['Segment'].values == times_b['Segment'].values).all():
        raise ValueError("times_a and times_b must have identical Segment ordering")

    out = times_a[['Segment', 'kind', 'start_m', 'end_m']].copy()
    out['min_speed'] = np.minimum(times_a['min_speed'].values, times_b['min_speed'].values)
    out['time_a_s'] = times_a['time_s'].values
    out['time_b_s'] = times_b['time_s'].values
    out['delta_s'] = out['time_b_s'] - out['time_a_s']
    return out
