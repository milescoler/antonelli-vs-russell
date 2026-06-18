#!/usr/bin/env python3
"""Pre-compute the Driver-vs-Car site JSON from FastF1.

For every completed round of the season and every team's driver pair, run the
existing qualifying (Chapter 1) and race (Chapter 2) analysis and serialize the
results to web/public/data/. The frontend reads these static files; no Python
runs at request time.

Usage:
    python scripts/build_site_data.py                 # all teams, with YoY
    python scripts/build_site_data.py --no-yoy        # skip year-over-year
    python scripts/build_site_data.py --teams mercedes,ferrari   # subset
    python scripts/build_site_data.py --season 2026

Output:
    web/public/data/index.json          # manifest (rounds + teams)
    web/public/data/teams/<slug>.json   # per-team analysis

Mirrors scripts/refresh.py's graceful per-session try/except: one bad session
never aborts the build. Output is deterministic (sorted keys, fixed rounding,
stable lastUpdated on no-op reruns) so CI can commit-if-changed.
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
from src import teams, serialize, benchmarks, race, standings, ratings  # noqa: E402
import fastf1                                     # noqa: E402
import pandas as pd                               # noqa: E402

CACHE = ROOT / "fastf1_cache"
DATA_DIR = ROOT / "web" / "public" / "data"
TEAMS_DIR = DATA_DIR / "teams"
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


def write_index(path: Path, index_obj: dict) -> bool:
    """Like write_json_if_changed, but preserves the prior `lastUpdated` when
    nothing else changed, so a no-data rerun produces a clean git diff."""
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        prev_rest = {k: v for k, v in prev.items() if k != "lastUpdated"}
        new_rest = {k: v for k, v in index_obj.items() if k != "lastUpdated"}
        if prev_rest == new_rest:
            index_obj["lastUpdated"] = prev.get("lastUpdated", index_obj["lastUpdated"])
    return write_json_if_changed(path, index_obj)


# ---- per-round analysis --------------------------------------------------

def _track_path(season, rnd, a_code):
    """Driver A's fastest-lap X/Y, resampled to the distance grid — for the
    track-map geometry. Cache-backed; failures degrade to no map."""
    try:
        session = load_qualifying_session(season, rnd)
        lap = get_fastest_valid_lap(session, a_code)
        return resample_to_distance_grid(get_lap_telemetry(lap))
    except Exception as exc:  # noqa: BLE001
        print(f"      track path failed R{rnd} {a_code}: {exc!r}")
        return None


def _qualifying_round(season, ri, a_code, b_code):
    cr = benchmarks.compare_teammates(season, ri["round"], a_code, b_code)
    try:
        corners = benchmarks.compute_corner_signatures(season, ri["round"], a_code, b_code)
    except Exception as exc:  # noqa: BLE001
        print(f"      corners failed R{ri['round']} {a_code}/{b_code}: {exc!r}")
        corners = None
    path_df = _track_path(season, ri["round"], a_code)
    return serialize.serialize_qualifying_round(
        cr, corners, round_number=ri["round"], event_name=ri["eventName"],
        a_code=a_code, b_code=b_code, is_canonical=True, path_df=path_df,
    )


def _race_round(season, ri, a_code, b_code):
    start = race.start_summary(season, ri["round"], a_code, b_code)
    p2 = start[start["driver"] == "P2"]
    p2_code = str(p2["code"].iloc[0]) if len(p2) else None
    drivers = list(dict.fromkeys([a_code, b_code] + ([p2_code] if p2_code else [])))
    pace = race.stint_pace(season, ri["round"], drivers)
    deg = race.tire_deg(season, ri["round"], [a_code, b_code])
    gap = race.gap_to_rival(season, ri["round"], a_code)
    return serialize.serialize_race_round(
        start, pace, deg, gap, round_number=ri["round"], event_name=ri["eventName"],
        a_code=a_code, b_code=b_code, is_canonical=True,
    )


def _yoy_for_team(season, round_infos, a_code, b_code, qual_rounds, prior_rounds):
    """Align prior-season qualifying deltas to this season's rounds by circuit
    (location, with a unique-country fallback), then build the YoY block.
    Returns None if nothing aligns."""
    q_prior = []
    for ri in round_infos:
        prior_round = teams._match_prior_round(ri["country"], ri["location"], prior_rounds)
        if prior_round is None:
            continue
        try:
            cr = benchmarks.compare_teammates(season - 1, prior_round, a_code, b_code)
        except Exception as exc:  # noqa: BLE001
            print(f"      yoy skip {ri['location']} {season-1}: {exc!r}")
            continue
        q_prior.append({"round": ri["round"],
                        "lapDelta_s": serialize._num(cr["meta"]["lap_delta_s"], 3)})
    return serialize.build_yoy(qual_rounds, q_prior)


# ---- driver ratings (car-adjusted) ---------------------------------------

def _qual_pace(year, rounds):
    """Per-driver best qualifying lap (light load, no telemetry) for the rating
    model. Returns rows {session, year, round, code, name, team, teamColor, lap_s}."""
    rows = []
    for rnd in rounds:
        try:
            s = fastf1.get_session(year, rnd, "Q")
            s.load(laps=False, telemetry=False, weather=False, messages=False)
        except Exception as exc:  # noqa: BLE001
            print(f"   ratings: skip {year} Q R{rnd}: {exc!r}")
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


def build_ratings(season, round_nums):
    """Assemble the car-adjusted ratings doc: Layer-1 teammate margins (headline),
    Layer-3 connectivity islands, Layer-2 equal-car grid with bootstrap CIs."""
    pace_now = _qual_pace(season, round_nums)
    prior_nums = [r["round"] for r in teams.list_completed_rounds(season - 1)]
    pace_prior = _qual_pace(season - 1, prior_nums)
    all_pace = pace_now + pace_prior

    # session-normalized gaps (% off session fastest)
    by_session = {}
    for r in all_pace:
        by_session.setdefault(r["session"], []).append(r)
    gap = {}  # (session, code) -> gap_pct
    for sess, rs in by_session.items():
        for code, g in ratings.normalize_session({r["code"]: r["lap_s"] for r in rs}).items():
            gap[(sess, code)] = g

    meta = {r["code"]: r for r in pace_now}  # latest-season identity for display

    # Layer 1 — teammate margin per driver (this season only)
    per_driver = {}  # code -> {deltas, vs, ...}
    for sess, rs in by_session.items():
        if sess[0] != season:
            continue
        by_team = {}
        for r in rs:
            by_team.setdefault(r["team"], []).append(r)
        for pair in by_team.values():
            if len(pair) != 2:
                continue
            x, y = pair
            gx, gy = gap[(sess, x["code"])], gap[(sess, y["code"])]
            per_driver.setdefault(x["code"], {"deltas": [], "vs": y["code"]})["deltas"].append(gy - gx)
            per_driver.setdefault(y["code"], {"deltas": [], "vs": x["code"]})["deltas"].append(gx - gy)

    ranking = []
    for code, d in per_driver.items():
        m = ratings.teammate_margin(d["deltas"])
        info = meta.get(code, {})
        ranking.append({
            "code": code, "name": info.get("name", code), "team": info.get("team"),
            "teamColor": info.get("teamColor"), "vs": d["vs"],
            "marginPct": m["mean"], "ciLow": m["ciLow"], "ciHigh": m["ciHigh"],
            "n": m["n"], "winRate": m["winRate"], "signTestP": m["signTestP"],
            "verdict": m["verdict"], "deltas": [serialize._num(x, 3) for x in d["deltas"]],
        })
    ranking.sort(key=lambda r: (r["marginPct"] is None, -(r["marginPct"] or 0), r["code"]))

    # Layer 2/3 — model over both seasons. Canonicalize the Sauber->Audi rebrand
    # to one lineage so it reads as continuity (a single team), not a transfer.
    lineage = {"Kick Sauber": "Audi", "Sauber": "Audi"}
    canon = lambda t: lineage.get(t, t)  # noqa: E731
    model_rows = [
        {"session": r["session"], "driver": r["code"],
         "teamSeason": (r["year"], canon(r["team"])), "gap_pct": gap[(r["session"], r["code"])]}
        for r in all_pace
    ]
    model = ratings.absolute_model(model_rows)
    boot = ratings.session_bootstrap(model_rows, b=800, seed=0)
    comp_of = model["componentOf"]
    theta = model["theta"]

    # Components/islands (Layer 3). multiTeam uses canonical team names.
    drv_by_comp = {}
    for code, idx in comp_of.items():
        drv_by_comp.setdefault(idx, []).append(code)
    components = []
    for idx, members in enumerate(model["connectivity"]["components"]):
        components.append({
            "id": idx,
            "teamSeasons": sorted([{"year": yr, "team": t} for (yr, t) in members],
                                  key=lambda x: (x["year"], x["team"])),
            "drivers": sorted(drv_by_comp.get(idx, [])),
            "multiTeam": len({t for (_, t) in members}) > 1,
        })

    # Equal-car: per-island mini-grids (within an island the ordering is data-backed;
    # theta is per-component-centered so it is NOT comparable across islands — we
    # deliberately do not emit a single cross-island ladder).
    equal_islands = []
    for idx in sorted(drv_by_comp):
        codes = drv_by_comp[idx]
        drivers_sorted = sorted(codes, key=lambda c: (theta[c], c))
        rows = []
        for rank, c in enumerate(drivers_sorted, 1):
            info = meta.get(c, {})
            ci = boot.get(c, {})
            rows.append({
                "code": c, "name": info.get("name", c), "team": info.get("team"),
                "teamColor": info.get("teamColor"), "theta": serialize._num(theta[c], 3),
                "ciLow": ci.get("ciLow"), "ciHigh": ci.get("ciHigh"), "rank": rank,
            })
        equal_islands.append({
            "component": idx,
            "multiTeam": next(c["multiTeam"] for c in components if c["id"] == idx),
            "drivers": rows,
        })
    equal_islands.sort(key=lambda i: (not i["multiTeam"], -len(i["drivers"]), i["component"]))

    return {
        "schemaVersion": serialize.SCHEMA_VERSION,
        "season": season,
        "headline": {
            "metric": "Teammate margin",
            "note": ("How decisively each driver beats their teammate in qualifying — "
                     "same car, so it's mostly the driver. % of lap time, + = faster. "
                     "A relative margin, not an absolute skill ranking."),
            "ranking": ranking,
        },
        "islands": {
            "note": ("Teams link onto one scale only when a driver drove for both. In "
                     "2025–26 almost no one moved, so most teams are isolated — the "
                     "data can't rank drivers across unlinked teams."),
            "components": components,
        },
        "equalCar": {
            "note": ("IF every car were equal, the modeled qualifying order — but only "
                     "WITHIN a linked island (drivers connected by a shared seat). Across "
                     "unlinked islands the data can't compare, so there's no single ladder; "
                     "the one multi-team island is the real cross-team result."),
            "islands": equal_islands,
        },
    }


# ---- orchestration -------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--no-yoy", action="store_true")
    ap.add_argument("--teams", type=str, default=None,
                    help="comma-separated team slugs to limit the build")
    args = ap.parse_args()
    season = args.season
    only = set(s.strip() for s in args.teams.split(",")) if args.teams else None

    setup_cache(str(CACHE))
    print(f"== {season}: discovering completed rounds ==")
    round_infos = teams.list_completed_rounds(season)
    round_nums = [r["round"] for r in round_infos]
    print(f"   rounds: {round_nums}")

    pairs_by_team = teams.season_team_pairs(season, round_nums)

    # YoY plumbing: prior-season team driver-code sets + the prior round list
    # (matched per-circuit at build time via teams._match_prior_round).
    prior_codes, prior_rounds = {}, []
    if not args.no_yoy:
        print(f"== {season-1}: loading prior season for YoY ==")
        prior_rounds = teams.list_completed_rounds(season - 1)
        prior_codes = teams.team_driver_codes(season - 1, [r["round"] for r in prior_rounds])

    index_teams = []
    for team_name in sorted(pairs_by_team):
        slug = teams.team_slug(team_name)
        if only and slug not in only:
            continue
        canon = teams._canonical_from_round_pairs(pairs_by_team[team_name])
        pair = {"a": canon["a"], "b": canon["b"]}
        a_code, b_code = pair["a"]["code"], pair["b"]["code"]
        print(f"== {slug}: {a_code} vs {b_code} ==")

        qual_rounds, race_rounds, covered = [], [], set()
        for ri in round_infos:
            try:
                qual_rounds.append(_qualifying_round(season, ri, a_code, b_code))
                covered.add(ri["round"])
            except Exception as exc:  # noqa: BLE001
                print(f"   skip Q R{ri['round']}: {exc!r}")
            try:
                race_rounds.append(_race_round(season, ri, a_code, b_code))
                covered.add(ri["round"])
            except Exception as exc:  # noqa: BLE001
                print(f"   skip R R{ri['round']}: {exc!r}")

        yoy = None
        yoy_available = (not args.no_yoy
                         and {a_code, b_code} <= prior_codes.get(team_name, set()))
        if yoy_available:
            yoy = _yoy_for_team(season, round_infos, a_code, b_code, qual_rounds,
                                prior_rounds)

        team_json = serialize.build_team_json(
            slug=slug, display_name=teams.team_display_name(team_name), pair=pair,
            qualifying_rounds=qual_rounds, race_rounds=race_rounds, yoy=yoy,
        )
        wrote = write_json_if_changed(TEAMS_DIR / f"{slug}.json", team_json)
        print(f"   {'wrote' if wrote else 'unchanged'} teams/{slug}.json "
              f"(Q:{len(qual_rounds)} R:{len(race_rounds)} yoy:{yoy is not None})")

        # Compact summary so the overview grid (sparkline + headline stat) renders
        # from index.json alone; full panels lazy-load the team file on click.
        deltas = [q["lapDelta_s"] for q in qual_rounds if q["lapDelta_s"] is not None]
        index_teams.append({
            "slug": slug,
            "displayName": teams.team_display_name(team_name),
            "canonicalPair": pair,
            "yoyAvailable": yoy is not None,
            "roundsCovered": sorted(covered),
            "hasSwap": canon["hasSwap"],
            "summary": {
                "meanLapDelta_s": serialize._num(sum(deltas) / len(deltas), 3) if deltas else None,
                "lapDeltaByRound": deltas,
                "yoyDeltaOfDeltas_s": yoy["deltaOfDeltas_s"] if yoy else None,
            },
        })

    if not only:  # season-wide artifacts; only on a full build
        print("== car-adjusted driver ratings ==")
        rating_doc = build_ratings(season, round_nums)
        write_json_if_changed(DATA_DIR / "driver_ratings.json", rating_doc)
        print(f"   wrote driver_ratings.json ({len(rating_doc['headline']['ranking'])} drivers, "
              f"{len(rating_doc['islands']['components'])} islands)")

        print("== championship standings (context) ==")
        table = standings.build_standings(standings.season_results(season, round_nums))
        standings_doc = {
            "schemaVersion": serialize.SCHEMA_VERSION,
            "season": season,
            "nextRace": teams.next_race(season),
            "standings": table,
        }
        write_json_if_changed(DATA_DIR / "standings.json", standings_doc)
        print(f"   wrote standings.json ({len(table)} drivers)")

        index = serialize.build_index(
            season=season, rounds=round_infos, teams=index_teams,
            last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source=SOURCE,
        )
        wrote = write_index(DATA_DIR / "index.json", index)
        print(f"{'wrote' if wrote else 'unchanged'} index.json ({len(index_teams)} teams)")

    print("\nDone. Review `git status web/public/data`, then commit.")


if __name__ == "__main__":
    main()
