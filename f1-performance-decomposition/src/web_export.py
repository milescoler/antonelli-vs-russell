"""Export the decomposition `res` dict to the web JSON contract, and derive the
teammate matchups to run. Pure functions only — no FastF1, no file IO — so they
are unit-tested offline. The build script (scripts/build_decomp_data.py) does the
IO and calls these.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _hex(color) -> str | None:
    if isinstance(color, str) and color:
        return color if color.startswith("#") else f"#{color}"
    return None


def teammate_pairs(results: pd.DataFrame) -> list[dict]:
    """Teams with exactly two classified drivers -> one pair each.

    A is the better-placed driver (lower GridPosition; falls back to Position,
    then to alphabetical) so the ordering is deterministic.
    """
    rank_col = "GridPosition" if "GridPosition" in results.columns else (
        "Position" if "Position" in results.columns else None)
    pairs: list[dict] = []
    for team, grp in results.groupby("TeamName", sort=True):
        codes = [str(c) for c in grp["Abbreviation"].tolist()]
        if len(codes) != 2:
            continue
        if rank_col is not None:
            grp = grp.sort_values(rank_col, kind="stable")
        else:
            grp = grp.sort_values("Abbreviation", kind="stable")
        a, b = (str(grp.iloc[0]["Abbreviation"]), str(grp.iloc[1]["Abbreviation"]))
        pairs.append({
            "team": str(team),
            "teamColor": _hex(grp.iloc[0].get("TeamColor")),
            "a": a, "b": b,
        })
    return pairs
