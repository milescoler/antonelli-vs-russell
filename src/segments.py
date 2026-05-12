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
        channels: which columns to interpolate. Defaults to Speed, Throttle, Brake, X, Y.

    Returns:
        DataFrame with uniform Distance column and interpolated channels.
    """
    # Handle default channels list if None
    if channels is None:
        channels = ['Speed', 'Throttle', 'Brake', 'X', 'Y']
    
    # Sort by distance and drop duplicates
    telem_clean = telemetry.sort_values('Distance').drop_duplicates(subset='Distance')
    target_distance = np.arange(0, telem_clean['Distance'].max(), step_m)
    out = {'Distance': target_distance}
    
    for channel in channels:
        if channel not in telem_clean.columns:
            continue
        out[channel] = np.interp(target_distance, telem_clean['Distance'].values, telem_clean[channel].values)
    
    return pd.DataFrame(out)

def build_segments_from_corners(
    circuit_info,
    lap_distance_m: float,
    threshold_m: float = DEFAULT_CORNER_GROUP_THRESHOLD_M,
) -> pd.DataFrame:
    """
    Build a DataFrame of track segments based on corner locations and distances.

    Args:
        circuit_info: DataFrame with 'Position' and 'Compound' columns.
        lap_distance_m: Total lap distance in meters.
        threshold_m: Distance threshold for grouping corners into segments.

    Returns:
        DataFrame with 'Start', 'End', and 'Compound' columns.
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
    step_m: float = DEFAULT_GRID_STEP_M,
) -> pd.DataFrame:
    """
    Compute per-segment time and min-speed from resampled telemetry.

    Args:
        telem_resampled: output of resample_to_distance_grid; must have
            Distance (meters), Speed (kph).
        segments: output of build_segments_from_corners; must have
            Segment, start_m, end_m, kind.
        step_m: distance grid step in meters; must match the step used when
            resampling.

    Returns:
        The input `segments` frame with two added columns:
          - min_speed (kph): min of Speed within [start_m, end_m).
          - time_s (seconds): sum of (step_m / speed_m_per_s) within [start_m, end_m).
    """
    speed_m_per_s = telem_resampled['Speed'].values * (1000.0 / 3600.0)
    distance = telem_resampled['Distance'].values

    min_speeds = []
    times = []
    for row in segments.itertuples():
        mask = (distance >= row.start_m) & (distance < row.end_m)
        seg_speed_kph = telem_resampled['Speed'].values[mask]
        seg_speed_mps = speed_m_per_s[mask]
        if len(seg_speed_mps) == 0:
            min_speeds.append(float('nan'))
            times.append(0.0)
            continue
        min_speeds.append(float(seg_speed_kph.min()))
        times.append(float((step_m / seg_speed_mps).sum()))

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
