#!/usr/bin/env python3
"""Pre-compute Pitwall season-dashboard JSON from FastF1.

Builds a single season.json (standings, qualifying pace, race pace, tire data)
plus per-round telemetry/<slug>.json files. All output is deterministic: sorted
keys, fixed rounding, and lastUpdated preserved on no-data reruns so `git diff`
stays clean.

Usage:
    python scripts/build_site_data.py            # season 2026
    python scripts/build_site_data.py --season 2025
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.loaders import (                         # noqa: E402
    setup_cache,
    load_qualifying_session,
    get_fastest_valid_lap,
    get_lap_telemetry,
)
from src.segments import resample_to_distance_grid  # noqa: E402
from src import teams, serialize, race, standings, season_stats  # noqa: E402
import fastf1                                     # noqa: E402
import pandas as pd                               # noqa: E402

CACHE = ROOT / "fastf1_cache"
DATA_DIR = ROOT / "web" / "public" / "data"
SOURCE = f"FastF1 {fastf1.__version__}"


# ---- IO helpers ----------------------------------------------------------

def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_json_if_changed(path: Path, obj) -> bool:
    """Write only if the canonical serialization differs from the file on disk."""
    text = _canonical(obj)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_season(path: Path, season_obj: dict) -> bool:
    """Like write_json_if_changed, but preserves the prior `lastUpdated` when
    nothing else changed, so a no-data rerun produces a clean git diff."""
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        prev_rest = {k: v for k, v in prev.items() if k != "lastUpdated"}
        new_rest = {k: v for k, v in season_obj.items() if k != "lastUpdated"}
        if prev_rest == new_rest:
            season_obj["lastUpdated"] = prev.get("lastUpdated", season_obj["lastUpdated"])
    return write_json_if_changed(path, season_obj)


# ---- qualifying pace rows ------------------------------------------------

def _qual_pace(year, rounds):
    """Per-driver best qualifying lap (light load, no telemetry).
    Returns rows {session, year, round, code, name, team, teamColor, lap_s}."""
    rows = []
    for rnd in rounds:
        try:
            s = fastf1.get_session(year, rnd, "Q")
            s.load(laps=False, telemetry=False, weather=False, messages=False)
        except Exception as exc:  # noqa: BLE001
            print(f"   qual pace: skip {year} Q R{rnd}: {exc!r}")
            continue
        for _, r in s.results.iterrows():
            secs = [t.total_seconds() for t in (r.get("Q1"), r.get("Q2"), r.get("Q3")) if pd.notna(t)]
            if not secs:
                continue
            tc = r.get("TeamColor")
            rows.append({
                "session": (year, rnd), "year": year, "round": int(rnd),
                "code": str(r["Abbreviation"]), "name": str(r["FullName"]),
                "team": str(r["TeamName"]), "teamColor": f"#{tc}" if isinstance(tc, str) and tc else None,
                "lap_s": min(secs),
            })
    return rows


# ---- race pace rows ------------------------------------------------------

def _race_pace_rows(year: int, round_infos: list[dict]) -> list[dict]:
    """Per-driver per-round race pace gap to fastest median.
    Returns rows {round, code, name, team, teamColor, gap_pct}."""
    rows = []
    for ri in round_infos:
        rnd = ri["round"]
        try:
            session = race.load_race_session(year, rnd)
        except Exception as exc:  # noqa: BLE001
            print(f"   race pace: skip R{rnd}: {exc!r}")
            continue

        # Build per-driver identity from results
        ident: dict[str, dict] = {}
        for _, r in session.results.iterrows():
            tc = r.get("TeamColor")
            ident[str(r["Abbreviation"])] = {
                "name": str(r["FullName"]),
                "team": str(r["TeamName"]),
                "teamColor": f"#{tc}" if isinstance(tc, str) and tc else None,
            }

        # Compute median clean-lap time per driver
        medians: dict[str, float] = {}
        for code in ident:
            try:
                clean = race.get_clean_laps(session, code)
            except Exception:  # noqa: BLE001
                continue
            if clean.empty:
                continue
            med = float(clean["LapTimeSeconds"].median())
            if not (med != med) and med > 0:  # NaN check
                medians[code] = med

        if not medians:
            continue

        ref = min(medians.values())
        for code, med in sorted(medians.items()):
            info = ident.get(code, {})
            gap_pct = 100.0 * (med - ref) / ref
            rows.append({
                "round": rnd,
                "code": code,
                "name": info.get("name", code),
                "team": info.get("team", ""),
                "teamColor": info.get("teamColor"),
                "gap_pct": gap_pct,
            })
    return rows


# ---- tire rows -----------------------------------------------------------

def _tire_rows(year: int, round_infos: list[dict]) -> list[dict]:
    """Aggregate per-driver stint pace and tire degradation across rounds.
    Returns list of {code, name, team, teamColor, stints:[...]}."""
    by_driver: dict[str, dict] = {}

    for ri in round_infos:
        rnd = ri["round"]
        try:
            session = race.load_race_session(year, rnd)
        except Exception as exc:  # noqa: BLE001
            print(f"   tire rows: skip R{rnd}: {exc!r}")
            continue

        # Driver identity
        ident: dict[str, dict] = {}
        for _, r in session.results.iterrows():
            tc = r.get("TeamColor")
            ident[str(r["Abbreviation"])] = {
                "name": str(r["FullName"]),
                "team": str(r["TeamName"]),
                "teamColor": f"#{tc}" if isinstance(tc, str) and tc else None,
            }

        drivers_in_session = list(ident.keys())

        # Stint pace
        try:
            pace_df = race.stint_pace(year, rnd, drivers_in_session)
        except Exception as exc:  # noqa: BLE001
            print(f"   tire pace: skip R{rnd}: {exc!r}")
            pace_df = pd.DataFrame()

        # Tire deg
        try:
            deg_df = race.tire_deg(year, rnd, drivers_in_session)
        except Exception as exc:  # noqa: BLE001
            print(f"   tire deg: skip R{rnd}: {exc!r}")
            deg_df = pd.DataFrame()

        # Build (code, stint) -> pace and deg
        pace_by_cs: dict[tuple, dict] = {}
        if not pace_df.empty:
            for _, pr in pace_df.iterrows():
                k = (str(pr["driver"]), int(pr["stint"]))
                pace_by_cs[k] = {
                    "compound": str(pr["compound"]),
                    "medianLap_s": serialize._num(pr["median_laptime_s"], 3),
                    "nClean": serialize._int_or_none(pr["n_clean"]),
                }

        deg_by_cs: dict[tuple, float | None] = {}
        if not deg_df.empty:
            for _, dr in deg_df.iterrows():
                k = (str(dr["driver"]), int(dr["stint"]))
                deg_by_cs[k] = serialize._num(dr["deg_slope_s_per_lap"], 4)

        # Merge into per-driver stints list
        all_keys = sorted(set(pace_by_cs) | set(deg_by_cs))
        for code, stint in all_keys:
            info = ident.get(code, {})
            drv = by_driver.setdefault(code, {
                "code": code,
                "name": info.get("name", code),
                "team": info.get("team", ""),
                "teamColor": info.get("teamColor"),
                "stints": [],
            })
            # Update identity with latest round info
            if info:
                drv["name"] = info.get("name", drv["name"])
                drv["team"] = info.get("team", drv["team"])
                drv["teamColor"] = info.get("teamColor", drv["teamColor"])

            pace_info = pace_by_cs.get((code, stint), {})
            deg_slope = deg_by_cs.get((code, stint))
            drv["stints"].append({
                "round": rnd,
                "stint": stint,
                "compound": pace_info.get("compound", "UNKNOWN"),
                "medianLap_s": pace_info.get("medianLap_s"),
                "degSlope": deg_slope,
                "nClean": pace_info.get("nClean"),
            })

    # Sort stints within each driver by (round, stint)
    result = []
    for code in sorted(by_driver.keys()):
        d = by_driver[code]
        d["stints"] = sorted(d["stints"], key=lambda s: (s["round"], s["stint"]))
        result.append(d)
    return result


# ---- telemetry per session -----------------------------------------------

def _telemetry_for_session(year: int, ri: dict) -> dict:
    """Build columnar telemetry path for each driver's fastest qualifying lap.
    Returns {session:{slug,round,eventName}, drivers:[...]}."""
    rnd = ri["round"]
    slug = ri["slug"]
    event_name = ri["eventName"]

    session_meta = {"slug": slug, "round": rnd, "eventName": event_name}

    try:
        session = load_qualifying_session(year, rnd)
    except Exception as exc:  # noqa: BLE001
        print(f"   telemetry: can't load Q R{rnd}: {exc!r}")
        return {"session": session_meta, "drivers": []}

    driver_entries = []
    for _, r in session.results.iterrows():
        code = str(r["Abbreviation"])
        tc = r.get("TeamColor")
        identity = {
            "code": code,
            "name": str(r["FullName"]),
            "team": str(r["TeamName"]),
            "teamColor": f"#{tc}" if isinstance(tc, str) and tc else None,
        }
        try:
            lap = get_fastest_valid_lap(session, code)
            telem = get_lap_telemetry(lap)
            grid_df = resample_to_distance_grid(telem)
        except Exception as exc:  # noqa: BLE001
            print(f"      telemetry skip {code} R{rnd}: {exc!r}")
            continue

        # Downsample to ≤140 points
        n = len(grid_df)
        step = max(1, n // 140)
        keep = list(range(0, n, step))

        path = {
            "x": [serialize._int_or_none(grid_df["X"].iloc[i]) for i in keep],
            "y": [serialize._int_or_none(grid_df["Y"].iloc[i]) for i in keep],
            "speed": [serialize._num(grid_df["Speed"].iloc[i], 3) for i in keep],
            "brake": [serialize._num(grid_df["Brake"].iloc[i], 3) for i in keep],
            "throttle": [serialize._num(grid_df["Throttle"].iloc[i], 3) for i in keep],
        }

        driver_entries.append({
            **identity,
            "path": path,
            "corners": [],
        })

    # Sort drivers by code for determinism
    driver_entries.sort(key=lambda d: d["code"])
    return {"session": session_meta, "drivers": driver_entries}


# ---- unique drivers meta -------------------------------------------------

def _drivers_meta(drivers_list: list[dict]) -> list[dict]:
    """Unique {code, name, team, teamColor} from standings, sorted by code."""
    seen: dict[str, dict] = {}
    for d in drivers_list:
        code = d["code"]
        if code not in seen:
            seen[code] = {
                "code": code,
                "name": d.get("name", code),
                "team": d.get("team", ""),
                "teamColor": d.get("teamColor"),
            }
    return sorted(seen.values(), key=lambda x: x["code"])


# ---- orchestration -------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()
    season = args.season

    setup_cache(str(CACHE))
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"== {season}: discovering completed rounds ==")
    round_infos = teams.list_completed_rounds(season)
    round_nums = [r["round"] for r in round_infos]
    print(f"   rounds: {round_nums}")

    # 1. Standings
    print("== standings ==")
    per_round = standings.season_results(season, round_nums)
    drivers = standings.build_standings(per_round)
    constructors = season_stats.constructors_table(drivers)
    print(f"   {len(drivers)} drivers, {len(constructors)} constructors")

    # 2. Qualifying pace (gap to pole = % off session fastest)
    print("== qualifying pace ==")
    qual_rows_raw = _qual_pace(season, round_nums)
    # Group by session, normalize within each session
    by_session: dict[tuple, list] = {}
    for r in qual_rows_raw:
        by_session.setdefault(r["session"], []).append(r)

    qual_rows: list[dict] = []
    for sess, rs in by_session.items():
        rnd = sess[1]
        gaps = season_stats.normalize_session({r["code"]: r["lap_s"] for r in rs})
        for r in rs:
            qual_rows.append({
                "round": rnd,
                "code": r["code"],
                "name": r["name"],
                "team": r["team"],
                "teamColor": r["teamColor"],
                "gap_pct": gaps[r["code"]],
            })

    qualifying = season_stats.pace_table(qual_rows)
    print(f"   {len(qualifying)} drivers in qualifying pace")

    # 3. Race pace (% off race fastest median)
    print("== race pace ==")
    race_rows = _race_pace_rows(season, round_infos)
    race_pace = season_stats.pace_table(race_rows)
    print(f"   {len(race_pace)} drivers in race pace")

    # 4. Tire
    print("== tire data ==")
    tire = _tire_rows(season, round_infos)
    print(f"   {len(tire)} drivers in tire data")

    # 5. Telemetry: one file per round
    print("== telemetry ==")
    telem_dir = DATA_DIR / "telemetry"
    telem_dir.mkdir(parents=True, exist_ok=True)
    telem_sessions = []
    for ri in round_infos:
        print(f"   R{ri['round']} {ri['eventName']}")
        telem_doc = _telemetry_for_session(season, ri)
        slug = ri["slug"]
        wrote = write_json_if_changed(telem_dir / f"{slug}.json", telem_doc)
        print(f"   {'wrote' if wrote else 'unchanged'} telemetry/{slug}.json "
              f"({len(telem_doc['drivers'])} drivers)")
        telem_sessions.append({
            "slug": ri["slug"],
            "round": ri["round"],
            "eventName": ri["eventName"],
        })

    # Assemble meta.drivers from standings (most complete source of driver identity)
    drivers_meta = _drivers_meta(drivers)

    season_doc = {
        "schemaVersion": serialize.SCHEMA_VERSION,
        "season": season,
        "lastUpdated": now_utc,
        "source": SOURCE,
        "meta": {
            "rounds": round_infos,
            "sessions": telem_sessions,
            "drivers": drivers_meta,
        },
        "standings": {
            "drivers": drivers,
            "constructors": constructors,
        },
        "qualifying": qualifying,
        "racePace": race_pace,
        "tire": tire,
    }

    wrote = write_season(DATA_DIR / "season.json", season_doc)
    print(f"\n{'wrote' if wrote else 'unchanged'} season.json "
          f"({len(drivers)} drivers, {len(round_infos)} rounds)")

    # Clean up stale files from old pipeline
    stale = [
        DATA_DIR / "driver_ratings.json",
        DATA_DIR / "index.json",
        DATA_DIR / "standings.json",
    ]
    for f in stale:
        if f.exists():
            f.unlink()
            print(f"removed stale {f.name}")

    stale_teams = DATA_DIR / "teams"
    if stale_teams.exists():
        import shutil
        shutil.rmtree(stale_teams)
        print("removed stale teams/")

    print("\nDone. Review `git status web/public/data`, then commit.")


if __name__ == "__main__":
    main()
