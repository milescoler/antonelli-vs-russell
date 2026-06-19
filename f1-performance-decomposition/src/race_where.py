"""Factor 1 for the race-win decomposition: where on track the winner built the
gap over P2, on COMPARABLE race laps (same compound, similar tyre age & fuel),
with per-sector bootstrap CIs. Runs in the engine namespace; emits JSON via CLI.
"""
from __future__ import annotations
import logging

import numpy as np
import pandas as pd

import config
from src import data_loading, resampling, delta as delta_mod, attribution, web_export

logger = logging.getLogger(__name__)


def comparable_pairs(winner_meta, p2_meta, *, age_tol=None, lap_tol=None):
    age_tol = config.COMPARABLE_AGE_TOL if age_tol is None else age_tol
    lap_tol = config.COMPARABLE_LAP_TOL if lap_tol is None else lap_tol
    pairs = []
    for w in winner_meta:
        for p in p2_meta:
            if (w["compound"] == p["compound"]
                    and abs(w["tyre_life"] - p["tyre_life"]) <= age_tol
                    and abs(w["lap_number"] - p["lap_number"]) <= lap_tol):
                pairs.append((w["idx"], p["idx"]))
    return pairs


def paired_sector_bootstrap(pair_deltas, *, n_boot=None, confidence=None, seed=None):
    n_boot = config.N_BOOTSTRAP if n_boot is None else n_boot
    confidence = config.CONFIDENCE if confidence is None else confidence
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)
    mat = np.asarray(pair_deltas, dtype=float)
    n_pairs, n_sec = mat.shape
    point = mat.mean(axis=0)
    boot = np.empty((n_boot, n_sec))
    for k in range(n_boot):
        idx = rng.integers(0, n_pairs, size=n_pairs)   # resample PAIRS (matched)
        boot[k] = mat[idx].mean(axis=0)
    a = 1.0 - confidence
    lo = np.percentile(boot, 100 * a / 2, axis=0)
    hi = np.percentile(boot, 100 * (1 - a / 2), axis=0)
    sig = (lo > 0) | (hi < 0)
    return [{"sector": i + 1, "deltaMean": float(point[i]), "ciLow": float(lo[i]),
             "ciHigh": float(hi[i]), "significant": bool(sig[i])} for i in range(n_sec)]


# --------------------------------------------------------------------------- #
# Race comparable-lap loader
# --------------------------------------------------------------------------- #

def load_race_laps(year: int, gp: str, winner: str, p2: str,
                   ) -> tuple[list[data_loading.Lap], list[data_loading.Lap]]:
    """Load and clean race laps for winner and P2 from a FastF1 Race session.

    Cleaning rules (race-specific; deliberately NOT the qualy 107% filter):
      * Whole-lap green flag (TrackStatus == "1")
      * Not the opening lap (LapNumber != 1)
      * No pit activity on this lap (PitInTime and PitOutTime both NaT)
      * Official lap time present (LapTime not NaT)
      * Telemetry non-degenerate (at least 50 samples, last Distance > 0)

    Returns (winner_laps, p2_laps) as lists of data_loading.Lap objects.
    """
    import fastf1

    data_loading.enable_cache()
    session = fastf1.get_session(year, gp, "R")
    session.load(telemetry=True, laps=True, weather=False, messages=False)
    logger.info("Loaded %s %s Race: %d total laps", year, gp, len(session.laps))

    winner_laps: list[data_loading.Lap] = []
    p2_laps: list[data_loading.Lap] = []

    for code, dest in ((winner, winner_laps), (p2, p2_laps)):
        driver_laps = session.laps.pick_drivers(code)
        kept = 0
        for _, lap in driver_laps.iterrows():
            lapnum = int(lap["LapNumber"])

            # --- filtering ---
            if lapnum == 1:
                logger.debug("  drop %s lap %d: formation/opening lap", code, lapnum)
                continue
            if pd.isna(lap["LapTime"]):
                logger.info("  drop %s lap %d: LapTime is NaT", code, lapnum)
                continue
            track_status = str(lap.get("TrackStatus", "")).strip()
            if track_status != "1":
                logger.info("  drop %s lap %d: TrackStatus=%r (not fully green)",
                            code, lapnum, track_status)
                continue
            pit_in = lap.get("PitInTime")
            pit_out = lap.get("PitOutTime")
            if not pd.isna(pit_in) or not pd.isna(pit_out):
                logger.info("  drop %s lap %d: pit lap (PitIn=%s PitOut=%s)",
                            code, lapnum, pit_in, pit_out)
                continue

            # --- telemetry ---
            try:
                raw_tel = lap.get_telemetry()
                tel = data_loading._standardise_telemetry(raw_tel)
            except Exception as exc:  # noqa: BLE001
                logger.info("  drop %s lap %d: telemetry error: %s", code, lapnum, exc)
                continue

            if len(tel) < 50:
                logger.info("  drop %s lap %d: degenerate telemetry (only %d rows)",
                            code, lapnum, len(tel))
                continue
            if float(tel["Distance"].iloc[-1]) <= 0:
                logger.info("  drop %s lap %d: degenerate telemetry (Distance<=0)", code, lapnum)
                continue

            compound = lap.get("Compound")
            tyre_life_raw = lap.get("TyreLife")
            tyre_life = None if pd.isna(tyre_life_raw) else float(tyre_life_raw)

            dest.append(data_loading.Lap(
                driver=code,
                lap_number=lapnum,
                lap_time=float(lap["LapTime"].total_seconds()),
                compound=str(compound) if compound is not None and not pd.isna(compound) else None,
                tyre_life=tyre_life,
                telemetry=tel,
            ))
            kept += 1

        logger.info("%s: kept %d race-clean laps", code, kept)

    return winner_laps, p2_laps


# --------------------------------------------------------------------------- #
# Where-on-track decomposition orchestration
# --------------------------------------------------------------------------- #

def decompose_where(winner_laps: list[data_loading.Lap],
                    p2_laps: list[data_loading.Lap],
                    corner_distances) -> dict | None:
    """Decompose where on track the winner built their gap over P2.

    Uses comparable pairs (same compound, similar tyre age & lap number) to
    produce paired per-sector bootstrap CIs, a mean delta curve, attribution
    narratives for the key sectors, and a web-export-shaped payload dict.

    Returns None when fewer than MIN_COMPARABLE_PAIRS pairs are available.
    """
    if not winner_laps or not p2_laps:
        logger.warning("decompose_where: no laps for one or both drivers")
        return None

    winner_code = winner_laps[0].driver
    p2_code = p2_laps[0].driver

    # 1. Build meta and find comparable pairs
    winner_meta = [
        {"idx": i, "compound": L.compound, "tyre_life": L.tyre_life or 0.0,
         "lap_number": L.lap_number}
        for i, L in enumerate(winner_laps)
    ]
    p2_meta = [
        {"idx": i, "compound": L.compound, "tyre_life": L.tyre_life or 0.0,
         "lap_number": L.lap_number}
        for i, L in enumerate(p2_laps)
    ]

    pairs = comparable_pairs(winner_meta, p2_meta)
    logger.info("comparable pairs: %d", len(pairs))

    if len(pairs) < config.MIN_COMPARABLE_PAIRS:
        logger.warning(
            "only %d comparable pairs (need %d) - returning None",
            len(pairs), config.MIN_COMPARABLE_PAIRS,
        )
        return None

    # 2. Build shared grid from the minimum lap length across all USED laps
    used_w_idx = {wi for wi, _ in pairs}
    used_p_idx = {pi for _, pi in pairs}
    used_winner = [winner_laps[i] for i in sorted(used_w_idx)]
    used_p2 = [p2_laps[i] for i in sorted(used_p_idx)]

    lap_len = min(L.lap_length for L in (used_winner + used_p2))
    grid = resampling.build_distance_grid(lap_len)
    logger.info("shared grid: %.1f m, %d points", lap_len, len(grid))

    # Resample each USED lap once (cache in dicts)
    rw: dict[int, pd.DataFrame] = {
        i: resampling.resample_lap(winner_laps[i], grid) for i in used_w_idx
    }
    rp: dict[int, pd.DataFrame] = {
        i: resampling.resample_lap(p2_laps[i], grid) for i in used_p_idx
    }

    # 3. Build micro-sector edges anchored to corners
    corner_distances_arr = (
        np.asarray(corner_distances, dtype=float)
        if corner_distances is not None else None
    )
    edges = delta_mod.micro_sector_edges(grid, corner_distances=corner_distances_arr)
    n_sectors = len(edges) - 1
    logger.info("micro-sector edges: %d sectors", n_sectors)

    # 4. Per-pair per-sector deltas + mean cumulative curve
    pair_deltas: list[np.ndarray] = []
    pair_curves: list[np.ndarray] = []

    for wi, pi in pairs:
        seg_w = delta_mod.segment_times(rw[wi], edges)
        seg_p = delta_mod.segment_times(rp[pi], edges)
        pair_deltas.append(seg_w - seg_p)

        # Cumulative delta curve for this pair
        ta_w = delta_mod.time_at_distance(rw[wi])
        ta_p = delta_mod.time_at_distance(rp[pi])
        pair_curves.append(ta_w - ta_p)

    pair_deltas_mat = np.vstack(pair_deltas)          # (n_pairs, n_sectors)
    mean_curve = np.mean(np.vstack(pair_curves), axis=0)  # (len(grid),)

    # 5. Paired bootstrap CIs on sectors
    sector_stats = paired_sector_bootstrap(pair_deltas_mat)

    # Merge with edge geometry
    sectors_out = []
    for i, ss in enumerate(sector_stats):
        start_m = float(edges[i])
        end_m = float(edges[i + 1])
        mid_m = 0.5 * (start_m + end_m)
        delta_mean = ss["deltaMean"]
        significant = ss["significant"]
        if np.isfinite(delta_mean):
            faster = winner_code if delta_mean < 0 else p2_code
        else:
            faster = None
        sectors_out.append({
            "i": i + 1,
            "startM": web_export._num(start_m, 1),
            "endM": web_export._num(end_m, 1),
            "midM": web_export._num(mid_m, 1),
            "deltaMean": web_export._num(delta_mean, 4),
            "ciLow": web_export._num(ss["ciLow"], 4),
            "ciHigh": web_export._num(ss["ciHigh"], 4),
            "significant": significant,
            "faster": faster,
        })

    # 6. Callouts
    sig_sectors = [s for s in sectors_out if s["significant"]]
    top_significant = sorted(sig_sectors, key=lambda s: abs(s["deltaMean"] or 0), reverse=True)
    top_sig_ids = [s["i"] for s in top_significant[:3]]

    non_sig = [s for s in sectors_out if not s["significant"]]
    if non_sig:
        noise_trap = max(non_sig, key=lambda s: abs(s["deltaMean"] or 0))["i"]
    else:
        noise_trap = None

    callouts = {"topSignificant": top_sig_ids, "noiseTrap": noise_trap}

    # 7. Attribution: pick the median-index pair as representative
    mid_pair_idx = len(pairs) // 2
    wi_rep, pi_rep = pairs[mid_pair_idx]
    repr_w = rw[wi_rep]
    repr_p = rp[pi_rep]

    attrib_rows = []
    if top_sig_ids:
        # Build a small DataFrame for the top significant sectors
        top_sig_rows = []
        for sec_id in top_sig_ids:
            ss = sector_stats[sec_id - 1]
            top_sig_rows.append({
                "sector": sec_id,
                "start_m": edges[sec_id - 1],
                "end_m": edges[sec_id],
                "delta_s_mean": ss["deltaMean"],
                "significant": ss["significant"],
            })
        top_df = pd.DataFrame(top_sig_rows)
        try:
            attrib_df = attribution.attribute(top_df, repr_w, repr_p, winner_code, p2_code)
            for _, r in attrib_df.iterrows():
                attrib_rows.append({
                    "sector": int(r["sector"]),
                    "driverFaster": str(r["faster_driver"]),
                    "deltaS": web_export._num(r["delta_s"], 4),
                    "significant": bool(r["significant"]),
                    "narrative": str(r["narrative"]),
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("attribution failed: %s", exc)

    # 8. Build the payload
    # Delta curve (downsampled)
    ci_idx = web_export._downsample_idx(len(grid), 200)
    delta_curve = [
        {"d": web_export._num(float(grid[i]), 1), "delta": web_export._num(float(mean_curve[i]), 4)}
        for i in ci_idx
    ]

    # Corners
    corners = web_export._corner_labels(corner_distances_arr)

    # Track map from representative winner lap + mean_curve rate. Use a denser
    # sampling than the delta curve so tight corners (Monaco hairpin/chicanes)
    # keep their geometry instead of smoothing into a blob.
    track_idx = web_export._downsample_idx(len(grid), 600)
    rate = np.gradient(mean_curve, grid)
    x_arr = repr_w["X"].to_numpy()
    y_arr = repr_w["Y"].to_numpy()
    track = [
        {
            "x": web_export._num(float(x_arr[i]), 1),
            "y": web_export._num(float(y_arr[i]), 1),
            "rate": web_export._num(float(rate[i]), 6),
        }
        for i in track_idx
    ]

    meta = {
        "nPairs": len(pairs),
        "nUniqueLapsA": len(used_w_idx),
        "nUniqueLapsB": len(used_p_idx),
        "winnerCode": winner_code,
        "p2Code": p2_code,
        "driverA": {"code": winner_code},
        "driverB": {"code": p2_code},
        "marginCurveS": web_export._num(float(mean_curve[-1]), 4),
    }

    return {
        "meta": meta,
        "deltaCurve": delta_curve,
        "corners": corners,
        "sectors": sectors_out,
        "attribution": attrib_rows,
        "callouts": callouts,
        "track": track,
    }


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    """CLI: python -m src.race_where --year 2026 --gp Monaco --a ANT --b RUS"""
    import argparse
    import json
    import sys
    import logging
    from pathlib import Path

    # Route all log noise to stderr so stdout stays clean JSON
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    # Suppress noisy FastF1/urllib loggers
    for _noisy in ("fastf1", "urllib3", "requests", "matplotlib"):
        logging.getLogger(_noisy).setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(description="Where-on-track factor 1 decomposition CLI")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--gp", required=True)
    parser.add_argument("--a", required=True, dest="driver_a", help="Winner driver code")
    parser.add_argument("--b", required=True, dest="driver_b", help="P2 driver code")
    args = parser.parse_args()

    # Point cache at the shared repo-root cache (so we reuse already-downloaded data)
    repo_cache = Path(__file__).resolve().parents[2] / "fastf1_cache"
    config.CACHE_DIR = repo_cache

    try:
        winner_laps, p2_laps = load_race_laps(args.year, args.gp, args.driver_a, args.driver_b)
    except Exception as exc:
        sys.stderr.write(f"ERROR load_race_laps: {exc}\n")
        sys.exit(1)

    # Try to load corner distances from the session
    corner_distances = None
    try:
        import fastf1
        from src import data_loading as _dl
        _dl.enable_cache()
        session = fastf1.get_session(args.year, args.gp, "R")
        # Session is already loaded by load_race_laps; if corner data is cheap, get it
        session.load(telemetry=False, laps=False, weather=False, messages=False)
        circuit_info = session.get_circuit_info()
        corner_distances = circuit_info.corners["Distance"].to_numpy()
    except Exception as exc:
        sys.stderr.write(f"WARNING corner distances unavailable ({exc}); using equal-bin fallback\n")
        corner_distances = None

    result = decompose_where(winner_laps, p2_laps, corner_distances)

    if result is None:
        payload = {
            "verdict": "insufficient",
            "reason": "fewer than %d comparable laps" % config.MIN_COMPARABLE_PAIRS,
        }
    else:
        payload = result

    print(json.dumps(payload))
    sys.exit(0)


if __name__ == "__main__":
    main()
