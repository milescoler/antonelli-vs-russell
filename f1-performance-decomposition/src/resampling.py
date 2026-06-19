"""Resample irregular telemetry onto a common distance grid.

WHY this is the foundation of the whole analysis: the two cars are sampled at
different instants and travel the lap at different speeds, so you cannot line
their samples up in time or by index. The only physically meaningful basis for
"are they doing the same thing here?" is *position on track*. We therefore put
every channel of every lap on one shared distance grid (every
``GRID_RESOLUTION_M`` metres) by linear interpolation. After this step the two
drivers are described at identical points on the circuit, which is the sole
valid footing for a point-by-point comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from src.data_loading import Lap, TELEMETRY_CHANNELS


def build_distance_grid(lap_length: float, resolution: float | None = None) -> np.ndarray:
    """Fixed 0..lap_length grid, inclusive of both ends.

    Endpoints are pinned exactly so the cumulative time at the finish line is
    read at the true lap length, not an interpolated near-miss.
    """
    resolution = resolution or config.GRID_RESOLUTION_M
    n = int(np.floor(lap_length / resolution)) + 1
    grid = np.linspace(0.0, lap_length, n)
    return grid


def resample_lap(lap: Lap, grid: np.ndarray) -> pd.DataFrame:
    """Interpolate one lap's channels onto ``grid``.

    Distance is forced monotone first (telemetry occasionally backs up a few
    cm), then every channel is linearly interpolated. Linear interpolation is
    deliberate: it is shape-preserving and introduces no spurious oscillation
    the way a spline would, and the grid is fine enough that curvature between
    knots is negligible.
    """
    tel = lap.telemetry
    d = tel["Distance"].to_numpy(dtype=float)
    # Enforce strict monotonicity for np.interp (drop the rare backward steps).
    keep = np.concatenate(([True], np.diff(d) > 0))
    d = d[keep]

    out = {"Distance": grid}
    for ch in TELEMETRY_CHANNELS:
        if ch == "Distance":
            continue
        y = tel[ch].to_numpy(dtype=float)[keep]
        out[ch] = np.interp(grid, d, y)
    return pd.DataFrame(out)


def resample_driver(laps: list[Lap], grid: np.ndarray) -> list[pd.DataFrame]:
    """Resample every lap of a driver onto the shared grid."""
    return [resample_lap(lp, grid) for lp in laps]


def common_grid(lap_a: Lap, lap_b: Lap, resolution: float | None = None) -> np.ndarray:
    """Build one grid both drivers share.

    We use the *shorter* measured lap length as the common finish so neither
    driver is extrapolated past their own data; the tiny tail difference
    (metres of GPS/lap-marker jitter) is immaterial to the corner-level story.
    """
    lap_length = min(lap_a.lap_length, lap_b.lap_length)
    return build_distance_grid(lap_length, resolution)
