from src import season_stats as ss

def test_normalize_session_pct_off_fastest():
    g = ss.normalize_session({"A": 90.0, "B": 90.9})
    assert g["A"] == 0.0 and abs(g["B"] - 1.0) < 1e-9

def test_constructors_table_sums_team_points():
    drivers = [
        {"code": "VER", "team": "Red Bull", "teamColor": "#1", "points": 25, "wins": 1, "podiums": 1},
        {"code": "HAD", "team": "Red Bull", "teamColor": "#1", "points": 8, "wins": 0, "podiums": 0},
        {"code": "NOR", "team": "McLaren", "teamColor": "#2", "points": 18, "wins": 0, "podiums": 1},
    ]
    t = ss.constructors_table(drivers)
    assert [c["team"] for c in t] == ["Red Bull", "McLaren"]
    assert t[0]["points"] == 33 and t[0]["wins"] == 1 and t[0]["podiums"] == 1

def test_pace_table_ranks_by_mean_ascending():
    rows = [
        {"round": 1, "code": "A", "name": "A", "team": "T", "teamColor": "#1", "gap_pct": 0.0},
        {"round": 2, "code": "A", "name": "A", "team": "T", "teamColor": "#1", "gap_pct": 0.2},
        {"round": 1, "code": "B", "name": "B", "team": "T", "teamColor": "#1", "gap_pct": 0.5},
    ]
    out = ss.pace_table(rows)
    assert out[0]["code"] == "A" and out[0]["rank"] == 1
    assert abs(out[0]["mean"] - 0.1) < 1e-9
    assert out[0]["byRound"] == [{"round": 1, "value": 0.0}, {"round": 2, "value": 0.2}]
