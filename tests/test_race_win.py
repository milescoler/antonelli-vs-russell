import pandas as pd
from src import race_win


def _results(rows):
    cols = ["Position", "Abbreviation", "FullName", "TeamName", "TeamColor", "Time", "Status"]
    return pd.DataFrame(rows, columns=cols)


def test_principals_resolves_winner_p2_and_margin():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished"),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.Timedelta(seconds=8.4), "Finished"),
        (3.0, "LEC", "Charles Leclerc", "Ferrari", "E80020", pd.Timedelta(seconds=12.1), "Finished"),
    ])
    p = race_win.principals_from_results(res)
    assert p["winner"]["code"] == "ANT" and p["p2"]["code"] == "NOR"
    assert p["winner"]["color"] == "#27F4D2"
    assert abs(p["marginS"] - 8.4) < 1e-6
    assert p["anyDnf"] is False


def test_principals_margin_none_when_p2_lapped_and_flags_dnf():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished"),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.NaT, "+1 Lap"),
        (3.0, "RUS", "George Russell", "Mercedes", "27F4D2", pd.NaT, "Retired"),
    ])
    p = race_win.principals_from_results(res)
    assert p["marginS"] is None
    assert p["anyDnf"] is True   # a classified runner did not Finish


def test_assemble_race_has_four_factors_and_placeholder_where():
    principals = {"winner": {"code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "color": "#27F4D2"},
                  "p2": {"code": "NOR", "name": "Lando Norris", "team": "McLaren", "color": "#FF8000"},
                  "marginS": 8.4, "anyDnf": False, "winnerStatus": "Finished", "p2Status": "Finished"}
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
