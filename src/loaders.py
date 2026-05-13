"""
Thin wrappers around FastF1 for loading qualifying sessions and extracting per-driver fastest laps.
"""

from pathlib import Path
import fastf1
import pandas as pd

DEFAULT_CACHE_DIR = "../fastf1_cache"


def setup_cache(cache_dir=DEFAULT_CACHE_DIR) -> None:
    """
    Ensure cache directory exists and enable FastF1 cache.

    Args:
        cache_dir (str): Path to cache directory.
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))


def load_qualifying_session(year: int, round_or_name) -> fastf1.core.Session:
    """
    Load qualifying session

    Args:
        year (int): Championship year.
        round_or_name (int or str): Round number or event name (e.g. 'Australia').

    Returns:
        fastf1.core.Session: FastF1 session object with telemetry loaded.
    """
    session = fastf1.get_session(year, round_or_name, 'Q')
    session.load()
    return session


def get_fastest_valid_lap(session, driver_code: str):
    """
    Get fastest valid lap for a driver in a session.

    Args:
        session: FastF1 session object.
        driver_code: Driver code (e.g. 'HAM').

    Returns:
        FastF1 lap object for the fastest valid lap.

    Raises:
        ValueError: If no valid laps are found for the driver.
    """
    driver_laps = session.laps.pick_drivers(driver_code)
    valid_laps = driver_laps.pick_quicklaps()
    fastest_lap = valid_laps.pick_fastest()

    if pd.isna(fastest_lap["LapTime"]):
        raise ValueError(
            f"No valid laps found for driver {driver_code} in this session"
        )

    return fastest_lap


def get_lap_telemetry(lap) -> pd.DataFrame:
    """
    Get lap telemetry for a lap.

    Args:
        lap: FastF1 lap object.

    Returns:
        Telemetry as a pandas DataFrame. Columns commonly used downstream:
          - Distance (m): cumulative distance from lap start (integrated from speed)
          - Speed (kph): instantaneous speed
          - Time (Timedelta): time from lap start
          - X, Y (track coordinates): position on the circuit
          - Throttle, Brake, nGear, DRS, RPM: control / state channels
          - Status, Source: telemetry provenance flags
        Other FastF1-provided columns may also be present.

    Raises:
        ValueError: If no telemetry found for the lap.
    """
    telemetry = lap.get_telemetry()

    if telemetry.empty:
        raise ValueError(f"No telemetry found for lap {lap['LapNumber']}")

    return telemetry
