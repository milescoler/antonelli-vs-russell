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
from src import teams, serialize, benchmarks, race  # noqa: E402
import fastf1                                     # noqa: E402

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

    if not only:  # only rewrite the manifest on a full build
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
