"""Synthetic telemetry fixtures - the offline / CI substitute for FastF1.

This module fabricates two drivers' laps with a *known* ground truth: a few
micro-sectors carry a real, repeatable advantage for one driver, the rest carry
only lap-to-lap noise. That lets the test-suite assert two things without a
network connection:

  1. the cumulative-delta curve reconciles with the (synthetic) official gap;
  2. the bootstrap flags the planted-signal sectors as significant and the
     noise-only sectors as not.

It returns exactly the ``DriverLaps`` / ``Lap`` structures that
``data_loading`` produces from real FastF1 data, so the rest of the pipeline
cannot tell the difference. The time channel is built by integrating 1/speed,
so the two time bases agree and reconciliation is exact by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_loading import Lap, DriverLaps, TELEMETRY_CHANNELS

LAP_LENGTH = 5000.0          # metres
V_MAX = 320.0                # km/h on the straights

# (centre_m, apex_speed_kmh, width_m) for a dozen corners.
_CORNERS = [
    (450, 110, 70), (900, 90, 60), (1350, 200, 90), (1850, 75, 55),
    (2350, 150, 80), (2750, 95, 60), (3200, 230, 100), (3650, 120, 70),
    (4050, 85, 55), (4400, 170, 85), (4750, 100, 60),
]

# Corners where driver A genuinely has the edge (carries more apex speed).
# These should come back flagged "significant"; everything else "noise".
_SIGNAL_CORNERS = {1, 6, 8}      # indices into _CORNERS
_SIGNAL_GAIN_KMH = 10.0          # apex-speed advantage planted for driver A


def corner_distances() -> np.ndarray:
    return np.array([c[0] for c in _CORNERS], dtype=float)


def _speed_profile(apex_offsets: np.ndarray) -> "tuple[np.ndarray, np.ndarray]":
    """Fine-grid (distance, speed) for one lap given per-corner apex offsets."""
    d = np.arange(0.0, LAP_LENGTH + 0.5, 0.5)
    v = np.full_like(d, V_MAX)
    for (c, apex, w), off in zip(_CORNERS, apex_offsets):
        dip = (V_MAX - (apex + off)) * np.exp(-(((d - c) / w) ** 2))
        v = v - dip
    return d, np.clip(v, 40.0, V_MAX)


def _derive_channels(d: np.ndarray, v: np.ndarray) -> dict:
    """Throttle / brake / gear / position derived from the speed trace."""
    dvdd = np.gradient(v, d)
    brake = (dvdd < -0.05).astype(float)
    throttle = np.where(dvdd >= -0.005, 100.0, 0.0)
    # Coast (small negative slope, not braking) -> partial throttle.
    coast = (dvdd < -0.005) & (dvdd >= -0.05)
    throttle[coast] = 40.0
    gear = np.clip(np.round(np.interp(v, [40, V_MAX], [1, 8])), 1, 8)
    theta = 2 * np.pi * d / LAP_LENGTH
    x = 1000 * np.cos(theta) * (1 + 0.15 * np.sin(3 * theta))
    y = 1000 * np.sin(theta) * (1 + 0.15 * np.sin(3 * theta))
    return {"Throttle": throttle, "Brake": brake, "nGear": gear, "X": x, "Y": y}


def _make_lap(driver: str, lap_number: int, apex_offsets: np.ndarray,
              sample_hz: float = 10.0) -> Lap:
    """Build one Lap, time-sampled (hence irregular in distance) like real data."""
    d_fine, v_fine = _speed_profile(apex_offsets)
    v_ms = v_fine / 3.6
    # Cumulative time by integrating 1/v over distance (trapezoid).
    dt = np.diff(d_fine) / (0.5 * (v_ms[:-1] + v_ms[1:]))
    t_fine = np.concatenate(([0.0], np.cumsum(dt)))
    total_t = float(t_fine[-1])

    chans = _derive_channels(d_fine, v_fine)

    # Sample at a fixed rate in *time* -> samples land irregularly in distance.
    t_samples = np.arange(0.0, total_t, 1.0 / sample_hz)
    d_s = np.interp(t_samples, t_fine, d_fine)
    tel = pd.DataFrame({
        "Distance": d_s,
        "Time": t_samples,
        "Speed": np.interp(d_s, d_fine, v_fine),
        "Throttle": np.interp(d_s, d_fine, chans["Throttle"]),
        "Brake": (np.interp(d_s, d_fine, chans["Brake"]) > 0.5).astype(float),
        "nGear": np.round(np.interp(d_s, d_fine, chans["nGear"])),
        "X": np.interp(d_s, d_fine, chans["X"]),
        "Y": np.interp(d_s, d_fine, chans["Y"]),
    })[TELEMETRY_CHANNELS]

    return Lap(driver=driver, lap_number=lap_number, lap_time=total_t,
               compound="SOFT", tyre_life=3.0, telemetry=tel)


def make_driver_laps(driver: str, n_laps: int, *, is_fast: bool,
                     noise_kmh: float = 2.5, seed: int = 0) -> DriverLaps:
    """Generate ``n_laps`` clean laps for one driver.

    ``is_fast`` driver A gets a genuine apex-speed gain in the signal corners;
    both drivers get independent per-corner, per-lap apex noise everywhere.
    """
    rng = np.random.default_rng(seed)
    laps = []
    for i in range(n_laps):
        offsets = rng.normal(0.0, noise_kmh, size=len(_CORNERS))
        if is_fast:
            for c in _SIGNAL_CORNERS:
                offsets[c] += _SIGNAL_GAIN_KMH
        laps.append(_make_lap(driver, lap_number=i + 1, apex_offsets=offsets))
    return DriverLaps(driver=driver, laps=laps, dropped=[])


def load_drivers(n_laps: int = 6,
                 driver_a: str = "RUS",
                 driver_b: str = "ANT",
                 seed: int = 20240619) -> tuple[DriverLaps, DriverLaps]:
    """Drop-in offline replacement for ``data_loading.load_drivers``.

    Driver B is the genuinely quicker driver here (carries more apex speed in
    the signal corners), so the planted advantage shows up as A-slower there.
    """
    a = make_driver_laps(driver_a, n_laps, is_fast=False, seed=seed)
    b = make_driver_laps(driver_b, n_laps, is_fast=True, seed=seed + 1)
    return a, b


SIGNAL_CORNERS = _SIGNAL_CORNERS
