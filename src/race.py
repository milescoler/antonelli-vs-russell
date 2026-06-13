"""
Race-session analysis: how Antonelli converts grid position into wins.
Loads FastF1 Race (R) sessions and computes start, race-pace, tire-degradation,
and gap-to-rival metrics. Mirrors src/benchmarks.py (qualifying) in spirit:
pure-ish functions returning tidy DataFrames; plotting lives in src/plotting.py.

Sign convention: positive = Antonelli better (positions gained, pace, low deg).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import fastf1

from src.loaders import setup_cache  # noqa: F401  (re-exported for convenience)

MIN_DEG_LAPS = 5  # minimum clean laps in a stint to fit a degradation slope


def load_race_session(year: int, round_or_name) -> fastf1.core.Session:
    """Load a Race (R) session with laps. Parallels load_qualifying_session,
    but for the race. Telemetry is not needed for the race metrics, so we load
    laps only (faster)."""
    session = fastf1.get_session(year, round_or_name, "R")
    session.load(telemetry=False, weather=False, messages=False)
    return session


def get_clean_laps(session, driver: str) -> pd.DataFrame:
    """Green-flag racing laps for one driver, as a plain DataFrame.

    A clean lap:
      - has TrackStatus == '1' for the WHOLE lap (FastF1 concatenates per-lap
        status codes; any multi-character value means the status changed
        mid-lap, e.g. a safety car was deployed — those laps are excluded),
      - is not an in-lap or out-lap (PitInTime / PitOutTime are NaT),
      - is not lap 1 (standing-start lap is not representative race pace),
      - has a valid LapTime.

    This is the shared filter every race-pace / tire metric builds on.
    """
    laps = session.laps.pick_drivers(driver)
    clean = laps[
        (laps["TrackStatus"] == "1")
        & (laps["LapNumber"] != 1)
        & (laps["PitInTime"].isna())
        & (laps["PitOutTime"].isna())
        & (laps["LapTime"].notna())
    ].copy()
    clean["LapTimeSeconds"] = clean["LapTime"].dt.total_seconds()
    return clean.reset_index(drop=True)


def _pn_finisher(session, n: int) -> str:
    """Driver code (abbreviation) of the car classified Pn in the race."""
    res = session.results
    row = res[res["Position"] == float(n)]
    if row.empty:
        raise ValueError(f"No P{n} finisher found in this race.")
    return str(row["Abbreviation"].iloc[0])


def _lap1_position(session, code: str) -> float:
    """Position at the end of lap 1 for a driver code."""
    laps = session.laps.pick_drivers(code)
    lap1 = laps[laps["LapNumber"] == 1]
    if lap1.empty:
        return float("nan")
    return float(lap1["Position"].iloc[0])


def start_summary(year: int, race_name, drv_a: str = "ANT", drv_b: str = "RUS") -> pd.DataFrame:
    """One row per reference driver (ANT, RUS, and the per-race P2 finisher):
    grid position, position at end of lap 1, positions gained on lap 1, and
    final classified position.

    'driver' column is the ROLE ('ANT' / 'RUS' / 'P2'); 'code' is the actual
    three-letter code (so the field reference's identity is visible — it
    varies by race).

    positions_gained = grid - lap1_pos  (positive = gained places off the line).
    """
    session = load_race_session(year, race_name)
    res = session.results

    p2_code = _pn_finisher(session, 2)
    roles = [("ANT", drv_a), ("RUS", drv_b), ("P2", p2_code)]

    rows = []
    for role, code in roles:
        r = res[res["Abbreviation"] == code]
        if r.empty:
            continue
        grid = float(r["GridPosition"].iloc[0])
        finish = float(r["Position"].iloc[0])
        lap1 = _lap1_position(session, code)
        rows.append({
            "race": str(session.event["EventName"]),
            "driver": role,
            "code": code,
            "grid": grid,
            "lap1_pos": lap1,
            "positions_gained": grid - lap1,
            "finish": finish,
            "status": str(r["Status"].iloc[0]),
        })
    return pd.DataFrame(rows)


def stint_pace(year: int, race_name, drivers: list[str]) -> pd.DataFrame:
    """Per driver per stint: median CLEAN-lap time, compound, and clean-lap
    count. Built on get_clean_laps, so safety-car/pit/lap-1 laps are excluded.
    Use for like-compound pace comparison between ANT, RUS, and the field ref;
    the caller is responsible for only comparing matching compounds."""
    session = load_race_session(year, race_name)
    rows = []
    for code in drivers:
        clean = get_clean_laps(session, code)
        if clean.empty:
            continue
        for stint, grp in clean.groupby("Stint"):
            rows.append({
                "race": str(session.event["EventName"]),
                "driver": code,
                "stint": int(stint),
                "compound": str(grp["Compound"].iloc[0]),
                "median_laptime_s": float(grp["LapTimeSeconds"].median()),
                "n_clean": int(len(grp)),
            })
    return pd.DataFrame(rows)


def tire_deg(year: int, race_name, drivers: list[str]) -> pd.DataFrame:
    """Per driver per clean stint: linear slope of clean-lap time vs TyreLife
    (seconds lost per lap of tire age), the compound, and the clean-lap count.

    Stints with fewer than MIN_DEG_LAPS clean laps yield deg_slope_s_per_lap =
    NaN (a fitted slope on 2-3 points is noise, not signal). Fuel burn lowers
    lap times through a stint and partially offsets real degradation — this is
    NOT corrected for; it is named as a caveat in the narrative."""
    session = load_race_session(year, race_name)
    rows = []
    for code in drivers:
        clean = get_clean_laps(session, code)
        if clean.empty:
            continue
        for stint, grp in clean.groupby("Stint"):
            n = len(grp)
            if n >= MIN_DEG_LAPS:
                slope = float(
                    np.polyfit(grp["TyreLife"].astype(float),
                               grp["LapTimeSeconds"].astype(float), 1)[0]
                )
            else:
                slope = float("nan")
            rows.append({
                "race": str(session.event["EventName"]),
                "driver": code,
                "stint": int(stint),
                "compound": str(grp["Compound"].iloc[0]),
                "deg_slope_s_per_lap": slope,
                "n_clean": int(n),
            })
    return pd.DataFrame(rows)


def gap_to_rival(year: int, race_name, driver: str) -> pd.DataFrame:
    """Per-lap race-control trace for `driver`, with a single consistent
    semantics so the notebook never special-cases the leader:

      - When `driver` is NOT leading at the end of a lap: gap_s is the time
        gap BEHIND the leader (positive = behind), and leading=False.
      - When `driver` IS leading: gap_s is the gap AHEAD of P2, expressed as a
        NEGATIVE number (so 'lower is better/further ahead' holds across the
        whole trace), and leading=True.

    Gaps are derived from each lap's cumulative session Time at the timing
    line: gap to a rival on a given lap = our Time(lap) - their Time(lap).
    Laps where the needed Time values are missing are skipped.
    """
    session = load_race_session(year, race_name)
    laps = session.laps

    # Pivot: cumulative Time at the end of each lap, per driver code.
    # session.laps['Time'] is the session clock at lap completion.
    t = laps[["LapNumber", "DriverNumber", "Position", "Time"]].copy()
    t["Time_s"] = t["Time"].dt.total_seconds()

    drv_num = str(session.get_driver(driver)["DriverNumber"])

    rows = []
    for lap_no, grp in t.groupby("LapNumber"):
        grp = grp.dropna(subset=["Time_s", "Position"])
        if grp.empty:
            continue
        me = grp[grp["DriverNumber"].astype(str) == drv_num]
        if me.empty:
            continue
        my_time = float(me["Time_s"].iloc[0])
        my_pos = float(me["Position"].iloc[0])

        if my_pos == 1.0:
            # Leading: gap ahead of P2 (negative).
            p2 = grp[grp["Position"] == 2.0]
            if p2.empty:
                continue
            gap = my_time - float(p2["Time_s"].iloc[0])  # <= 0
            leading = True
        else:
            # Chasing: gap behind leader (positive).
            leader = grp[grp["Position"] == 1.0]
            if leader.empty:
                continue
            gap = my_time - float(leader["Time_s"].iloc[0])  # >= 0
            leading = False

        rows.append({
            "race": str(session.event["EventName"]),
            "lap": int(lap_no),
            "gap_s": gap,
            "leading": leading,
        })
    return pd.DataFrame(rows).sort_values("lap").reset_index(drop=True)
