"""Cross-year, per-track overperformance — the project's car-control layer
ACROSS seasons (the teammate comparison controls for the car WITHIN a season).

Core idea: a great car flatters a driver everywhere, so a driver's result at one
track is only informative RELATIVE TO their own season baseline. We compute, per
driver-year, (season baseline over the OTHER rounds) - (result at this track);
positive = better than their usual that year. Averaging across years gives a
driver's track affinity with car quality largely divided out. The same arithmetic
on teams reveals track-specific CAR strengths.

metric='finish' excludes DNF rounds (a retirement's classified position is not
pace); metric='grid' is the DNF-free qualifying cross-check.

Data note: runs on the project's synthetic '2026-world' source; results are
internally consistent but not real F1 history. Keep claims data-driven.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import fastf1

from src.loaders import setup_cache  # noqa: F401  (re-exported for convenience)

MIN_TRACK_YEARS = 3  # below this, a driver/team's affinity is flagged small-n


def _is_classified(status) -> bool:
    """Running at the flag: 'Finished' or lapped ('+1 Lap', '+2 Laps', ...).
    Everything else (Accident, Engine, Retired, Disqualified, DNS) is a DNF."""
    s = str(status)
    return s == "Finished" or s.startswith("+")


def load_results(year: int, track: str) -> pd.DataFrame:
    """Results-only load of one Race (R) session as tidy rows. No telemetry/laps
    (fast). `track` is matched by FastF1's partial event-name resolution."""
    session = fastf1.get_session(year, track, "R")
    session.load(telemetry=False, weather=False, messages=False, laps=False)
    res = session.results
    return pd.DataFrame({
        "year": year,
        "round": int(session.event["RoundNumber"]),
        "track": track,
        "country": str(session.event.get("Country", "")),
        "location": str(session.event.get("Location", "")),
        "driver": res["Abbreviation"].astype(str).values,
        "team": res["TeamName"].astype(str).values,
        "grid": pd.to_numeric(res["GridPosition"], errors="coerce").values,
        "finish": pd.to_numeric(res["Position"], errors="coerce").values,
        "status": res["Status"].astype(str).values,
        "classified": [_is_classified(s) for s in res["Status"]],
    })


def season_table(year: int) -> pd.DataFrame:
    """Every completed round of a season as tidy rows — the basis for season
    baselines. Results-only loads; rounds that fail to load are skipped (a
    schedule entry may have no results in this data source)."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    frames = []
    for _, ev in schedule.iterrows():
        rnd = int(ev["RoundNumber"])
        try:
            session = fastf1.get_session(year, rnd, "R")
            session.load(telemetry=False, weather=False, messages=False, laps=False)
        except Exception:
            continue
        if session.results is None or len(session.results) == 0:
            continue
        res = session.results
        frames.append(pd.DataFrame({
            "year": year,
            "round": rnd,
            "track": str(ev["EventName"]),
            "country": str(ev.get("Country", "")),
            "location": str(ev.get("Location", "")),
            "driver": res["Abbreviation"].astype(str).values,
            "team": res["TeamName"].astype(str).values,
            "grid": pd.to_numeric(res["GridPosition"], errors="coerce").values,
            "finish": pd.to_numeric(res["Position"], errors="coerce").values,
            "status": res["Status"].astype(str).values,
            "classified": [_is_classified(s) for s in res["Status"]],
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _match_track(st: pd.DataFrame, track: str) -> pd.DataFrame:
    """Rows of a season table at `track`. Matches the 2026 race name (which is a
    country or location, e.g. 'Canada', 'Miami') against the schedule's Country
    and Location fields as well as the EventName — robust to the
    'Canada'->'Canadian GP' / 'China'->'Chinese GP' adjective mismatch, and
    (unlike FastF1's fuzzy resolver) returns NOTHING when the track wasn't on
    that season's calendar rather than mis-matching a different GP."""
    tl = track.lower()
    m = st["track"].astype(str).str.lower().str.contains(tl, na=False)
    if "country" in st.columns:
        m = m | st["country"].astype(str).str.lower().eq(tl)
    if "location" in st.columns:
        m = m | st["location"].astype(str).str.lower().eq(tl)
    return st[m]


def _affinity_rows(track: str, years, metric: str, group_col: str) -> pd.DataFrame:
    """Shared engine for driver_/team_ affinity. For each year, find the track's
    round, then for each group (driver or team) compute:
        track value  = group's metric at the track round
                       (finish: classified only; grid: grid>=1)
        baseline     = group's mean metric over the OTHER rounds
                       (finish: classified only; grid: grid>=1)
        delta        = baseline - track value   (positive = better than usual)
    Groups with no usable baseline that year contribute no row."""
    is_finish = metric == "finish"
    col = "finish" if is_finish else "grid"
    rows = []
    for y in years:
        st = season_table(y)
        if st.empty:
            continue
        trk = _match_track(st, track)
        if trk.empty:
            continue
        trk_round = int(trk["round"].iloc[0])

        def _usable(frame):
            if is_finish:
                return frame[frame["classified"] & frame[col].notna()]
            return frame[(frame["grid"] >= 1) & frame[col].notna()]

        for key, g in st.groupby(group_col):
            here = _usable(g[g["round"] == trk_round])
            if here.empty:
                continue
            track_val = float(here[col].mean())  # mean handles team's two cars
            others = _usable(g[g["round"] != trk_round])
            if others.empty:
                continue  # no baseline -> drop (spec edge case)
            baseline = float(others[col].mean())
            rows.append({group_col: key, "year": y,
                         "track_val": track_val, "baseline": baseline,
                         "delta": baseline - track_val})
    return pd.DataFrame(rows)


def _aggregate(rows: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if rows.empty:
        return rows
    agg = (rows.groupby(group_col)
                .agg(affinity=("delta", "mean"),
                     n_years=("delta", "size"),
                     mean_track=("track_val", "mean"))
                .reset_index())
    agg["small_n"] = agg["n_years"] < MIN_TRACK_YEARS
    return agg.sort_values("affinity", ascending=False).reset_index(drop=True)


def driver_track_affinity(track: str, years, metric: str = "finish") -> pd.DataFrame:
    """Per driver: mean overperformance vs own-season baseline at `track` across
    `years`, with n_years and a small_n flag (n_years < MIN_TRACK_YEARS).
    metric in {'finish','grid'}. Sorted best (most positive) first."""
    return _aggregate(_affinity_rows(track, years, metric, "driver"), "driver")


def team_track_affinity(track: str, years, metric: str = "finish") -> pd.DataFrame:
    """As driver_track_affinity, aggregated by team — track-specific CAR
    strength. A team's per-round value is the mean over its (classified) cars."""
    return _aggregate(_affinity_rows(track, years, metric, "team"), "team")


def track_leaderboard(track: str, years) -> pd.DataFrame:
    """Raw 'who owns this track' board over the window: wins, podiums, mean
    finish, mean grid, starts per driver. NOT car-controlled — the accessible
    hook before the overperformance metric. Sorted wins, then podiums, then
    mean finish."""
    frames = []
    for y in years:
        try:
            frames.append(load_results(y, track))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    allr = pd.concat(frames, ignore_index=True)
    cls = allr[allr["classified"]]
    out = pd.DataFrame({"n_starts": allr.groupby("driver").size()})
    out["wins"] = cls[cls["finish"] == 1].groupby("driver").size()
    out["podiums"] = cls[cls["finish"] <= 3].groupby("driver").size()
    out["mean_finish"] = cls.groupby("driver")["finish"].mean()
    out["mean_grid"] = allr[allr["grid"] >= 1].groupby("driver")["grid"].mean()
    out = out.fillna({"wins": 0, "podiums": 0}).reset_index()
    out["wins"] = out["wins"].astype(int)
    out["podiums"] = out["podiums"].astype(int)
    return out.sort_values(["wins", "podiums", "mean_finish"],
                           ascending=[False, False, True]).reset_index(drop=True)
