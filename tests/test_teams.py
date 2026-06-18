"""Unit tests for src/teams.py — the pure pair-resolution / round-discovery
core. These mock the FastF1 `results` and `schedule` DataFrames so they run
fast and never touch the network or cache."""
from datetime import date

import pandas as pd

from src import teams


def _results(rows):
    """Build a minimal session.results-like DataFrame.
    rows = list of (TeamName, Abbreviation, DriverNumber, FullName)."""
    return pd.DataFrame(
        rows, columns=["TeamName", "Abbreviation", "DriverNumber", "FullName"]
    )


def _schedule(rows):
    """Build a minimal get_event_schedule-like DataFrame.
    rows = list of (RoundNumber, EventName, EventDate, Country, Location, EventFormat)."""
    return pd.DataFrame(
        rows,
        columns=[
            "RoundNumber", "EventName", "EventDate",
            "Country", "Location", "EventFormat",
        ],
    )


# ---- team_slug -----------------------------------------------------------

def test_team_slug_lowercases_and_hyphenates():
    assert teams.team_slug("Mercedes") == "mercedes"
    assert teams.team_slug("Red Bull Racing") == "red-bull-racing"
    assert teams.team_slug("Haas F1 Team") == "haas-f1-team"


# ---- _pairs_from_results -------------------------------------------------

def test_pairs_from_results_orders_a_b_by_car_number():
    df = _results([
        ("Mercedes", "RUS", 63, "George Russell"),
        ("Mercedes", "ANT", 12, "Andrea Kimi Antonelli"),
        ("Ferrari", "LEC", 16, "Charles Leclerc"),
        ("Ferrari", "HAM", 44, "Lewis Hamilton"),
    ])
    pairs = teams._pairs_from_results(df)
    merc = pairs["Mercedes"]
    # Lower car number is always driver A.
    assert merc["a"]["code"] == "ANT" and merc["a"]["number"] == 12
    assert merc["b"]["code"] == "RUS" and merc["b"]["number"] == 63
    assert merc["a"]["number"] < merc["b"]["number"]
    assert merc["a"]["name"] == "Andrea Kimi Antonelli"
    ferr = pairs["Ferrari"]
    assert ferr["a"]["code"] == "LEC" and ferr["b"]["code"] == "HAM"


# ---- _completed_from_schedule -------------------------------------------

def test_next_from_schedule_returns_earliest_future_round():
    sched = _schedule([
        (6, "Monaco Grand Prix", pd.Timestamp("2026-06-07"), "Monaco", "Monte Carlo", "conventional"),
        (7, "Barcelona Grand Prix", pd.Timestamp("2026-06-14"), "Spain", "Barcelona", "conventional"),
        (8, "Austrian Grand Prix", pd.Timestamp("2026-06-28"), "Austria", "Spielberg", "conventional"),
        (9, "British Grand Prix", pd.Timestamp("2026-07-05"), "United Kingdom", "Silverstone", "conventional"),
    ])
    nxt = teams._next_from_schedule(sched, today=date(2026, 6, 17))
    assert nxt["round"] == 8 and nxt["country"] == "Austria"


def test_completed_from_schedule_excludes_round_zero_and_future():
    sched = _schedule([
        (0, "Pre-Season Testing", pd.Timestamp("2026-02-20"), "Bahrain", "Sakhir", "testing"),
        (1, "Australian Grand Prix", pd.Timestamp("2026-03-08"), "Australia", "Melbourne", "conventional"),
        (4, "Miami Grand Prix", pd.Timestamp("2026-05-03"), "United States", "Miami Gardens", "sprint_qualifying"),
        (8, "Austrian Grand Prix", pd.Timestamp("2026-06-28"), "Austria", "Spielberg", "conventional"),
    ])
    out = teams._completed_from_schedule(sched, today=date(2026, 6, 17))
    rounds = [r["round"] for r in out]
    assert rounds == [1, 4]  # round 0 (testing) and round 8 (future) excluded; sorted
    miami = next(r for r in out if r["round"] == 4)
    assert miami["format"] == "sprint_qualifying"
    assert miami["eventName"] == "Miami Grand Prix"


# ---- _canonical_from_round_pairs ----------------------------------------

def _pr(a_code, a_num, b_code, b_num):
    return {
        "a": {"code": a_code, "number": a_num, "name": a_code},
        "b": {"code": b_code, "number": b_num, "name": b_code},
    }


def test_canonical_pair_no_swap():
    rounds = [_pr("ANT", 12, "RUS", 63)] * 3
    canon = teams._canonical_from_round_pairs(rounds)
    assert canon["a"]["code"] == "ANT" and canon["b"]["code"] == "RUS"
    assert canon["hasSwap"] is False


def test_canonical_pair_most_frequent_with_swap():
    # A reserve driver (DOO) stood in for one round; canonical = the majority pair.
    rounds = [
        _pr("ANT", 12, "RUS", 63),
        _pr("ANT", 12, "RUS", 63),
        _pr("ANT", 12, "DOO", 7),
    ]
    canon = teams._canonical_from_round_pairs(rounds)
    assert {canon["a"]["code"], canon["b"]["code"]} == {"ANT", "RUS"}
    assert canon["hasSwap"] is True


def test_canonical_pair_tie_breaks_to_earliest():
    rounds = [_pr("ANT", 12, "RUS", 63), _pr("ANT", 12, "DOO", 7)]
    canon = teams._canonical_from_round_pairs(rounds)
    assert {canon["a"]["code"], canon["b"]["code"]} == {"ANT", "RUS"}
    assert canon["hasSwap"] is True


# ---- _match_prior_round (cross-year circuit matching) --------------------

def _prior(rows):
    """rows = list of (round, country, location)."""
    return [{"round": r, "country": c, "location": loc} for r, c, loc in rows]


def test_match_prior_round_prefers_exact_location():
    prior = _prior([(9, "Spain", "Barcelona"), (6, "United States", "Miami Gardens")])
    # Barcelona matches by location even though 2026 has another Spain round (Madrid).
    assert teams._match_prior_round("Spain", "Barcelona", prior) == 9


def test_match_prior_round_falls_back_to_unique_country():
    # Monaco's location string differs across years ('Monte Carlo' vs 'Monaco'),
    # but Country is unique in the prior season -> still matches.
    prior = _prior([(8, "Monaco", "Monaco"), (10, "Canada", "Montréal")])
    assert teams._match_prior_round("Monaco", "Monte Carlo", prior) == 8


def test_match_prior_round_none_when_ambiguous_country_and_no_location():
    # A US round with no location match and 3 US rounds in prior -> ambiguous -> None.
    prior = _prior([(6, "United States", "Miami Gardens"),
                    (19, "United States", "Austin"),
                    (22, "United States", "Las Vegas")])
    assert teams._match_prior_round("United States", "Unknownville", prior) is None


# ---- _yoy_available ------------------------------------------------------

def test_yoy_available_true_when_same_pair_drove_team_prior_year():
    assert teams._yoy_available({"ANT", "RUS"}, {"ANT", "RUS"}) is True


def test_yoy_available_false_when_a_seat_changed():
    # 2025 the team had RUS + HAM; 2026 it's ANT + RUS -> ANT didn't drive it in 2025.
    assert teams._yoy_available({"ANT", "RUS"}, {"RUS", "HAM"}) is False
