"""Unit tests for src/ratings.py — the car-adjusted ranking core.
Pure functions only (no FastF1): normalized gap, Layer-1 teammate margin,
Layer-3 connectivity/estimability, and Layer-2 model recovery on synthetic data."""
import math

from src import ratings


# ---- normalized gap ------------------------------------------------------

def test_normalize_session_is_pct_off_fastest():
    g = ratings.normalize_session({"A": 90.0, "B": 90.9, "C": 91.8})
    assert g["A"] == 0.0
    assert abs(g["B"] - 1.0) < 1e-9  # 0.9 / 90 * 100
    assert abs(g["C"] - 2.0) < 1e-9


# ---- Layer 1: teammate margin -------------------------------------------

def test_teammate_margin_clear_case_is_reliably_faster():
    # 7 rounds, A consistently ~0.5 faster with tiny noise -> CI excludes 0, sign test tiny.
    deltas = [0.5, 0.52, 0.48, 0.51, 0.49, 0.5, 0.5]
    m = ratings.teammate_margin(deltas)
    assert m["n"] == 7
    assert abs(m["mean"] - 0.5) < 0.02
    assert m["ciLow"] > 0
    assert m["winRate"] == 1.0
    assert m["signTestP"] < 0.05
    assert m["verdict"] == "reliably_faster"


def test_teammate_margin_split_is_inconclusive():
    # 5 of 7 in A's favor but noisy -> not a reliable separation (the honest message).
    deltas = [0.3, 0.2, -0.4, 0.1, -0.5, 0.25, 0.15]
    m = ratings.teammate_margin(deltas)
    assert m["winRate"] == round(5 / 7, 3)
    assert m["signTestP"] > 0.10  # 5/7 is not significant
    assert m["verdict"] == "inconclusive"
    assert m["ciLow"] < 0 < m["ciHigh"]  # CI spans zero


def test_teammate_margin_single_round_has_no_interval():
    m = ratings.teammate_margin([0.4])
    assert m["n"] == 1
    assert m["se"] is None and m["ciLow"] is None
    assert m["verdict"] == "inconclusive"


# ---- Layer 3: connectivity / islands ------------------------------------

def test_connectivity_isolated_teams_are_separate_components():
    nodes = {
        "ANT": {(2025, "Mercedes"), (2026, "Mercedes")},
        "RUS": {(2025, "Mercedes"), (2026, "Mercedes")},
        "HAM": {(2025, "Ferrari"), (2026, "Ferrari")},
        "LEC": {(2025, "Ferrari"), (2026, "Ferrari")},
    }
    c = ratings.connectivity(nodes)
    assert len(c["components"]) == 2
    assert ratings.estimable("ANT", "RUS", c) is True
    assert ratings.estimable("ANT", "HAM", c) is False  # different islands


def test_connectivity_shared_driver_bridges_teams():
    nodes = {
        "VER": {(2025, "Red Bull"), (2026, "Red Bull")},
        "HAD": {(2025, "Racing Bulls"), (2026, "Red Bull")},  # the transfer bridge
        "ANT": {(2025, "Mercedes"), (2026, "Mercedes")},
    }
    c = ratings.connectivity(nodes)
    assert ratings.estimable("VER", "HAD", c) is True  # merged via shared (2026, Red Bull)
    assert ratings.estimable("VER", "ANT", c) is False


def test_connectivity_rebrand_does_not_bridge_to_other_teams():
    # Sauber->Audi is continuity (same drivers span it), NOT a cross-team transfer.
    nodes = {
        "BOR": {(2025, "Sauber"), (2026, "Audi")},
        "HUL": {(2025, "Sauber"), (2026, "Audi")},
        "ANT": {(2025, "Mercedes"), (2026, "Mercedes")},
    }
    c = ratings.connectivity(nodes)
    assert ratings.estimable("BOR", "HUL", c) is True  # same Audi/Sauber island
    assert ratings.estimable("BOR", "ANT", c) is False  # does not reach Mercedes


# ---- Layer 2: absolute model recovery -----------------------------------

def test_absolute_model_recovers_within_team_difference():
    # One team, two seasons; A is 0.4 faster than B both years. The model must
    # recover the within-team driver gap (the identified quantity).
    rows = []
    for yr in (2025, 2026):
        car = 1.0 if yr == 2025 else 0.6  # different car level per season
        rows.append({"driver": "A", "teamSeason": (yr, "M"), "gap_pct": car + 0.0})
        rows.append({"driver": "B", "teamSeason": (yr, "M"), "gap_pct": car + 0.4})
    model = ratings.absolute_model(rows)
    theta = model["theta"]
    assert abs((theta["B"] - theta["A"]) - 0.4) < 1e-6


def test_equal_car_grid_ranks_by_driver_effect():
    grid = ratings.equal_car_grid({"A": -0.2, "B": 0.2, "C": -0.1}, {"A": 0, "B": 0, "C": 1})
    assert [g["driver"] for g in grid] == ["A", "C", "B"]  # lower theta = faster
    a = next(g for g in grid if g["driver"] == "A")
    assert a["globalRank"] == 1 and a["componentRank"] == 1


def test_session_bootstrap_brackets_point_estimate():
    rows = []
    for s, yr in enumerate([2025, 2026]):
        for rnd in range(4):
            car = 1.0 if yr == 2025 else 0.6
            rows.append({"session": (yr, rnd), "driver": "A", "teamSeason": (yr, "M"), "gap_pct": car})
            rows.append({"session": (yr, rnd), "driver": "B", "teamSeason": (yr, "M"), "gap_pct": car + 0.4})
    boot = ratings.session_bootstrap(rows, b=200, seed=1)
    # B is reliably slower; its CI should sit above A's (positive theta).
    assert boot["B"]["ciLow"] is not None
    assert boot["B"]["ciLow"] >= boot["A"]["ciHigh"] - 1e-6


def test_absolute_model_flags_cross_island_as_not_estimable():
    rows = [
        {"driver": "A", "teamSeason": (2026, "M"), "gap_pct": 0.0},
        {"driver": "B", "teamSeason": (2026, "M"), "gap_pct": 0.4},
        {"driver": "C", "teamSeason": (2026, "F"), "gap_pct": 0.1},
        {"driver": "D", "teamSeason": (2026, "F"), "gap_pct": 0.5},
    ]
    model = ratings.absolute_model(rows)
    assert model["estimable"](("A", "B")) is True
    assert model["estimable"](("A", "C")) is False  # different islands
