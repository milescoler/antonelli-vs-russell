import pandas as pd
from src import web_export, run
import config


def _results():
    return pd.DataFrame([
        {"Abbreviation": "RUS", "TeamName": "Mercedes", "TeamColor": "27F4D2", "GridPosition": 1},
        {"Abbreviation": "ANT", "TeamName": "Mercedes", "TeamColor": "27F4D2", "GridPosition": 2},
        {"Abbreviation": "NOR", "TeamName": "McLaren",  "TeamColor": "FF8000", "GridPosition": 3},
        {"Abbreviation": "PIA", "TeamName": "McLaren",  "TeamColor": "FF8000", "GridPosition": 5},
        {"Abbreviation": "VER", "TeamName": "Red Bull", "TeamColor": "3671C6", "GridPosition": 4},
        # Red Bull second car DNS / not classified -> single driver, excluded as a pair.
    ])


def test_teammate_pairs_groups_by_team_and_orders_by_grid():
    pairs = web_export.teammate_pairs(_results())
    keys = {(p["team"], p["a"], p["b"]) for p in pairs}
    assert ("Mercedes", "RUS", "ANT") in keys      # RUS grid 1 < ANT grid 2 -> A=RUS
    assert ("McLaren", "NOR", "PIA") in keys
    # Single-car team yields no pair.
    assert all(p["team"] != "Red Bull" for p in pairs)
    # Color is hex-prefixed.
    merc = next(p for p in pairs if p["team"] == "Mercedes")
    assert merc["teamColor"] == "#27F4D2"


def test_matchup_payload_shape_and_reconciliation():
    res = run.run_pipeline(use_synthetic=True, driver_a="RUS", driver_b="ANT")
    meta = {"slug": "canadian", "eventName": "Synthetic GP", "round": 5,
            "year": config.YEAR, "session": "Q",
            "driverAName": "George Russell", "driverBName": "Kimi Antonelli",
            "team": "Mercedes", "teamColor": "#27F4D2"}
    max_points = 120
    p = web_export.matchup_payload(res, meta, max_points=max_points)

    # meta echoes identity + reconciles
    assert p["meta"]["driverA"]["code"] == "RUS"
    assert p["meta"]["driverB"]["code"] == "ANT"
    assert abs(p["meta"]["reconResidualS"]) <= config.RECONCILE_TOLERANCE_S
    # curve is downsampled, ends at the official gap, starts at 0
    assert len(p["deltaCurve"]) <= 120
    assert p["deltaCurve"][0]["delta"] == 0.0
    assert abs(p["deltaCurve"][-1]["delta"] - p["meta"]["officialGapS"]) <= config.RECONCILE_TOLERANCE_S
    # one sector row per micro-sector, each carries a CI + significance flag
    assert len(p["sectors"]) == len(res["table"])
    s0 = p["sectors"][0]
    assert {"i", "midM", "deltaMean", "ciLow", "ciHigh", "significant"} <= set(s0)
    # callouts: noiseTrap is None or an int sector id; topSignificant is a list
    assert isinstance(p["callouts"]["topSignificant"], list)
    # track points carry x/y/rate
    assert {"x", "y", "rate"} <= set(p["track"][0])


def test_build_index_separates_valid_and_excluded():
    races = [{"slug": "canadian", "name": "Canadian Grand Prix", "round": 5}]
    entries = [
        {"key": "canadian__RUS_ANT", "race": "canadian", "team": "Mercedes",
         "teamColor": "#27F4D2", "a": "RUS", "b": "ANT",
         "valid": True, "officialGapS": -0.07, "significantCount": 3},
        {"key": "barcelona__RUS_ANT", "race": "barcelona", "team": "Mercedes",
         "teamColor": "#27F4D2", "a": "RUS", "b": "ANT",
         "valid": False, "reason": "No clean laps for one of the drivers"},
    ]
    idx = web_export.build_index("canadian__RUS_ANT", races, entries)
    assert idx["hero"] == "canadian__RUS_ANT"
    assert idx["matchups"][0]["key"] == "barcelona__RUS_ANT"   # sorted by key
    excluded = [m for m in idx["matchups"] if not m["valid"]]
    assert excluded and "reason" in excluded[0]


def test_matchup_key():
    assert web_export.matchup_key("canadian", "RUS", "ANT") == "canadian__RUS_ANT"
