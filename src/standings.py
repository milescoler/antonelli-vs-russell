"""Driver-level season standings + a transparent next-race win-odds heuristic.

"Who's doing the best" is answered with **real championship points** (FastF1's
results carry a Points column). Predictions are an explicitly labeled heuristic —
a recency-weighted blend of recent finishing points — NOT a trained model. The
honesty (state the method, don't dress it up) matches the rest of the project.

The pure functions (build_standings / predict_next) take plain per-round result
dicts and are unit-tested; the FastF1 loader is a thin wrapper.
"""
from __future__ import annotations

import fastf1
import pandas as pd

from src.serialize import _int_or_none, _num


def _results_for_round(year: int, rnd: int) -> list[dict]:
    """Light load of a race's results into plain dicts (no telemetry)."""
    session = fastf1.get_session(year, rnd, "R")
    session.load(laps=False, telemetry=False, weather=False, messages=False)
    rows = []
    for _, r in session.results.iterrows():
        tc = r.get("TeamColor")
        rows.append({
            "code": str(r["Abbreviation"]),
            "name": str(r["FullName"]),
            "team": str(r["TeamName"]),
            "teamColor": f"#{tc}" if isinstance(tc, str) and tc else None,
            "pos": _int_or_none(r["Position"]),
            "grid": _int_or_none(r["GridPosition"]),
            "points": 0.0 if pd.isna(r["Points"]) else float(r["Points"]),
            "status": str(r["Status"]),
        })
    return rows


def season_results(year: int, rounds: list[int]) -> list[list[dict]]:
    """Per-round result rows for the completed rounds (graceful per-round skip)."""
    out = []
    for rnd in rounds:
        try:
            out.append(_results_for_round(year, rnd))
        except Exception as exc:  # noqa: BLE001
            print(f"  standings: skip R{rnd}: {exc!r}")
    return out


# ---- pure: standings -----------------------------------------------------

def build_standings(per_round: list[list[dict]]) -> list[dict]:
    """Championship standings from real points, sorted by points desc (then wins).
    Each entry carries form metrics + the per-round finishing positions."""
    agg: dict[str, dict] = {}
    for rnd in per_round:
        for r in rnd:
            d = agg.setdefault(r["code"], {
                "code": r["code"], "name": r["name"], "team": r["team"],
                "teamColor": r["teamColor"], "points": 0.0, "wins": 0,
                "podiums": 0, "finishes": [], "_classified": [],
            })
            d["name"], d["team"], d["teamColor"] = r["name"], r["team"], r["teamColor"]
            d["points"] += r["points"]
            if r["pos"] == 1:
                d["wins"] += 1
            if r["pos"] is not None and r["pos"] <= 3:
                d["podiums"] += 1
            d["finishes"].append(r["pos"])
            if r["pos"] is not None:
                d["_classified"].append(r["pos"])

    out = []
    for d in agg.values():
        classified = d.pop("_classified")
        out.append({
            **d,
            "points": _num(d["points"], 1),
            "avgFinish": _num(sum(classified) / len(classified), 1) if classified else None,
            "bestFinish": min(classified) if classified else None,
        })
    out.sort(key=lambda x: (-(x["points"] or 0), -x["wins"], x["avgFinish"] or 99))
    return out


# ---- pure: next-race prediction (heuristic) ------------------------------

def predict_next(per_round: list[list[dict]], recent_n: int = 3, power: float = 2.0,
                 top: int = 6) -> list[dict]:
    """Heuristic win odds for the next race: recency-weighted recent-form points,
    raised to `power` to concentrate on front-runners, then normalized to shares.
    NOT a probability model — a transparent form index. Returns the top `top`."""
    recent = per_round[-recent_n:]
    meta: dict[str, dict] = {}
    score: dict[str, float] = {}
    for i, rnd in enumerate(recent):
        weight = i + 1  # most recent round weighted highest
        for r in rnd:
            score[r["code"]] = score.get(r["code"], 0.0) + weight * r["points"]
            meta[r["code"]] = r
    powered = {c: s ** power for c, s in score.items() if s > 0}
    total = sum(powered.values()) or 1.0
    ranked = sorted(powered.items(), key=lambda kv: -kv[1])[:top]
    return [
        {
            "code": c,
            "name": meta[c]["name"],
            "team": meta[c]["team"],
            "teamColor": meta[c]["teamColor"],
            "winOdds": _num(p / total, 3),
            "recentPoints": _num(score[c], 1),
        }
        for c, p in ranked
    ]
