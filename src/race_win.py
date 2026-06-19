"""Resolve a race's principals (winner, P2) and assemble the per-race
decomposition payload, reusing src/race.py (factor math), src/serialize.py
(serializers), and src/race_verdict.py (verdicts). FastF1-touching wrappers are
thin; the pure logic operates on DataFrames so it is unit-tested offline.
"""
from __future__ import annotations

import pandas as pd


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
