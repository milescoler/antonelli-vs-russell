from src import race_verdict as rv


def test_start_verdict_real_when_winner_gains_and_holds():
    rows = [
        {"role": "A", "code": "ANT", "grid": 3, "lap1Pos": 1, "positionsGained": 2,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 1, "lap1Pos": 2, "positionsGained": -1,
         "finish": 2, "status": "Finished", "dnf": False},
    ]
    v = rv.start_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "real" and v["magnitudeS"] == 2  # places gained (unit=places)
    assert v["magnitudeUnit"] == "places"


def test_start_verdict_inherited_when_rival_dnf():
    rows = [
        {"role": "A", "code": "ANT", "grid": 2, "lap1Pos": 2, "positionsGained": 0,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 5, "lap1Pos": 5, "positionsGained": 0,
         "finish": 2, "status": "Finished", "dnf": False},
        {"role": "WINNER_RIVAL_DNF", "code": "RUS", "grid": 1, "lap1Pos": 1,
         "positionsGained": 0, "finish": None, "status": "Retired", "dnf": True},
    ]
    v = rv.start_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "inherited"


def test_start_verdict_noise_when_small_swing():
    rows = [
        {"role": "A", "code": "ANT", "grid": 1, "lap1Pos": 1, "positionsGained": 0,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 2, "lap1Pos": 2, "positionsGained": 0,
         "finish": 2, "status": "Finished", "dnf": False},
    ]
    assert rv.start_verdict(rows, "ANT", "NOR")["verdict"] == "noise"


def test_pace_verdict_real_on_like_compound_advantage():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "MEDIUM", "medianLaptime_s": 80.0, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "MEDIUM", "medianLaptime_s": 80.4, "nClean": 17},
    ]
    v = rv.pace_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "real" and v["magnitudeS"] < 0  # winner faster per lap


def test_pace_verdict_insufficient_without_shared_compound():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "SOFT", "medianLaptime_s": 80.0, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "HARD", "medianLaptime_s": 80.4, "nClean": 17},
    ]
    assert rv.pace_verdict(rows, "ANT", "NOR")["verdict"] == "insufficient"


def test_tyre_verdict_insufficient_on_small_sample():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "MEDIUM", "degSlope_s_per_lap": 0.03, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "MEDIUM", "degSlope_s_per_lap": None, "nClean": 3},
    ]
    assert rv.tyre_verdict(rows, "ANT", "NOR")["verdict"] == "insufficient"
