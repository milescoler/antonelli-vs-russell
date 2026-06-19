"""Resolve a race's principals (winner, P2) and assemble the per-race
decomposition payload, reusing src/race.py (factor math), src/serialize.py
(serializers), and src/race_verdict.py (verdicts). FastF1-touching wrappers are
thin; the pure logic operates on DataFrames so it is unit-tested offline.
"""
from __future__ import annotations

import pandas as pd

from src import serialize, race_verdict


def _hex(color) -> str | None:
    if isinstance(color, str) and color:
        return color if color.startswith("#") else f"#{color}"
    return None


def _driver(row) -> dict:
    return {
        "code": str(row["Abbreviation"]),
        "name": str(row["FullName"]),
        "team": str(row["TeamName"]),
        "color": _hex(row.get("TeamColor")),
    }


def principals_from_results(results: pd.DataFrame) -> dict:
    res = results.sort_values("Position")
    win_row = res[res["Position"] == 1.0]
    p2_row = res[res["Position"] == 2.0]
    if win_row.empty or p2_row.empty:
        raise ValueError("race has no classified P1/P2")
    win_row, p2_row = win_row.iloc[0], p2_row.iloc[0]

    t = p2_row.get("Time")
    margin_s = None if pd.isna(t) else float(pd.to_timedelta(t).total_seconds())

    classified = res[res["Position"].notna()]
    any_dnf = bool((classified["Status"].astype(str) != "Finished").any())

    return {
        "winner": _driver(win_row),
        "p2": _driver(p2_row),
        "marginS": margin_s,
        "anyDnf": any_dnf,
        "winnerStatus": str(win_row["Status"]),
        "p2Status": str(p2_row["Status"]),
    }


def assemble_race(*, principals, start_df, stint_df, deg_df, gap_df,
                  round_number, slug, event_name, year) -> dict:
    w, p2 = principals["winner"]["code"], principals["p2"]["code"]

    start_rows = serialize.serialize_start(start_df, a_code=w, b_code=p2)
    pace_rows = serialize.serialize_stint_pace(stint_df)
    deg_rows = serialize.serialize_tire_deg(deg_df)
    gap = serialize.serialize_gap_trace(gap_df, w) if gap_df is not None and len(gap_df) else \
        {"driverCode": w, "laps": [], "gap_s": [], "leading": []}

    pace_v = race_verdict.pace_verdict(pace_rows, w, p2)
    tyre_v = race_verdict.tyre_verdict(deg_rows, w, p2)
    start_v = race_verdict.start_verdict(start_rows, w, p2)

    factors = {
        "where": {"verdict": "insufficient", "magnitudeS": None,
                  "headline": "computed in the where-on-track pass", "decomp": None},
        "tyre": {**tyre_v, "stints": [r for r in deg_rows if r["code"] in (w, p2)]},
        "pace": {**pace_v, "gapTrace": gap,
                 "stints": [r for r in pace_rows if r["code"] in (w, p2)]},
        "start": {**start_v, "rows": start_rows},
    }
    return {
        "meta": {"race": slug, "eventName": event_name, "round": int(round_number),
                 "year": int(year), "winner": principals["winner"], "p2": principals["p2"],
                 "marginS": principals["marginS"], "anyDnf": principals["anyDnf"]},
        "signConvention": "winner_minus_p2",
        "factors": factors,
        "caveats": {"anyDnf": principals["anyDnf"], "fuelNotCorrected": True,
                    "noCleanLapsDriver": [c for c in (w, p2)
                                          if c not in {r["code"] for r in pace_rows}]},
    }
