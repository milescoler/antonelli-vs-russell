"""Driver-input attribution: *why* the time appears where it does.

At the micro-sectors with the largest real deltas, we read the two drivers'
Speed / Throttle / Brake / Gear traces and characterise the cause along the
three phases of a corner: entry (braking), mid-corner (apex speed), and exit
(throttle application). The output is a short, falsifiable sentence per sector -
the causal story the stats earned the right to tell.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config

BRAKE_ON = 0.1        # brake intensity counts as "on the brakes" above this
THROTTLE_FULL = 95.0  # % throttle counted as "back to full"


def _window(resampled: pd.DataFrame, start_m: float, end_m: float) -> pd.DataFrame:
    d = resampled["Distance"].to_numpy()
    mask = (d >= start_m) & (d <= end_m)
    return resampled.loc[mask]


def sector_features(resampled: pd.DataFrame, start_m: float, end_m: float) -> dict:
    """Summarise one driver's inputs through one micro-sector."""
    w = _window(resampled, start_m, end_m)
    d = w["Distance"].to_numpy()
    speed = w["Speed"].to_numpy()
    brake = w["Brake"].to_numpy()
    throttle = w["Throttle"].to_numpy()

    apex_idx = int(np.argmin(speed))
    apex_d = float(d[apex_idx])

    # First point on the brakes within the sector (entry/braking marker).
    on_brakes = np.where(brake > BRAKE_ON)[0]
    brake_point = float(d[on_brakes[0]]) if len(on_brakes) else np.nan

    # First return to full throttle at or after the apex (exit marker).
    after_apex = throttle.copy()
    after_apex[:apex_idx] = 0.0
    full = np.where(after_apex >= THROTTLE_FULL)[0]
    throttle_point = float(d[full[0]]) if len(full) else np.nan

    return {
        "min_speed": float(speed.min()),
        "apex_m": apex_d,
        "brake_point_m": brake_point,
        "throttle_full_m": throttle_point,
        "entry_speed": float(speed[0]),
        "exit_speed": float(speed[-1]),
    }


def attribute_sector(sector_row: pd.Series,
                     repr_a: pd.DataFrame,
                     repr_b: pd.DataFrame,
                     driver_a: str | None = None,
                     driver_b: str | None = None) -> dict:
    """Compare inputs for one micro-sector and narrate the dominant cause."""
    driver_a = driver_a or config.DRIVER_A
    driver_b = driver_b or config.DRIVER_B
    s, e = float(sector_row["start_m"]), float(sector_row["end_m"])
    fa = sector_features(repr_a, s, e)
    fb = sector_features(repr_b, s, e)

    delta = float(sector_row["delta_s_mean"])
    # delta = t_A - t_B. delta < 0 => A faster here; delta > 0 => B faster.
    faster, slower = (driver_a, driver_b) if delta < 0 else (driver_b, driver_a)

    # Differences expressed from the faster driver's perspective.
    d_minspeed = fa["min_speed"] - fb["min_speed"]      # +ve => A carries more
    d_brake = (fa["brake_point_m"] - fb["brake_point_m"])   # +ve => A brakes later
    d_throttle = (fa["throttle_full_m"] - fb["throttle_full_m"])  # +ve => A later to throttle

    reasons = []
    if np.isfinite(d_brake) and abs(d_brake) >= 3:
        later, earlier = (driver_a, driver_b) if d_brake > 0 else (driver_b, driver_a)
        reasons.append(f"{later} brakes ~{abs(d_brake):.0f} m later than {earlier} (entry)")
    if abs(d_minspeed) >= 2:
        more, less = (driver_a, driver_b) if d_minspeed > 0 else (driver_b, driver_a)
        reasons.append(f"{more} carries ~{abs(d_minspeed):.0f} km/h more apex speed (mid-corner)")
    if np.isfinite(d_throttle) and abs(d_throttle) >= 3:
        earlier, later = (driver_b, driver_a) if d_throttle > 0 else (driver_a, driver_b)
        reasons.append(f"{earlier} gets to full throttle ~{abs(d_throttle):.0f} m sooner (exit)")

    if not reasons:
        reasons.append("inputs look near-identical; the delta is diffuse, not from one clear input")

    sig = "real (CI excludes 0)" if bool(sector_row.get("significant", False)) else "within noise"
    narrative = (
        f"Sector {int(sector_row['sector'])} "
        f"({s:.0f}-{e:.0f} m): {abs(delta):.3f} s to {faster} [{sig}]. "
        + "; ".join(reasons) + "."
    )

    return {
        "sector": int(sector_row["sector"]),
        "delta_s": delta,
        "faster_driver": faster,
        "significant": bool(sector_row.get("significant", False)),
        **{f"{driver_a}_{k}": v for k, v in fa.items()},
        **{f"{driver_b}_{k}": v for k, v in fb.items()},
        "narrative": narrative,
    }


def attribute(top_sectors: pd.DataFrame,
              repr_a: pd.DataFrame,
              repr_b: pd.DataFrame,
              driver_a: str | None = None,
              driver_b: str | None = None) -> pd.DataFrame:
    """Attribution table + narratives for the key micro-sectors."""
    rows = [attribute_sector(row, repr_a, repr_b, driver_a, driver_b)
            for _, row in top_sectors.iterrows()]
    return pd.DataFrame(rows)
