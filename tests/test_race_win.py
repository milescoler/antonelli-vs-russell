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
