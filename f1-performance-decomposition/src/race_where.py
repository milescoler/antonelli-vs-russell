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


def paired_sector_bootstrap(pair_deltas, *, n_boot=None, confidence=None, seed=None):
    n_boot = config.N_BOOTSTRAP if n_boot is None else n_boot
    confidence = config.CONFIDENCE if confidence is None else confidence
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)
    mat = np.asarray(pair_deltas, dtype=float)
    n_pairs, n_sec = mat.shape
    point = mat.mean(axis=0)
    boot = np.empty((n_boot, n_sec))
    for k in range(n_boot):
        idx = rng.integers(0, n_pairs, size=n_pairs)   # resample PAIRS (matched)
        boot[k] = mat[idx].mean(axis=0)
    a = 1.0 - confidence
    lo = np.percentile(boot, 100 * a / 2, axis=0)
    hi = np.percentile(boot, 100 * (1 - a / 2), axis=0)
    sig = (lo > 0) | (hi < 0)
    return [{"sector": i + 1, "deltaMean": float(point[i]), "ciLow": float(lo[i]),
             "ciHigh": float(hi[i]), "significant": bool(sig[i])} for i in range(n_sec)]
