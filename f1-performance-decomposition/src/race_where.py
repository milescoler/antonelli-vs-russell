"""Factor 1 for the race-win decomposition: where on track the winner built the
gap over P2, on COMPARABLE race laps (same compound, similar tyre age & fuel),
with per-sector bootstrap CIs. Runs in the engine namespace; emits JSON via CLI.
"""
from __future__ import annotations
import numpy as np
import config


def comparable_pairs(winner_meta, p2_meta, *, age_tol=None, lap_tol=None):
    age_tol = config.COMPARABLE_AGE_TOL if age_tol is None else age_tol
    lap_tol = config.COMPARABLE_LAP_TOL if lap_tol is None else lap_tol
    pairs = []
    for w in winner_meta:
        for p in p2_meta:
            if (w["compound"] == p["compound"]
                    and abs(w["tyre_life"] - p["tyre_life"]) <= age_tol
                    and abs(w["lap_number"] - p["lap_number"]) <= lap_tol):
                pairs.append((w["idx"], p["idx"]))
    return pairs
