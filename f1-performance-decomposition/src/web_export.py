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


def _num(x, n: int = 4):
    """Round to n decimals; NaN/inf/None -> None (JSON null)."""
    if x is None:
        return None
    try:
        fx = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(fx) or math.isinf(fx)) else round(fx, n)


def _downsample_idx(n: int, max_points: int) -> list[int]:
    """Indices subsampling 0..n-1 to at most ``max_points`` points, always
    including the first and last (so the curve still ends at the finish line)."""
    if n <= max_points:
        return list(range(n))
    return sorted({int(round(i)) for i in np.linspace(0, n - 1, max_points)})


def _corner_labels(corner_distances) -> list[dict]:
    if corner_distances is None:
        return []
    cd = np.sort(np.asarray(corner_distances, dtype=float))
    return [{"d": _num(d, 1), "label": f"T{i + 1}"} for i, d in enumerate(cd)]


def matchup_payload(res: dict, race_meta: dict, *, max_points: int = 200) -> dict:
    grid = np.asarray(res["grid"], dtype=float)
    delta = np.asarray(res["delta"], dtype=float)
    repr_a = res["repr_a"]
    rate = np.gradient(delta, grid)             # s per m: slope of the curve

    ci = _downsample_idx(len(grid), max_points)
    delta_curve = [{"d": _num(grid[i], 1), "delta": _num(delta[i], 4)} for i in ci]
    track = [{"x": _num(repr_a["X"].to_numpy()[i], 1),
              "y": _num(repr_a["Y"].to_numpy()[i], 1),
              "rate": _num(rate[i], 6)} for i in ci]

    sectors = [{
        "i": int(r["sector"]),
        "startM": _num(r["start_m"], 1), "endM": _num(r["end_m"], 1),
        "midM": _num(r["mid_m"], 1),
        "deltaMean": _num(r["delta_s_mean"], 4),
        "ciLow": _num(r["ci_low"], 4), "ciHigh": _num(r["ci_high"], 4),
        "significant": bool(r["significant"]),
        "faster": (None if not np.isfinite(r["delta_s_mean"])
                   else (res["driver_a"] if r["delta_s_mean"] > 0 else res["driver_b"])),
    } for _, r in res["table"].sort_values("sector").iterrows()]
    # note: delta = t_A - t_B, so deltaMean > 0 => A slower => B faster in that sector.

    attribution = [{
        "sector": int(r["sector"]),
        "driverFaster": str(r["faster_driver"]),
        "deltaS": _num(r["delta_s"], 4),
        "significant": bool(r["significant"]),
        "narrative": str(r["narrative"]),
    } for _, r in res["attrib"].iterrows()] if len(res["attrib"]) else []

    table = res["table"]
    noise = table[~table["significant"]]
    callouts = {
        "topSignificant": [int(s) for s in res["top"]["sector"].tolist()] if len(res["top"]) else [],
        "noiseTrap": (int(noise.iloc[0]["sector"]) if len(noise) else None),
    }

    return {
        "meta": {
            "race": race_meta["slug"], "eventName": race_meta["eventName"],
            "round": int(race_meta["round"]), "year": int(race_meta["year"]),
            "session": race_meta["session"],
            "driverA": {"code": res["driver_a"], "name": race_meta["driverAName"],
                        "team": race_meta["team"], "color": race_meta["teamColor"]},
            "driverB": {"code": res["driver_b"], "name": race_meta["driverBName"],
                        "team": race_meta["team"], "color": race_meta["teamColor"]},
            "officialGapS": _num(res["official_gap"], 3),
            "reconResidualS": _num(res["residual"], 4),
            "nCleanLapsA": int(res["n_laps_a"]), "nCleanLapsB": int(res["n_laps_b"]),
        },
        "deltaCurve": delta_curve,
        "corners": _corner_labels(res["corner_distances"]),
        "sectors": sectors,
        "attribution": attribution,
        "callouts": callouts,
        "track": track,
    }
