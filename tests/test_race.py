"""
Race-session analysis tests. Invariant checks on real cached telemetry
(no exact-value brittleness), plus Canada and Monaco end-to-end regression
anchors — the two races the "how he wins" reframe hinges on (Canada: started
P2, led by lap 2, won after Russell retired; Monaco: pole to flag-to-flag win).
"""
from pathlib import Path
import pytest

from src.loaders import setup_cache
from src import race

CACHE_DIR = Path(__file__).resolve().parent.parent / "fastf1_cache"
CANADA_DIR = CACHE_DIR / "2026" / "2026-05-24_Canadian_Grand_Prix"
MONACO_DIR = CACHE_DIR / "2026" / "2026-06-07_Monaco_Grand_Prix"


@pytest.fixture(scope="module", autouse=True)
def _enable_cache():
    if not (CANADA_DIR.exists() and MONACO_DIR.exists()):
        pytest.skip("FastF1 cache not populated for Canada/Monaco 2026.")
    setup_cache(str(CACHE_DIR))


def test_load_race_session_has_laps():
    session = race.load_race_session(2026, "Canada")
    assert session.laps is not None
    assert len(session.laps) > 0


def test_get_clean_laps_are_green_and_exclude_lap1_and_pits():
    session = race.load_race_session(2026, "Canada")
    clean = race.get_clean_laps(session, "ANT")
    assert (clean["TrackStatus"] == "1").all()
    assert (clean["LapNumber"] != 1).all()
    assert clean["PitInTime"].isna().all()
    assert clean["PitOutTime"].isna().all()
    assert len(clean) > 0
    assert clean["LapTime"].notna().all()


def test_start_summary_canada_anchor():
    df = race.start_summary(2026, "Canada")
    ant = df[df["driver"] == "ANT"].iloc[0]
    assert int(ant["grid"]) == 2
    assert int(ant["lap1_pos"]) == 2
    assert int(ant["finish"]) == 1
    assert int(ant["positions_gained"]) == int(ant["grid"]) - int(ant["lap1_pos"])
    assert "P2" in set(df["driver"])
    p2 = df[df["driver"] == "P2"].iloc[0]
    assert p2["code"] == "HAM"


def test_start_summary_monaco_anchor():
    # Monaco is the cleanest "pure win" case: pole to victory, no inheritance.
    df = race.start_summary(2026, "Monaco")
    ant = df[df["driver"] == "ANT"].iloc[0]
    assert int(ant["grid"]) == 1
    assert int(ant["lap1_pos"]) == 1
    assert int(ant["finish"]) == 1
    p2 = df[df["driver"] == "P2"].iloc[0]
    assert p2["code"] == "HAM"


def test_stint_pace_columns_and_plausible():
    df = race.stint_pace(2026, "Canada", ["ANT", "RUS"])
    assert {"driver", "stint", "compound", "median_laptime_s", "n_clean"}.issubset(df.columns)
    assert len(df) > 0
    # Median lap times are plausible race laps for Montreal (~70-95 s).
    assert df["median_laptime_s"].between(60, 110).all()


def test_tire_deg_small_n_guard_and_columns():
    df = race.tire_deg(2026, "Canada", ["ANT", "RUS"])
    assert race.MIN_DEG_LAPS == 5
    assert {"driver", "stint", "compound", "deg_slope_s_per_lap", "n_clean"}.issubset(df.columns)
    short = df[df["n_clean"] < race.MIN_DEG_LAPS]
    assert short["deg_slope_s_per_lap"].isna().all()
    enough = df[df["n_clean"] >= race.MIN_DEG_LAPS]
    assert enough["deg_slope_s_per_lap"].notna().all()


def test_gap_to_rival_leading_flag_and_columns():
    df = race.gap_to_rival(2026, "Canada", "ANT")
    assert {"lap", "gap_s", "leading"}.issubset(df.columns)
    assert df["leading"].any()
    assert (df.loc[df["leading"], "gap_s"] <= 0).all()
    assert df["lap"].is_monotonic_increasing
