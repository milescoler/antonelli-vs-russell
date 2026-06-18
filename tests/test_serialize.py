"""Unit tests for src/serialize.py — pure DataFrame -> JSON-ready dict functions.
All inputs are hand-built DataFrames matching the columns the analysis modules
emit, so these are fast and FastF1-free."""
import json
import math

import numpy as np
import pandas as pd

from src import serialize


# ---- _num ----------------------------------------------------------------

def test_num_maps_nan_and_inf_to_none():
    assert serialize._num(float("nan")) is None
    assert serialize._num(np.nan) is None
    assert serialize._num(float("inf")) is None
    assert serialize._num(pd.NA) is None


def test_num_rounds_floats():
    assert serialize._num(1.23456, 3) == 1.235
    assert serialize._num(75.0, 3) == 75.0


# ---- segment category means ----------------------------------------------

def _segments(rows):
    cols = ["Segment", "kind", "start_m", "end_m", "min_speed",
            "time_a_s", "time_b_s", "delta_s", "category", "sensor_ok"]
    return pd.DataFrame(rows, columns=cols)


def test_segment_category_means_excludes_sensor_bad_and_orders():
    df = _segments([
        ("S1", "straight", 0, 100, 250, 1.0, 1.04, 0.04, "straight", True),
        ("S2", "straight", 100, 200, 250, 1.0, 1.02, 0.02, "straight", True),
        ("C1", "corner", 200, 260, 90, 1.0, 1.11, 0.11, "slow_corner", True),
        # sensor-bad row must be excluded from the mean:
        ("C2", "corner", 260, 320, 95, 1.0, 9.99, 8.99, "slow_corner", False),
    ])
    means = serialize.serialize_segment_category_means(df)
    cats = [m["category"] for m in means]
    # fixed enum order, only categories with data present
    assert cats == ["straight", "slow_corner"]
    straight = means[0]
    assert straight["nSegments"] == 2
    assert straight["meanDelta_s"] == 0.03  # (0.04+0.02)/2
    slow = means[1]
    assert slow["nSegments"] == 1  # the sensor-bad C2 excluded
    assert slow["meanDelta_s"] == 0.11


# ---- corner signature buckets --------------------------------------------

def _corners(rows):
    cols = ["race", "corner", "distance_m", "apex_a_kph", "apex_b_kph",
            "mean_apex_kph", "apex_delta_kph", "brake_on_a", "brake_on_b",
            "brake_on_delta", "throttle_full_a", "throttle_full_b",
            "throttle_full_delta", "sensor_ok"]
    return pd.DataFrame(rows, columns=cols)


def test_corner_buckets_group_by_speed_category():
    df = _corners([
        # slow (<130): two corners
        ("R", 1, 250, 80, 78, 80, 2.0, 30, 34, -4.0, 10, 12, -2.0, True),
        ("R", 2, 600, 90, 92, 90, -2.0, 28, 30, -2.0, 8, 8, 0.0, True),
        # fast (>=200): one corner
        ("R", 3, 1200, 220, 219, 220, 1.0, 40, 40, 0.0, 5, 6, -1.0, True),
        # sensor-bad excluded:
        ("R", 4, 1500, 85, 85, 85, 9.0, 9, 9, 9.0, 9, 9, 9.0, False),
    ])
    buckets = {b["category"]: b for b in serialize.serialize_corner_buckets(df)}
    assert "slow_corner" in buckets and "fast_corner" in buckets
    assert buckets["slow_corner"]["nCorners"] == 2
    assert buckets["slow_corner"]["apexDeltaKph_mean"] == 0.0  # (2 + -2)/2
    assert buckets["slow_corner"]["brakeOnDelta_m_mean"] == -3.0  # (-4 + -2)/2
    assert buckets["fast_corner"]["nCorners"] == 1


# ---- start conversion (A/B remap by CODE, DNF handling) ------------------

def _start(rows):
    cols = ["race", "driver", "code", "grid", "lap1_pos",
            "positions_gained", "finish", "status"]
    return pd.DataFrame(rows, columns=cols)


def test_serialize_start_remaps_roles_by_code_not_label():
    # Ferrari pair LEC/HAM. start_summary labels the teammate roles 'ANT'/'RUS'
    # regardless of who they are; the real codes are in `code`. We must map by code.
    df = _start([
        ("R", "ANT", "LEC", 4, 4, 0, 3.0, "Finished"),
        ("R", "RUS", "HAM", 2, 2, 0, 1.0, "Finished"),
        ("R", "P2", "RUS", 1, 1, 0, 2.0, "Finished"),
    ])
    out = serialize.serialize_start(df, a_code="LEC", b_code="HAM")
    by_role = {r["role"]: r for r in out}
    assert by_role["A"]["code"] == "LEC"
    assert by_role["B"]["code"] == "HAM"
    assert by_role["P2"]["code"] == "RUS"


def test_serialize_start_marks_dnf_and_nulls_finish():
    df = _start([
        ("R", "ANT", "ANT", 3, 2, 1, float("nan"), "Retired"),
        ("R", "RUS", "RUS", 1, 1, 0, 2.0, "Finished"),
        ("R", "P2", "HAM", 2, 3, -1, 1.0, "Finished"),
    ])
    out = serialize.serialize_start(df, a_code="ANT", b_code="RUS")
    a = next(r for r in out if r["role"] == "A")
    assert a["dnf"] is True
    assert a["finish"] is None
    b = next(r for r in out if r["role"] == "B")
    assert b["dnf"] is False
    assert b["finish"] == 2


# ---- tire deg (NaN slope -> null) ----------------------------------------

def _deg(rows):
    cols = ["race", "driver", "stint", "compound", "deg_slope_s_per_lap", "n_clean"]
    return pd.DataFrame(rows, columns=cols)


def test_serialize_tire_deg_nulls_small_sample_slope():
    df = _deg([
        ("R", "ANT", 1, "MEDIUM", 0.031, 18),
        ("R", "RUS", 1, "MEDIUM", float("nan"), 3),
    ])
    out = serialize.serialize_tire_deg(df)
    short = next(r for r in out if r["code"] == "RUS")
    assert short["degSlope_s_per_lap"] is None
    assert short["nClean"] == 3


# ---- gap trace (columnar, sign convention) -------------------------------

def test_serialize_gap_trace_is_columnar_and_keeps_sign():
    df = pd.DataFrame(
        [("R", 1, -1.2, True), ("R", 2, -1.5, True), ("R", 3, 0.4, False)],
        columns=["race", "lap", "gap_s", "leading"],
    )
    out = serialize.serialize_gap_trace(df, "ANT")
    assert out["driverCode"] == "ANT"
    assert out["laps"] == [1, 2, 3]
    assert out["gap_s"] == [-1.2, -1.5, 0.4]
    assert out["leading"] == [True, True, False]
    # leading laps have gap_s <= 0
    for g, lead in zip(out["gap_s"], out["leading"]):
        if lead:
            assert g <= 0


# ---- qualifying round: invariant survives, sign convention ---------------

def _meta(lap_delta):
    return {
        "year": 2026, "round": 1, "event_name": "Australian Grand Prix",
        "lap_time_a_s": 78.518, "lap_time_b_s": 78.518 + lap_delta,
        "lap_delta_s": lap_delta, "q_session_a": 3, "q_session_b": 3,
        "q_mismatch": False,
    }


def test_qualifying_round_segment_means_reconstruct_lap_delta():
    segs = _segments([
        ("S1", "straight", 0, 100, 250, 1.0, 1.10, 0.10, "straight", True),
        ("C1", "corner", 100, 160, 90, 1.0, 1.08, 0.08, "slow_corner", True),
        ("C2", "corner", 160, 220, 160, 1.0, 1.12, 0.12, "medium_corner", True),
    ])
    lap_delta = 0.10 + 0.08 + 0.12  # all sensor_ok -> sum equals lap delta
    compare_result = {"segments": segs, "meta": _meta(lap_delta)}
    corners = _corners([])
    out = serialize.serialize_qualifying_round(
        compare_result, corners, round_number=1,
        event_name="Australian Grand Prix", a_code="ANT", b_code="RUS",
        is_canonical=True,
    )
    assert out["lapDelta_s"] == round(lap_delta, 3)
    assert out["pairThisRound"] == {"aCode": "ANT", "bCode": "RUS"}
    # positive lapDelta => A faster (sign convention preserved)
    assert out["lapDelta_s"] > 0
    reconstructed = sum(m["meanDelta_s"] * m["nSegments"] for m in out["segmentCategoryMeans"])
    assert math.isclose(reconstructed, lap_delta, abs_tol=1e-6)


def test_qualifying_round_flags_qmismatch_and_sensor_freeze():
    segs = _segments([
        ("S1", "straight", 0, 100, 250, 1.0, 1.10, 0.10, "straight", True),
        ("C1", "corner", 100, 160, 90, 1.0, 9.0, 8.0, "slow_corner", False),
    ])
    meta = _meta(0.1)
    meta["q_mismatch"] = True
    out = serialize.serialize_qualifying_round(
        {"segments": segs, "meta": meta}, _corners([]), round_number=1,
        event_name="X", a_code="ANT", b_code="RUS", is_canonical=True,
    )
    assert out["caveats"]["qMismatch"] is True
    assert out["caveats"]["sensorFreezeAny"] is True


# ---- YoY -----------------------------------------------------------------

def test_build_yoy_none_when_no_overlapping_rounds():
    q2026 = [{"round": 7, "lapDelta_s": -0.3}]
    q2025 = [{"round": 1, "lapDelta_s": 0.2}]
    assert serialize.build_yoy(q2026, q2025) is None


def test_build_yoy_computes_delta_of_means_over_overlap():
    q2026 = [{"round": 1, "lapDelta_s": 0.30}, {"round": 2, "lapDelta_s": 0.10}]
    q2025 = [{"round": 1, "lapDelta_s": 0.10}, {"round": 2, "lapDelta_s": 0.10},
             {"round": 9, "lapDelta_s": 5.0}]
    yoy = serialize.build_yoy(q2026, q2025)
    assert yoy["nRoundsCompared"] == 2
    assert yoy["meanLapDelta_s_2026"] == 0.20
    assert yoy["meanLapDelta_s_2025"] == 0.10
    assert yoy["deltaOfDeltas_s"] == 0.10


# ---- track geometry ------------------------------------------------------

def _path(rows):
    """rows = list of (Distance, X, Y)."""
    return pd.DataFrame(rows, columns=["Distance", "X", "Y"])


def test_serialize_track_attaches_segment_delta_to_points():
    path = _path([(0, 0, 0), (50, 10, 0), (100, 20, 0), (150, 20, 10), (199, 20, 20)])
    segs = _segments([
        ("S1", "straight", 0, 100, 250, 1.0, 1.10, 0.10, "straight", True),
        ("C1", "corner", 100, 200, 90, 1.0, 0.90, -0.20, "slow_corner", True),
        # a sensor-bad segment must contribute null delta (not a misleading color):
        ("C2", "corner", 200, 300, 95, 1.0, 9.0, 8.0, "slow_corner", False),
    ])
    p2 = _path([(0, 0, 0), (50, 10, 0), (150, 20, 10), (250, 30, 20)])
    out = serialize.serialize_track(p2, segs, _corners([]), max_points=10)
    # Columnar path with parallel x/y/delta arrays of equal length.
    assert len(out["path"]["x"]) == len(out["path"]["y"]) == len(out["path"]["delta"])
    assert 0.1 in out["path"]["delta"]  # d=50 in S1
    assert -0.2 in out["path"]["delta"]  # d=150 in C1
    assert None in out["path"]["delta"]  # d=250 in sensor-bad C2 -> null


def test_serialize_track_maps_corners_to_nearest_xy():
    path = _path([(0, 0, 0), (100, 10, 5), (200, 20, 10)])
    corner = _corners([("R", 1, 100, 80, 78, 80, 2.0, 30, 34, -4.0, 10, 12, -2.0, True)])
    out = serialize.serialize_track(path, _segments([]), corner, max_points=10)
    c = out["corners"][0]
    assert c["x"] == 10 and c["y"] == 5  # nearest path point to distance 100
    assert c["apexDeltaKph"] == 2.0 and c["brakeOnDelta"] == -4.0


def test_serialize_track_none_when_no_path():
    assert serialize.serialize_track(None, _segments([]), _corners([])) is None
    assert serialize.serialize_track(_path([]), _segments([]), _corners([])) is None


# ---- index manifest + determinism ----------------------------------------

def test_build_index_has_required_keys():
    idx = serialize.build_index(
        season=2026,
        rounds=[{"round": 1, "slug": "australian", "eventName": "Australian Grand Prix",
                 "eventDate": "2026-03-08", "format": "conventional",
                 "hasQualifying": True, "hasRace": True}],
        teams=[{"slug": "mercedes", "displayName": "Mercedes",
                "canonicalPair": {"a": {"code": "ANT", "number": 12, "name": "x"},
                                  "b": {"code": "RUS", "number": 63, "name": "y"}},
                "yoyAvailable": True, "roundsCovered": [1], "hasSwap": False}],
        last_updated="2026-06-17T00:00:00Z", source="FastF1 3.8.1",
    )
    assert idx["schemaVersion"] >= 1
    assert idx["season"] == 2026
    assert idx["teams"][0]["canonicalPair"]["a"]["number"] < idx["teams"][0]["canonicalPair"]["b"]["number"]


def test_serialization_is_deterministic():
    segs = _segments([
        ("S1", "straight", 0, 100, 250, 1.0, 1.10, 0.10, "straight", True),
    ])
    cr = {"segments": segs, "meta": _meta(0.10)}
    a = serialize.serialize_qualifying_round(cr, _corners([]), round_number=1,
        event_name="X", a_code="ANT", b_code="RUS", is_canonical=True)
    b = serialize.serialize_qualifying_round(cr, _corners([]), round_number=1,
        event_name="X", a_code="ANT", b_code="RUS", is_canonical=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
