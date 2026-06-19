"""Resolve a race's principals (winner, P2) and assemble the per-race
decomposition payload, reusing src/race.py (factor math), src/serialize.py
(serializers), and src/race_verdict.py (verdicts). FastF1-touching wrappers are
thin; the pure logic operates on DataFrames so it is unit-tested offline.
"""
from __future__ import annotations

import re

import pandas as pd

from src import serialize, race_verdict

# Lapped-but-classified statuses: "+1 Lap", "+2 Laps", etc.
_LAPPED_RE = re.compile(r"^\+\d+ Laps?$")


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


def _is_dnf(status: str) -> bool:
    """True when status represents a true retirement (not a classified finisher
    that is merely lapped). Lapped finishers have statuses like '+1 Lap',
    '+2 Laps', etc. — those are NOT retirements."""
    if status == "Finished":
        return False
    if _LAPPED_RE.match(status):
        return False
    return True


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
    any_dnf = bool(classified["Status"].astype(str).apply(_is_dnf).any())

    winner_code = str(win_row["Abbreviation"])

    # Detect inherited win: find the polesitter (GridPosition == 1.0) and check
    # if they retired before the end of the race (true DNF, not lapped).
    pole_rows = res[res["GridPosition"] == 1.0] if "GridPosition" in res.columns else res.iloc[0:0]
    if not pole_rows.empty:
        pole_row = pole_rows.iloc[0]
        pole_code = str(pole_row["Abbreviation"])
        pole_status = str(pole_row["Status"])
        winner_inherited = (pole_code != winner_code) and _is_dnf(pole_status)
        pole_sitter = pole_code
    else:
        winner_inherited = False
        pole_sitter = None

    winner_started_pole = bool(
        not pd.isna(win_row.get("GridPosition")) and float(win_row["GridPosition"]) == 1.0
    )

    return {
        "winner": _driver(win_row),
        "p2": _driver(p2_row),
        "marginS": margin_s,
        "anyDnf": any_dnf,
        "winnerStatus": str(win_row["Status"]),
        "p2Status": str(p2_row["Status"]),
        "winnerInherited": winner_inherited,
        "poleSitter": pole_sitter,
        "winnerStartedPole": winner_started_pole,
    }


def verdict_from_where(payload: dict) -> dict:
    """Convert a raw where-on-track engine payload into a verdict block.

    Args:
        payload: the JSON dict printed by the engine CLI (either a full decomp
                 result or {"verdict": "insufficient", "reason": ...}).

    Returns a dict with keys: verdict, magnitudeS, headline, caveat.
    """
    if payload.get("verdict") == "insufficient":
        return {
            "verdict": "insufficient",
            "magnitudeS": None,
            "headline": "too few comparable laps to decompose where on track",
            "caveat": payload.get("reason"),
        }

    sectors = payload.get("sectors", [])
    meta = payload.get("meta", {})
    sig = [s for s in sectors if s.get("significant")]
    n_sig = len(sig)
    N = len(sectors)

    if n_sig > 0:
        verdict = "real"
        magnitude_s = sum(s["deltaMean"] for s in sig if s.get("deltaMean") is not None) or None
    else:
        verdict = "noise"
        magnitude_s = None

    winner_code = meta.get("winnerCode") or meta.get("driverA", {}).get("code", "winner")
    headline = f"{winner_code} gained in {n_sig} of {N} micro-sectors"

    n_a = meta.get("nUniqueLapsA")
    n_b = meta.get("nUniqueLapsB")
    caveat = (
        f"based on {n_a} vs {n_b} unique comparable laps — "
        "significance is exploratory at this sample size"
    )

    return {
        "verdict": verdict,
        "magnitudeS": magnitude_s,
        "headline": headline,
        "caveat": caveat,
    }


def assemble_race(*, principals, start_df, stint_df, deg_df, gap_df,
                  round_number, slug, event_name, year) -> dict:
    w, p2 = principals["winner"]["code"], principals["p2"]["code"]

    inherited = bool(principals.get("winnerInherited", False))

    start_rows = serialize.serialize_start(start_df, a_code=w, b_code=p2)
    pace_rows = serialize.serialize_stint_pace(stint_df)
    deg_rows = serialize.serialize_tire_deg(deg_df)
    gap = serialize.serialize_gap_trace(gap_df, w) if gap_df is not None and len(gap_df) else \
        {"driverCode": w, "laps": [], "gap_s": [], "leading": []}

    pace_v = race_verdict.pace_verdict(pace_rows, w, p2)
    tyre_v = race_verdict.tyre_verdict(deg_rows, w, p2)
    start_v = race_verdict.start_verdict(start_rows, w, p2, inherited=inherited)

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
                 "marginS": principals["marginS"], "anyDnf": principals["anyDnf"],
                 "winnerInherited": inherited,
                 "poleSitter": principals.get("poleSitter"),
                 "winnerStartedPole": principals.get("winnerStartedPole")},
        "signConvention": "winner_minus_p2",
        "factors": factors,
        "caveats": {"anyDnf": principals["anyDnf"], "fuelNotCorrected": True,
                    "noCleanLapsDriver": [c for c in (w, p2)
                                          if c not in {r["code"] for r in pace_rows}]},
    }
