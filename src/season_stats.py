"""Pure descriptive aggregations for the Pitwall season dashboard. No FastF1, no I/O."""
from __future__ import annotations
import math

def _r(x, n=3):
    if x is None: return None
    fx = float(x)
    return None if math.isnan(fx) or math.isinf(fx) else round(fx, n)

def normalize_session(times: dict[str, float]) -> dict[str, float]:
    fastest = min(times.values())
    return {c: 100.0 * (t - fastest) / fastest for c, t in times.items()}

def constructors_table(drivers: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for d in drivers:
        c = agg.setdefault(d["team"], {"team": d["team"], "teamColor": d.get("teamColor"),
                                       "points": 0.0, "wins": 0, "podiums": 0})
        c["points"] += d.get("points") or 0
        c["wins"] += d.get("wins", 0)
        c["podiums"] += d.get("podiums", 0)
    out = [{**c, "points": _r(c["points"], 1)} for c in agg.values()]
    out.sort(key=lambda x: (-(x["points"] or 0), -x["wins"], x["team"]))
    return out

def pace_table(rows: list[dict], value_key: str = "gap_pct") -> list[dict]:
    by: dict[str, dict] = {}
    for r in rows:
        d = by.setdefault(r["code"], {"code": r["code"], "name": r["name"], "team": r["team"],
                                      "teamColor": r.get("teamColor"), "_vals": [], "byRound": []})
        d["name"], d["team"], d["teamColor"] = r["name"], r["team"], r.get("teamColor")
        d["_vals"].append(float(r[value_key]))
        d["byRound"].append({"round": int(r["round"]), "value": _r(r[value_key], 3)})
    out = []
    for d in by.values():
        vals = d.pop("_vals")
        d["byRound"].sort(key=lambda x: x["round"])
        out.append({**d, "mean": _r(sum(vals) / len(vals), 3) if vals else None})
    out.sort(key=lambda x: (x["mean"] is None, x["mean"] if x["mean"] is not None else 9e9, x["code"]))
    for i, d in enumerate(out, 1):
        d["rank"] = i
    return out
