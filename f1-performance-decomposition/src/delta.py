"""The core artefact: a cumulative time-delta curve and its decomposition.

``delta(d) = t_A(d) - t_B(d)`` is the running time gap between the two drivers
as a function of distance round the lap. Its value at the finish line *is* the
total lap-time gap; its slope localises where the gap is being opened. Slicing
that curve into micro-sectors turns "0.3 s faster" into "0.12 s of it comes
from the braking zone into Turn 4".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


# --------------------------------------------------------------------------- #
# Per-driver time-at-distance
# --------------------------------------------------------------------------- #
def time_at_distance(resampled: pd.DataFrame, basis: str | None = None) -> np.ndarray:
    """Cumulative time (s) at each grid point for one resampled lap.

    Two valid bases (see REPORT.md §Method):

    * ``telemetry_time`` - the car's own measured ``Time`` channel, already on
      the grid. Preferred: it is a direct measurement, free of the numerical
      integration error that quantised speed introduces.
    * ``speed_integral`` - integrate ``1/v`` over distance. Independent of the
      timing beam, so it is the cross-check that the measured time is sane.
    """
    basis = basis or config.TIME_BASIS
    if basis == "telemetry_time":
        t = resampled["Time"].to_numpy(dtype=float)
        return t - t[0]
    if basis == "speed_integral":
        d = resampled["Distance"].to_numpy(dtype=float)
        v = resampled["Speed"].to_numpy(dtype=float) / 3.6   # km/h -> m/s
        v = np.clip(v, 1e-3, None)                            # guard standstill
        dt = np.diff(d) / (0.5 * (v[:-1] + v[1:]))            # trapezoid in 1/v
        return np.concatenate(([0.0], np.cumsum(dt)))
    raise ValueError(f"unknown time basis: {basis!r}")


def cumulative_delta(resampled_a: pd.DataFrame,
                     resampled_b: pd.DataFrame,
                     basis: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return (grid, delta) where delta = t_A - t_B on the shared grid."""
    grid = resampled_a["Distance"].to_numpy(dtype=float)
    ta = time_at_distance(resampled_a, basis)
    tb = time_at_distance(resampled_b, basis)
    return grid, ta - tb


# --------------------------------------------------------------------------- #
# Micro-sector segmentation
# --------------------------------------------------------------------------- #
def micro_sector_edges(grid: np.ndarray,
                       n_sectors: int | None = None,
                       corner_distances: np.ndarray | None = None) -> np.ndarray:
    """Boundary distances partitioning the lap into micro-sectors.

    If ``corner_distances`` are supplied (FastF1 circuit info), boundaries are
    placed at the *midpoints between consecutive corners* - so each sector
    brackets one corner and the braking/exit either side of it, which is how a
    driver actually experiences the lap. Otherwise we fall back to equal
    distance bins.
    """
    n_sectors = n_sectors or config.N_MICRO_SECTORS
    lap_length = float(grid[-1])

    if corner_distances is not None and config.SEGMENT_BY_CORNERS:
        cd = np.sort(np.asarray(corner_distances, dtype=float))
        cd = cd[(cd > 0) & (cd < lap_length)]
        if len(cd) >= 2:
            mids = 0.5 * (cd[:-1] + cd[1:])
            edges = np.concatenate(([0.0], mids, [lap_length]))
            return edges

    return np.linspace(0.0, lap_length, n_sectors + 1)


def _interp_delta_at(grid: np.ndarray, delta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.interp(x, grid, delta)


def decompose(grid: np.ndarray,
              delta: np.ndarray,
              edges: np.ndarray) -> pd.DataFrame:
    """Time contributed by each micro-sector = change in delta across it.

    The contributions sum exactly to the endpoint of the curve (telescoping),
    which is the invariant the reconciliation test leans on.
    """
    d_at_edges = _interp_delta_at(grid, delta, edges)
    contrib = np.diff(d_at_edges)
    return pd.DataFrame({
        "sector": np.arange(1, len(contrib) + 1),
        "start_m": edges[:-1],
        "end_m": edges[1:],
        "mid_m": 0.5 * (edges[:-1] + edges[1:]),
        "delta_s": contrib,          # +ve => driver A slower here (B faster)
    })


def segment_times(resampled: pd.DataFrame,
                  edges: np.ndarray,
                  basis: str | None = None) -> np.ndarray:
    """Time spent in each micro-sector for one lap (used by the bootstrap)."""
    grid = resampled["Distance"].to_numpy(dtype=float)
    t = time_at_distance(resampled, basis)
    t_at_edges = np.interp(edges, grid, t)
    return np.diff(t_at_edges)


# --------------------------------------------------------------------------- #
# Reconciliation
# --------------------------------------------------------------------------- #
def reconcile(delta_endpoint: float,
              official_gap: float,
              tolerance: float | None = None) -> tuple[bool, float]:
    """Check the curve's finish-line value against the official lap-time gap.

    Returns (ok, residual). A failure means the time basis is wrong, not that
    one driver got faster - it is a correctness gate, not a finding.
    """
    tolerance = tolerance if tolerance is not None else config.RECONCILE_TOLERANCE_S
    residual = float(delta_endpoint - official_gap)
    return abs(residual) <= tolerance, residual


def reconcile_driver(resampled_lap: pd.DataFrame,
                     official_lap_time: float,
                     tolerance: float | None = None) -> tuple[bool, float]:
    """Per-driver gate: the lap's own measured telemetry time at its own finish
    must match its own official lap time. Independent of the other driver, so the
    grid-truncation tail does not enter the residual."""
    tol = config.RECONCILE_TOLERANCE_S if tolerance is None else tolerance
    t = time_at_distance(resampled_lap)
    resid = float(t[-1] - official_lap_time)
    return abs(resid) <= tol, resid
