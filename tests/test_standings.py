"""Unit tests for the pure championship-standings aggregation."""
from src.standings import build_standings


def _r(code, pos, points, team="T", color="#fff", status="Finished", grid=None):
    return {
        "code": code, "name": code, "team": team, "teamColor": color,
        "pos": pos, "grid": grid, "points": points, "status": status,
    }


# ---- standings -----------------------------------------------------------

def test_build_standings_sums_points_and_ranks_by_points():
    per_round = [
        [_r("VER", 1, 25), _r("HAM", 2, 18), _r("NOR", 3, 15)],
        [_r("VER", 1, 25), _r("HAM", 2, 18), _r("NOR", 4, 12)],
    ]
    s = build_standings(per_round)
    assert [d["code"] for d in s] == ["VER", "HAM", "NOR"]
    assert s[0]["points"] == 50 and s[0]["wins"] == 2
    assert s[1]["points"] == 36
    by = {d["code"]: d for d in s}
    assert by["NOR"]["podiums"] == 1  # P3 once, P4 once
    assert by["HAM"]["avgFinish"] == 2.0
    assert by["VER"]["bestFinish"] == 1


def test_build_standings_handles_dnf_none_position():
    per_round = [[_r("ALO", None, 0, status="Retired"), _r("STR", 5, 10)]]
    s = build_standings(per_round)
    alo = next(d for d in s if d["code"] == "ALO")
    assert alo["avgFinish"] is None  # no classified finish
    assert alo["finishes"] == [None]
    assert alo["wins"] == 0 and alo["podiums"] == 0
