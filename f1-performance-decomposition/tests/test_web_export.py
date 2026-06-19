import json
from pathlib import Path

import pandas as pd
from src import web_export, run
import config

_HERO_SLUG = "canadian"
_HERO_A, _HERO_B = "RUS", "ANT"


def _build_synthetic_demo(out_dir: Path) -> None:
    """Inline reimplementation of the deleted build_decomp_data.py helper."""
    res = run.run_pipeline(use_synthetic=True, driver_a=_HERO_A, driver_b=_HERO_B)
    meta = {"slug": _HERO_SLUG, "eventName": "Synthetic GP", "round": 0,
            "year": config.YEAR, "session": "Q",
            "driverAName": _HERO_A, "driverBName": _HERO_B,
            "team": "Synthetic", "teamColor": "#27F4D2"}
    key = web_export.matchup_key(_HERO_SLUG, _HERO_A, _HERO_B)
    payload = web_export.matchup_payload(res, meta)
    (out_dir / f"{key}.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    entries = [{
        "key": key, "race": _HERO_SLUG, "team": "Synthetic", "teamColor": "#27F4D2",
        "a": _HERO_A, "b": _HERO_B, "valid": True,
        "officialGapS": payload["meta"]["officialGapS"],
        "significantCount": sum(1 for s in payload["sectors"] if s["significant"]),
    }]
    races = [{"slug": _HERO_SLUG, "name": "Synthetic GP", "round": 0}]
    (out_dir / "index.json").write_text(
        json.dumps(web_export.build_index(key, races, entries),
                   sort_keys=True, indent=2, ensure_ascii=False) + "\n")


def test_synthetic_demo_writes_valid_json(tmp_path):
    _build_synthetic_demo(tmp_path)

    index = json.loads((tmp_path / "index.json").read_text())
    assert index["hero"] in {m["key"] for m in index["matchups"]}
    hero = next(m for m in index["matchups"] if m["key"] == index["hero"])
    assert hero["valid"] is True

    payload = json.loads((tmp_path / f"{index['hero']}.json").read_text())
    assert payload["deltaCurve"][0]["delta"] == 0.0
    assert "sectors" in payload and "callouts" in payload


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


def test_faster_field_follows_sign_convention():
    res = run.run_pipeline(use_synthetic=True, driver_a="RUS", driver_b="ANT")
    meta = {"slug": "canadian", "eventName": "Synthetic GP", "round": 5,
            "year": config.YEAR, "session": "Q",
            "driverAName": "George Russell", "driverBName": "Kimi Antonelli",
            "team": "Mercedes", "teamColor": "#27F4D2"}
    p = web_export.matchup_payload(res, meta)
    for s in p["sectors"]:
        dm = s["deltaMean"]
        if dm is None:
            assert s["faster"] is None
        elif dm > 0:
            assert s["faster"] == "ANT"   # A=RUS slower => B=ANT faster
        elif dm < 0:
            assert s["faster"] == "RUS"   # A=RUS faster
    # noiseTrap, if present, is the largest-|deltaMean| insignificant sector
    noise = [s for s in p["sectors"] if not s["significant"] and s["deltaMean"] is not None]
    if noise:
        want = max(noise, key=lambda s: abs(s["deltaMean"]))["i"]
        assert p["callouts"]["noiseTrap"] == want
