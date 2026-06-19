from src import race_where as rw
import numpy as np

def _m(rows):  # rows = (idx, compound, tyre_life, lap_number)
    return [{"idx": i, "compound": c, "tyre_life": t, "lap_number": l} for i, c, t, l in rows]

def test_comparable_pairs_matches_compound_age_lap():
    w = _m([(0, "MEDIUM", 5, 10), (1, "SOFT", 3, 30)])
    p = _m([(0, "MEDIUM", 7, 12), (1, "HARD", 5, 11), (2, "SOFT", 20, 31)])
    pairs = rw.comparable_pairs(w, p, age_tol=3, lap_tol=5)
    assert (0, 0) in pairs          # MEDIUM, |5-7|=2<=3, |10-12|=2<=5
    assert (1, 2) not in pairs      # SOFT but |3-20|=17 age too far
    assert all(w[a]["compound"] == p[b]["compound"] for a, b in pairs)

def test_paired_bootstrap_flags_real_and_noise_sectors():
    rng = np.random.default_rng(0)
    n = 40
    s_real = -0.10 + 0.01 * rng.standard_normal(n)   # consistent winner gain
    s_noise = 0.0 + 0.10 * rng.standard_normal(n)     # centred on zero, wide
    mat = np.column_stack([s_real, s_noise])
    out = rw.paired_sector_bootstrap(mat, n_boot=2000, confidence=0.95, seed=1)
    assert out[0]["significant"] is True and out[0]["ciHigh"] < 0   # real winner gain
    assert out[1]["significant"] is False                           # noise straddles 0
