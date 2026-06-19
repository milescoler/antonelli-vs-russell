import pandas as pd
from src import web_export


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
