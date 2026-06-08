"""Cross-year track-history tests. Invariants on real cached/loadable results
(no brittle magic numbers except deliberate definitional checks). Skips if the
historical cache can't be reached.

NOTE: this analysis runs on the project's synthetic '2026-world' data source;
assertions check the METRIC DEFINITIONS, not real-world F1 history."""
import math
import pytest
import pandas as pd

from src.loaders import setup_cache
from src import track_history as th

CACHE = "fastf1_cache"


@pytest.fixture(scope="module", autouse=True)
def _cache():
    setup_cache(CACHE)


def test_load_results_columns_and_classification():
    try:
        df = th.load_results(2024, "Monaco")
    except Exception as e:
        pytest.skip(f"Historical results unavailable: {e!r}")
    for col in ["year", "round", "track", "driver", "team", "grid",
                "finish", "status", "classified"]:
        assert col in df.columns
    assert df["classified"].dtype == bool
    p1 = df[df["finish"] == 1].iloc[0]
    assert bool(p1["classified"]) is True


def test_season_table_spans_multiple_rounds():
    try:
        st = th.season_table(2024)
    except Exception as e:
        pytest.skip(f"Historical schedule/results unavailable: {e!r}")
    assert st["round"].nunique() > 5
    assert {"year", "round", "driver", "team", "grid", "finish",
            "classified"}.issubset(st.columns)
    assert not st.duplicated(subset=["round", "driver"]).any()


def _toy_season(year, track_round=2):
    """Hand-built season table to test the metric arithmetic exactly.
    DRV1: finishes 2 at the track, [4,6] elsewhere -> baseline 5, delta +3.
    DRV2: DNF at the track (excluded) -> no delta.
    DRV3: only ran the track round -> no baseline -> dropped."""
    rows = [
        # driver, round, finish, classified
        ("DRV1", track_round, 2, True),
        ("DRV1", 1, 4, True),
        ("DRV1", 3, 6, True),
        ("DRV2", track_round, 18, False),   # DNF at track
        ("DRV2", 1, 5, True),
        ("DRV3", track_round, 1, True),      # only appears at the track
    ]
    return pd.DataFrame([
        {"year": year, "round": r,
         "track": "TrackX" if r == track_round else f"R{r}",
         "driver": d, "team": d + "team", "grid": f, "finish": f,
         "status": "Finished" if c else "Accident", "classified": c}
        for d, r, f, c in rows
    ])


def test_driver_affinity_arithmetic_and_dnf_and_baseline(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.driver_track_affinity("TrackX", [2099], metric="finish")
    by = df.set_index("driver")
    # DRV1: baseline mean(4,6)=5, track=2 -> affinity +3.
    assert math.isclose(by.loc["DRV1", "affinity"], 3.0)
    assert int(by.loc["DRV1", "n_years"]) == 1
    # DRV2 (DNF at track) and DRV3 (no baseline) must NOT appear.
    assert "DRV2" not in by.index
    assert "DRV3" not in by.index


def test_driver_affinity_small_n_flag(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.driver_track_affinity("TrackX", [2099], metric="finish")
    assert bool(df.set_index("driver").loc["DRV1", "small_n"]) is True  # 1 < 3


def test_team_affinity_uses_shared_engine(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.team_track_affinity("TrackX", [2099], metric="finish")
    assert math.isclose(df.set_index("team").loc["DRV1team", "affinity"], 3.0)


def test_track_leaderboard_columns_and_sort():
    try:
        lb = th.track_leaderboard("Monaco", [2022, 2023, 2024])
    except Exception as e:
        pytest.skip(f"Historical results unavailable: {e!r}")
    for col in ["driver", "n_starts", "wins", "podiums", "mean_finish", "mean_grid"]:
        assert col in lb.columns
    assert (lb["wins"] >= 0).all()
    assert lb["wins"].is_monotonic_decreasing
