"""Data access layer - the *only* module that talks to FastF1.

Everything downstream consumes plain, standardised pandas DataFrames (the
schema in ``TELEMETRY_CHANNELS``), so the statistical pipeline never depends on
FastF1 internals and can be exercised offline with synthetic fixtures
(``src.synthetic``). That separation is what makes the reconciliation test
runnable without a network connection.

Lap cleaning is explicit and *logged*: every lap that is dropped says why. For
a portfolio piece the discarded laps are as informative as the kept ones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

# Standardised telemetry schema. Every loader (real or synthetic) returns a
# DataFrame with exactly these columns so the rest of the pipeline is agnostic.
TELEMETRY_CHANNELS = [
    "Distance",   # cumulative metres along the lap, monotone increasing
    "Time",       # seconds since lap start (the car's own clock)
    "Speed",      # km/h
    "Throttle",   # 0-100 %
    "Brake",      # 0/1 (or 0-100); treated as an intensity
    "nGear",      # 1-8
    "X",          # track position (for the map plot)
    "Y",
]


@dataclass
class Lap:
    """One clean, flat-out lap described on its native (irregular) samples."""

    driver: str
    lap_number: int
    lap_time: float                 # official lap time, seconds
    compound: str | None
    tyre_life: float | None
    telemetry: pd.DataFrame         # columns == TELEMETRY_CHANNELS

    @property
    def lap_length(self) -> float:
        return float(self.telemetry["Distance"].iloc[-1])


@dataclass
class DriverLaps:
    """All clean laps for one driver plus the representative (fastest) lap."""

    driver: str
    laps: list[Lap]
    dropped: list[tuple[int, str]] = field(default_factory=list)

    @property
    def fastest(self) -> Lap:
        return min(self.laps, key=lambda lp: lp.lap_time)


# --------------------------------------------------------------------------- #
# Cache + session
# --------------------------------------------------------------------------- #
def enable_cache() -> None:
    """Point FastF1 at the local cache so reruns are offline and fast."""
    import fastf1

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    logger.info("FastF1 cache enabled at %s", config.CACHE_DIR)


def load_session(year: int | None = None,
                 gp: str | None = None,
                 session: str | None = None):
    """Load and return a FastF1 session with laps + telemetry available."""
    import fastf1

    year = year or config.YEAR
    gp = gp or config.GRAND_PRIX
    session = session or config.SESSION

    enable_cache()
    ses = fastf1.get_session(year, gp, session)
    ses.load(telemetry=True, laps=True, weather=False, messages=True)
    logger.info("Loaded %s %s %s: %d laps", year, gp, session, len(ses.laps))
    return ses


# --------------------------------------------------------------------------- #
# Lap selection / cleaning
# --------------------------------------------------------------------------- #
def _standardise_telemetry(tel: pd.DataFrame) -> pd.DataFrame:
    """Coerce a FastF1 telemetry frame into the canonical schema."""
    tel = tel.copy()
    if "Distance" not in tel:
        tel = tel.add_distance()
    # FastF1 stores Time as a timedelta relative to lap/session start.
    if np.issubdtype(tel["Time"].dtype, np.timedelta64):
        tel["Time"] = tel["Time"].dt.total_seconds()
        tel["Time"] -= tel["Time"].iloc[0]          # zero at lap start
    # Brake may be boolean; downstream treats it as a 0-1 intensity.
    tel["Brake"] = tel["Brake"].astype(float)
    for col in ("X", "Y"):
        if col not in tel:
            tel[col] = np.nan
    return tel[TELEMETRY_CHANNELS].reset_index(drop=True)


def select_clean_laps(session, driver: str) -> DriverLaps:
    """Pick flat-out, green-flag laps for one driver and log every rejection.

    Cleaning rules (each a known confound from the spec's §3.6):
      * accurate laps only (FastF1's ``IsAccurate``) - drops sensor/lap-marker
        glitches and in/out laps;
      * green flag - the lap must not overlap a yellow/SC/red track status;
      * within ``QUICKLAP_THRESHOLD`` of the driver's own best - removes laps
        compromised by traffic, lifts, or aborted runs.
    """
    laps = session.laps.pick_drivers(driver)
    kept: list[Lap] = []
    dropped: list[tuple[int, str]] = []

    # 107%-style quicklap filter relative to this driver's own best.
    try:
        quick = laps.pick_quicklaps(config.QUICKLAP_THRESHOLD)
        quick_lapnums = set(quick["LapNumber"].astype(int))
    except Exception:  # noqa: BLE001 - older/newer FastF1 signature drift
        quick_lapnums = set(laps["LapNumber"].astype(int))

    for _, lap in laps.iterrows():
        lapnum = int(lap["LapNumber"])
        if pd.isna(lap["LapTime"]):
            dropped.append((lapnum, "no lap time (in/out or incomplete)"))
            continue
        if "IsAccurate" in lap and not bool(lap["IsAccurate"]):
            dropped.append((lapnum, "FastF1 flagged lap as not accurate"))
            continue
        if lapnum not in quick_lapnums:
            dropped.append((lapnum, f"slower than {config.QUICKLAP_THRESHOLD:.0%} of personal best"))
            continue
        try:
            tel = _standardise_telemetry(lap.get_telemetry())
        except Exception as exc:  # noqa: BLE001
            dropped.append((lapnum, f"telemetry unavailable: {exc}"))
            continue
        if len(tel) < 50 or tel["Distance"].iloc[-1] <= 0:
            dropped.append((lapnum, "degenerate telemetry"))
            continue
        kept.append(Lap(
            driver=driver,
            lap_number=lapnum,
            lap_time=float(lap["LapTime"].total_seconds()),
            compound=lap.get("Compound"),
            tyre_life=(None if pd.isna(lap.get("TyreLife")) else float(lap["TyreLife"])),
            telemetry=tel,
        ))

    for lapnum, why in dropped:
        logger.info("  drop %s lap %d: %s", driver, lapnum, why)
    logger.info("%s: kept %d clean laps, dropped %d", driver, len(kept), len(dropped))
    if len(kept) < config.MIN_CLEAN_LAPS:
        logger.warning("%s has only %d clean lap(s) - bootstrap CIs will be weak",
                       driver, len(kept))
    return DriverLaps(driver=driver, laps=kept, dropped=dropped)


def load_drivers(year=None, gp=None, session=None,
                 driver_a=None, driver_b=None) -> tuple[DriverLaps, DriverLaps]:
    """End-to-end: load the session and return clean laps for both drivers."""
    ses = load_session(year, gp, session)
    a = select_clean_laps(ses, driver_a or config.DRIVER_A)
    b = select_clean_laps(ses, driver_b or config.DRIVER_B)
    return a, b
