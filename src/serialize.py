"""Pure serialization: turn the analysis modules' DataFrames/dicts into
JSON-ready Python dicts matching the site schema. No FastF1, no file I/O — every
function takes plain data and returns plain data, so it is trivially unit-tested
and deterministic.

Sign conventions are preserved from the source modules:
  - qualifying lapDelta_s / segment meanDelta_s: positive => driver A faster
  - gap_s: negative => leading / ahead of P2
NaN/inf/NA serialize to JSON null via `_num` / `_int_or_none`.
"""
from __future__ import annotations

import math

import pandas as pd

SCHEMA_VERSION = 1

# Segment categories in fixed display order.
CATEGORY_ORDER = ["straight", "slow_corner", "medium_corner", "fast_corner"]
CORNER_CATEGORY_ORDER = ["slow_corner", "medium_corner", "fast_corner"]

# Corner-speed thresholds — mirror benchmarks.SLOW_CORNER_MAX_KPH /
# benchmarks.FAST_CORNER_MIN_KPH (kept inline so this module imports no FastF1).
SLOW_CORNER_MAX_KPH = 130.0
FAST_CORNER_MIN_KPH = 200.0


# ---- numeric helpers -----------------------------------------------------

def _num(x, ndigits: int = 3):
    """Round to `ndigits`, mapping NaN/inf/NA/None -> None (JSON null)."""
    try:
        if x is None or x is pd.NA:
            return None
        fx = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(fx) or math.isinf(fx):
        return None
    return round(fx, ndigits)


def _int_or_none(x):
    """Coerce to int, mapping NaN/inf/NA/None -> None."""
    try:
        if x is None or x is pd.NA:
            return None
        fx = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(fx) or math.isinf(fx):
        return None
    return int(round(fx))


def _corner_category(mean_apex_kph) -> str:
    v = _num(mean_apex_kph, 3)
    if v is None:
        return "unknown"
    if v < SLOW_CORNER_MAX_KPH:
        return "slow_corner"
    if v < FAST_CORNER_MIN_KPH:
        return "medium_corner"
    return "fast_corner"


# ---- qualifying (Chapter 1) ----------------------------------------------

def serialize_segment_category_means(segments_df: pd.DataFrame) -> list[dict]:
    """Mean per-segment delta_s per category, over sensor_ok segments only,
    in fixed category order. Categories with no data are omitted."""
    df = segments_df[segments_df["sensor_ok"].astype(bool)]
    out = []
    for cat in CATEGORY_ORDER:
        sub = df[df["category"] == cat]
        if len(sub) == 0:
            continue
        out.append({
            "category": cat,
            "meanDelta_s": _num(sub["delta_s"].mean(), 3),
            "nSegments": int(len(sub)),
        })
    return out


def serialize_corner_buckets(corner_df: pd.DataFrame) -> list[dict]:
    """Mean apex/brake/throttle deltas bucketed by corner-speed category,
    sensor_ok corners only. Means skip null deltas; nCorners counts sensor_ok
    corners in the bucket."""
    out: list[dict] = []
    if corner_df is None or len(corner_df) == 0:
        return out
    df = corner_df[corner_df["sensor_ok"].astype(bool)].copy()
    if len(df) == 0:
        return out
    df["_cat"] = df["mean_apex_kph"].apply(_corner_category)
    for cat in CORNER_CATEGORY_ORDER:
        sub = df[df["_cat"] == cat]
        if len(sub) == 0:
            continue
        apex = sub["apex_delta_kph"].dropna()
        brake = sub["brake_on_delta"].dropna()
        thr = sub["throttle_full_delta"].dropna()
        out.append({
            "category": cat,
            "apexDeltaKph_mean": _num(apex.mean(), 1) if len(apex) else None,
            "brakeOnDelta_m_mean": _num(brake.mean(), 1) if len(brake) else None,
            "throttleFullDelta_m_mean": _num(thr.mean(), 1) if len(thr) else None,
            "nCorners": int(len(sub)),
        })
    return out


def serialize_qualifying_round(
    compare_result: dict,
    corner_df: pd.DataFrame | None,
    *,
    round_number: int,
    event_name: str,
    a_code: str,
    b_code: str,
    is_canonical: bool,
) -> dict:
    """One qualifying round entry from compare_teammates(...) output + corners."""
    meta = compare_result["meta"]
    segments = compare_result["segments"]
    sensor_freeze = bool((~segments["sensor_ok"].astype(bool)).any())
    if corner_df is not None and len(corner_df) > 0:
        sensor_freeze = sensor_freeze or bool((~corner_df["sensor_ok"].astype(bool)).any())
    return {
        "round": int(round_number),
        "eventName": str(event_name),
        "pairThisRound": {"aCode": str(a_code), "bCode": str(b_code)},
        "isCanonicalPair": bool(is_canonical),
        "lapTimeA_s": _num(meta["lap_time_a_s"], 3),
        "lapTimeB_s": _num(meta["lap_time_b_s"], 3),
        "lapDelta_s": _num(meta["lap_delta_s"], 3),
        "qSessionA": _int_or_none(meta.get("q_session_a")),
        "qSessionB": _int_or_none(meta.get("q_session_b")),
        "caveats": {
            "qMismatch": bool(meta.get("q_mismatch", False)),
            "sensorFreezeAny": sensor_freeze,
        },
        "segmentCategoryMeans": serialize_segment_category_means(segments),
        "cornerSignatureBuckets": serialize_corner_buckets(corner_df),
    }


def build_yoy(qual_rounds_2026: list[dict], qual_rounds_2025: list[dict]) -> dict | None:
    """Year-over-year block over rounds present in BOTH seasons. None if no
    overlap (e.g. the pairing didn't drive this team last year)."""
    d26 = {r["round"]: r["lapDelta_s"] for r in qual_rounds_2026 if r.get("lapDelta_s") is not None}
    d25 = {r["round"]: r["lapDelta_s"] for r in qual_rounds_2025 if r.get("lapDelta_s") is not None}
    overlap = sorted(set(d26) & set(d25))
    if not overlap:
        return None
    m26 = sum(d26[r] for r in overlap) / len(overlap)
    m25 = sum(d25[r] for r in overlap) / len(overlap)
    return {
        "season": 2025,
        "meanLapDelta_s_2026": _num(m26, 3),
        "meanLapDelta_s_2025": _num(m25, 3),
        "deltaOfDeltas_s": _num(m26 - m25, 3),
        "nRoundsCompared": len(overlap),
    }


# ---- race (Chapter 2) ----------------------------------------------------

def serialize_start(start_df: pd.DataFrame, *, a_code: str, b_code: str) -> list[dict]:
    """Start conversion rows, remapping the two teammate ROLE labels to A/B by
    matching `code` (not the literal ANT/RUS labels start_summary emits). P2 row
    passes through. finish=null + dnf=true when not Finished."""
    out = []
    for _, r in start_df.iterrows():
        role_label = str(r["driver"])
        code = str(r["code"])
        if role_label == "P2":
            role = "P2"
        elif code == a_code:
            role = "A"
        elif code == b_code:
            role = "B"
        else:
            role = "P2"  # defensive: shouldn't happen
        status = str(r["status"])
        finish = _int_or_none(r["finish"])
        out.append({
            "role": role,
            "code": code,
            "grid": _int_or_none(r["grid"]),
            "lap1Pos": _int_or_none(r["lap1_pos"]),
            "positionsGained": _int_or_none(r["positions_gained"]),
            "finish": finish,
            "status": status,
            "dnf": bool(finish is None or status != "Finished"),
        })
    out.sort(key=lambda d: {"A": 0, "B": 1, "P2": 2}.get(d["role"], 3))
    return out


def serialize_stint_pace(stint_df: pd.DataFrame) -> list[dict]:
    out = [
        {
            "code": str(r["driver"]),
            "stint": _int_or_none(r["stint"]),
            "compound": str(r["compound"]),
            "medianLaptime_s": _num(r["median_laptime_s"], 3),
            "nClean": _int_or_none(r["n_clean"]),
        }
        for _, r in stint_df.iterrows()
    ]
    out.sort(key=lambda d: (d["code"], d["stint"] if d["stint"] is not None else -1))
    return out


def serialize_tire_deg(deg_df: pd.DataFrame) -> list[dict]:
    out = [
        {
            "code": str(r["driver"]),
            "stint": _int_or_none(r["stint"]),
            "compound": str(r["compound"]),
            "degSlope_s_per_lap": _num(r["deg_slope_s_per_lap"], 4),
            "nClean": _int_or_none(r["n_clean"]),
        }
        for _, r in deg_df.iterrows()
    ]
    out.sort(key=lambda d: (d["code"], d["stint"] if d["stint"] is not None else -1))
    return out


def serialize_gap_trace(gap_df: pd.DataFrame, driver_code: str) -> dict:
    df = gap_df.sort_values("lap")
    return {
        "driverCode": str(driver_code),
        "laps": [int(x) for x in df["lap"].tolist()],
        "gap_s": [_num(x, 2) for x in df["gap_s"].tolist()],
        "leading": [bool(x) for x in df["leading"].tolist()],
    }


def serialize_race_round(
    start_df: pd.DataFrame,
    stint_df: pd.DataFrame,
    deg_df: pd.DataFrame,
    gap_df: pd.DataFrame | None,
    *,
    round_number: int,
    event_name: str,
    a_code: str,
    b_code: str,
    is_canonical: bool,
) -> dict:
    start = serialize_start(start_df, a_code=a_code, b_code=b_code)
    pace = serialize_stint_pace(stint_df)
    deg = serialize_tire_deg(deg_df)
    if gap_df is not None and len(gap_df) > 0:
        gap = serialize_gap_trace(gap_df, a_code)
    else:
        gap = {"driverCode": str(a_code), "laps": [], "gap_s": [], "leading": []}
    codes_with_pace = {p["code"] for p in pace}
    return {
        "round": int(round_number),
        "eventName": str(event_name),
        "pairThisRound": {"aCode": str(a_code), "bCode": str(b_code)},
        "isCanonicalPair": bool(is_canonical),
        "start": start,
        "stintPace": pace,
        "tireDeg": deg,
        "gapTrace": gap,
        "caveats": {
            "anyDnf": bool(any(r["dnf"] for r in start)),
            "smallSampleDeg": bool(any(d["degSlope_s_per_lap"] is None for d in deg)),
            "noCleanLapsDriver": [c for c in (a_code, b_code) if c not in codes_with_pace],
            "fuelNotCorrected": True,
        },
    }


# ---- assembly ------------------------------------------------------------

def build_team_json(*, slug, display_name, pair, qualifying_rounds, race_rounds, yoy) -> dict:
    out = {
        "schemaVersion": SCHEMA_VERSION,
        "slug": slug,
        "displayName": display_name,
        "pair": pair,
        "signConvention": "positive_means_a_faster",
        "qualifying": {"byRound": qualifying_rounds},
        "race": {"byRound": race_rounds},
        "caveatsGlobal": {"fuelNotCorrected": True, "syntheticHistory": False, "notes": []},
    }
    if yoy is not None:
        out["qualifying"]["yoy"] = yoy
    return out


def build_index(*, season, rounds, teams, last_updated, source) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "season": season,
        "lastUpdated": last_updated,
        "source": source,
        "rounds": rounds,
        "teams": teams,
    }
