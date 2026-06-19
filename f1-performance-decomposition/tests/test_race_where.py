from src import race_where as rw

def _m(rows):  # rows = (idx, compound, tyre_life, lap_number)
    return [{"idx": i, "compound": c, "tyre_life": t, "lap_number": l} for i, c, t, l in rows]

def test_comparable_pairs_matches_compound_age_lap():
    w = _m([(0, "MEDIUM", 5, 10), (1, "SOFT", 3, 30)])
    p = _m([(0, "MEDIUM", 7, 12), (1, "HARD", 5, 11), (2, "SOFT", 20, 31)])
    pairs = rw.comparable_pairs(w, p, age_tol=3, lap_tol=5)
    assert (0, 0) in pairs          # MEDIUM, |5-7|=2<=3, |10-12|=2<=5
    assert (1, 2) not in pairs      # SOFT but |3-20|=17 age too far
    assert all(w[a]["compound"] == p[b]["compound"] for a, b in pairs)
