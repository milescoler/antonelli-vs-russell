"""Per-factor signal-vs-noise verdicts for the race-win decomposition.

Pure functions over serializer outputs. Each returns
{magnitudeS, magnitudeUnit, verdict, headline, caveat}. Thresholds are starting
values calibrated on real data; the pace/tyre bootstrap-CI upgrade lands with the
where-on-track pass.
"""
from __future__ import annotations

# Tunable starting thresholds (calibrate on real 2026 data).
START_REAL_PLACES = 2          # net lap-1 places gained to call the start decisive
PACE_REAL_S_PER_LAP = 0.15     # like-compound per-lap median advantage to call pace real
TYRE_REAL_S_PER_LAP = 0.03     # like-compound deg-slope advantage to call tyre real


def _row(rows, code):
    for r in rows:
        if r["code"] == code:
            return r
    return None


def start_verdict(start_rows: list[dict], winner_code: str, p2_code: str,
                  *, inherited: bool = False) -> dict:
    w = _row(start_rows, winner_code)
    gained = (w or {}).get("positionsGained")
    if inherited:
        verdict = "inherited"
        caveat = "lead inherited when the polesitter retired"
        headline = f"{winner_code} inherited the lead after the polesitter retired"
    elif gained is None:
        verdict, caveat = "insufficient", "no lap-1 data"
        headline = "no lap-1 data"
    elif gained >= START_REAL_PLACES:
        verdict, caveat = "real", "conflates start skill with grid position and lap-1 luck"
        headline = f"{winner_code} {'+' if gained >= 0 else ''}{gained} places on lap 1"
    else:
        verdict, caveat = "noise", "lap-1 swing within normal first-lap scatter"
        headline = f"{winner_code} {'+' if (gained or 0) >= 0 else ''}{gained} places on lap 1"
    return {
        "magnitudeS": (None if gained is None else float(gained)),
        "magnitudeUnit": "places",
        "verdict": verdict,
        "headline": headline,
        "caveat": caveat,
    }


def _like_compound_pairs(rows, winner_code, p2_code, value_key):
    """Per shared (compound) the (winner_value, p2_value) on the winner's and P2's
    stints of that compound (mean across stints of the compound)."""
    out = {}
    for code in (winner_code, p2_code):
        for r in rows:
            if r["code"] != code or r.get(value_key) is None:
                continue
            out.setdefault(r["compound"], {}).setdefault(code, []).append(r[value_key])
    pairs = []
    for comp, d in out.items():
        if winner_code in d and p2_code in d:
            wv = sum(d[winner_code]) / len(d[winner_code])
            pv = sum(d[p2_code]) / len(d[p2_code])
            pairs.append((comp, wv, pv))
    return pairs


def pace_verdict(stint_pace_rows: list[dict], winner_code: str, p2_code: str) -> dict:
    pairs = _like_compound_pairs(stint_pace_rows, winner_code, p2_code, "medianLaptime_s")
    if not pairs:
        return {"magnitudeS": None, "magnitudeUnit": "s_per_lap", "verdict": "insufficient",
                "headline": "no shared compound to compare race pace",
                "caveat": "winner and P2 never ran the same compound"}
    # winner − P2 per-lap delta, averaged over shared compounds (negative = winner faster)
    delta = sum(wv - pv for _, wv, pv in pairs) / len(pairs)
    verdict = "real" if delta <= -PACE_REAL_S_PER_LAP else "noise"
    return {"magnitudeS": round(delta, 3), "magnitudeUnit": "s_per_lap", "verdict": verdict,
            "headline": f"{winner_code} {abs(delta):.2f}s/lap "
                        f"{'faster' if delta < 0 else 'slower'} on like compounds",
            "caveat": "not fuel-corrected; tyre-management can mask true pace"}


def tyre_verdict(deg_rows: list[dict], winner_code: str, p2_code: str) -> dict:
    pairs = _like_compound_pairs(deg_rows, winner_code, p2_code, "degSlope_s_per_lap")
    if not pairs:
        return {"magnitudeS": None, "magnitudeUnit": "s_per_lap_of_age", "verdict": "insufficient",
                "headline": "no comparable stint long enough to fit degradation",
                "caveat": "deg slope needs >=5 clean laps on a shared compound"}
    delta = sum(wv - pv for _, wv, pv in pairs) / len(pairs)  # negative = winner degrades less
    verdict = "real" if delta <= -TYRE_REAL_S_PER_LAP else "noise"
    return {"magnitudeS": round(delta, 4), "magnitudeUnit": "s_per_lap_of_age", "verdict": verdict,
            "headline": f"{winner_code} tyres degrade {abs(delta):.3f}s/lap "
                        f"{'less' if delta < 0 else 'more'} on like compounds",
            "caveat": "fuel burn partially offsets degradation; small stint counts"}
