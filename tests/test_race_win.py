import pandas as pd
from src import race_win


def _results(rows):
    cols = ["Position", "Abbreviation", "FullName", "TeamName", "TeamColor", "Time", "Status",
            "GridPosition"]
    return pd.DataFrame(rows, columns=cols)


def test_principals_resolves_winner_p2_and_margin():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished", 1.0),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.Timedelta(seconds=8.4), "Finished", 2.0),
        (3.0, "LEC", "Charles Leclerc", "Ferrari", "E80020", pd.Timedelta(seconds=12.1), "Finished", 3.0),
    ])
    p = race_win.principals_from_results(res)
    assert p["winner"]["code"] == "ANT" and p["p2"]["code"] == "NOR"
    assert p["winner"]["color"] == "#27F4D2"
    assert abs(p["marginS"] - 8.4) < 1e-6
    assert p["anyDnf"] is False


def test_principals_margin_none_when_p2_lapped_and_flags_dnf():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished", 1.0),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.NaT, "+1 Lap", 2.0),
        (3.0, "RUS", "George Russell", "Mercedes", "27F4D2", pd.NaT, "Retired", 3.0),
    ])
    p = race_win.principals_from_results(res)
    assert p["marginS"] is None
    assert p["anyDnf"] is True   # a classified runner did not Finish


def test_inherited_win_detected_when_polesitter_retires():
    """Polesitter (GridPosition==1) retires; a different driver wins → inherited."""
    res = _results([
        (1.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.Timedelta(0), "Finished", 5.0),
        (2.0, "LEC", "Charles Leclerc", "Ferrari", "E80020", pd.Timedelta(seconds=5.2), "Finished", 2.0),
        (3.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.NaT, "Retired", 1.0),
    ])
    p = race_win.principals_from_results(res)
    assert p["winnerInherited"] is True
    assert p["poleSitter"] == "ANT"
    assert p["winnerStartedPole"] is False
    assert p["anyDnf"] is True


def test_pole_to_flag_win_not_inherited():
    """Winner started from pole (GridPosition==1) and finished → not inherited."""
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished", 1.0),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.Timedelta(seconds=8.4), "Finished", 2.0),
        (3.0, "LEC", "Charles Leclerc", "Ferrari", "E80020", pd.Timedelta(seconds=12.1), "Finished", 3.0),
    ])
    p = race_win.principals_from_results(res)
    assert p["winnerInherited"] is False
    assert p["winnerStartedPole"] is True
    assert p["poleSitter"] == "ANT"


def test_assemble_race_has_four_factors_and_placeholder_where():
    principals = {"winner": {"code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "color": "#27F4D2"},
                  "p2": {"code": "NOR", "name": "Lando Norris", "team": "McLaren", "color": "#FF8000"},
                  "marginS": 8.4, "anyDnf": False, "winnerStatus": "Finished", "p2Status": "Finished",
                  "winnerInherited": False, "poleSitter": "ANT", "winnerStartedPole": True}
    start_df = pd.DataFrame([
        ("R", "ANT", "ANT", 3, 1, 2, 1.0, "Finished"),
        ("R", "RUS", "NOR", 1, 2, -1, 2.0, "Finished"),
        ("R", "P2", "NOR", 1, 2, -1, 2.0, "Finished"),
    ], columns=["race", "driver", "code", "grid", "lap1_pos", "positions_gained", "finish", "status"])
    stint_df = pd.DataFrame([
        ("R", "ANT", 1, "MEDIUM", 80.0, 18), ("R", "NOR", 1, "MEDIUM", 80.4, 17),
    ], columns=["race", "driver", "stint", "compound", "median_laptime_s", "n_clean"])
    deg_df = pd.DataFrame([
        ("R", "ANT", 1, "MEDIUM", 0.030, 18), ("R", "NOR", 1, "MEDIUM", 0.045, 17),
    ], columns=["race", "driver", "stint", "compound", "deg_slope_s_per_lap", "n_clean"])
    gap_df = pd.DataFrame([("R", 1, -1.2, True), ("R", 2, -2.0, True)],
                          columns=["race", "lap", "gap_s", "leading"])

    out = race_win.assemble_race(principals=principals, start_df=start_df, stint_df=stint_df,
                                 deg_df=deg_df, gap_df=gap_df, round_number=5, slug="canadian",
                                 event_name="Canadian Grand Prix", year=2026)
    assert set(out["factors"]) == {"where", "tyre", "pace", "start"}
    assert out["factors"]["where"]["verdict"] == "insufficient"   # placeholder
    assert out["factors"]["pace"]["verdict"] == "real"
    assert out["meta"]["marginS"] == 8.4
    assert "stintPace" in out["factors"]["tyre"] or "stints" in out["factors"]["tyre"]


def test_verdict_from_where_real_when_sector_significant():
    """verdict_from_where returns 'real' when at least one sector is significant."""
    payload = {
        "meta": {
            "nPairs": 10,
            "nUniqueLapsA": 8,
            "nUniqueLapsB": 7,
            "winnerCode": "ANT",
            "p2Code": "RUS",
            "driverA": {"code": "ANT"},
            "driverB": {"code": "RUS"},
            "marginCurveS": -1.23,
        },
        "sectors": [
            {"i": 1, "deltaMean": -0.15, "ciLow": -0.25, "ciHigh": -0.05, "significant": True, "faster": "ANT"},
            {"i": 2, "deltaMean": 0.02, "ciLow": -0.08, "ciHigh": 0.12, "significant": False, "faster": "RUS"},
        ],
        "attribution": [],
        "callouts": {"topSignificant": [1], "noiseTrap": 2},
        "deltaCurve": [],
        "corners": [],
        "track": [],
    }
    v = race_win.verdict_from_where(payload)
    assert v["verdict"] == "real"
    assert v["magnitudeS"] is not None
    assert abs(v["magnitudeS"] - (-0.15)) < 1e-9
    assert "ANT" in v["headline"]
    assert "1 of 2" in v["headline"]
    assert "8 vs 7" in v["caveat"]


def test_verdict_from_where_insufficient_passthrough():
    """verdict_from_where passes through an 'insufficient' payload unchanged."""
    payload = {
        "verdict": "insufficient",
        "reason": "fewer than 4 comparable laps",
    }
    v = race_win.verdict_from_where(payload)
    assert v["verdict"] == "insufficient"
    assert v["magnitudeS"] is None
    assert "too few" in v["headline"]
    assert v["caveat"] == "fewer than 4 comparable laps"


def test_verdict_from_where_noise_when_no_significant_sectors():
    """verdict_from_where returns 'noise' when no sector is significant."""
    payload = {
        "meta": {
            "nPairs": 5,
            "nUniqueLapsA": 4,
            "nUniqueLapsB": 3,
            "winnerCode": "NOR",
            "p2Code": "ANT",
            "driverA": {"code": "NOR"},
            "driverB": {"code": "ANT"},
            "marginCurveS": -0.5,
        },
        "sectors": [
            {"i": 1, "deltaMean": -0.03, "ciLow": -0.10, "ciHigh": 0.04, "significant": False, "faster": "NOR"},
        ],
        "attribution": [],
        "callouts": {"topSignificant": [], "noiseTrap": 1},
        "deltaCurve": [],
        "corners": [],
        "track": [],
    }
    v = race_win.verdict_from_where(payload)
    assert v["verdict"] == "noise"
    assert v["magnitudeS"] is None
    assert "0 of 1" in v["headline"]


def test_index_entry_marks_valid_and_excluded():
    from importlib.util import spec_from_file_location, module_from_spec
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    spec = spec_from_file_location("build_race", root / "scripts" / "build_race_decomp_data.py")
    mod = module_from_spec(spec); spec.loader.exec_module(mod)
    valid = mod.index_entry(slug="canadian", round_number=5, payload={
        "meta": {"winner": {"code": "ANT"}, "p2": {"code": "NOR"}, "marginS": 8.4},
        "factors": {"where": {"verdict": "insufficient"}, "tyre": {"verdict": "noise"},
                    "pace": {"verdict": "real"}, "start": {"verdict": "real"}}})
    assert valid["valid"] is True and valid["realFactorCount"] == 2 and valid["slug"] == "canadian"
    excl = mod.index_entry(slug="japanese", round_number=3, reason="no classified P2")
    assert excl["valid"] is False and excl["reason"] == "no classified P2"
