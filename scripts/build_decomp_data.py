#!/usr/bin/env python3
"""Pre-compute lap-decomposition JSON for the web flagship.

Reads web/public/data/season.json (built first by build_site_data.py) for round
identity, then for every teammate pair at every completed round runs the
decomposition core and writes:

  web/public/data/decomp/index.json            -- hero key, races, matchup list
  web/public/data/decomp/<slug>__<A>_<B>.json  -- one payload per VALID matchup

Failures (no clean laps, reconciliation residual > tolerance, load errors) are
recorded in the index with a human reason, never silently dropped.

Usage:
    python scripts/build_decomp_data.py                 # live FastF1
    python scripts/build_decomp_data.py --synthetic     # offline smoke demo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECOMP_ROOT = REPO_ROOT / "f1-performance-decomposition"
# Import the sub-project core ONLY (its `src`/`config`); never the main repo src.
sys.path.insert(0, str(DECOMP_ROOT))

import config                                   # noqa: E402  (sub-project config)
from src import run, web_export                 # noqa: E402

DATA_DIR = REPO_ROOT / "web" / "public" / "data" / "decomp"
SEASON_JSON = REPO_ROOT / "web" / "public" / "data" / "season.json"

# Hero matchup: the protagonist pairing, fixed.
HERO_SLUG = "canadian"
HERO_A, HERO_B = "RUS", "ANT"


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_json_if_changed(path: Path, obj) -> bool:
    text = _canonical(obj)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _share_cache_with_repo_root() -> None:
    """Use the repo-root fastf1_cache so we don't re-download what the main
    telemetry build already fetched."""
    config.CACHE_DIR = REPO_ROOT / "fastf1_cache"


def _name_lookup(results) -> dict:
    return {str(r["Abbreviation"]): str(r["FullName"]) for _, r in results.iterrows()}


def build_synthetic_demo(out_dir: Path) -> Path:
    """Offline: one hero matchup from the synthetic fixture + an index. No network."""
    res = run.run_pipeline(use_synthetic=True, driver_a=HERO_A, driver_b=HERO_B)
    meta = {"slug": HERO_SLUG, "eventName": "Synthetic GP", "round": 0,
            "year": config.YEAR, "session": "Q",
            "driverAName": HERO_A, "driverBName": HERO_B,
            "team": "Synthetic", "teamColor": "#27F4D2"}
    key = web_export.matchup_key(HERO_SLUG, HERO_A, HERO_B)
    payload = web_export.matchup_payload(res, meta)
    write_json_if_changed(out_dir / f"{key}.json", payload)
    entries = [{
        "key": key, "race": HERO_SLUG, "team": "Synthetic", "teamColor": "#27F4D2",
        "a": HERO_A, "b": HERO_B, "valid": True,
        "officialGapS": payload["meta"]["officialGapS"],
        "significantCount": sum(1 for s in payload["sectors"] if s["significant"]),
    }]
    races = [{"slug": HERO_SLUG, "name": "Synthetic GP", "round": 0}]
    write_json_if_changed(out_dir / "index.json",
                          web_export.build_index(key, races, entries))
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="offline smoke demo (no FastF1)")
    args = ap.parse_args()

    if args.synthetic:
        build_synthetic_demo(DATA_DIR)
        print(f"wrote synthetic demo to {DATA_DIR}")
        return

    _share_cache_with_repo_root()
    season = json.loads(SEASON_JSON.read_text(encoding="utf-8"))
    year = int(season["season"])
    rounds = season["meta"]["rounds"]            # [{slug, round, eventName, ...}]
    races = [{"slug": r["slug"], "name": r["eventName"], "round": int(r["round"])}
             for r in rounds]

    entries: list[dict] = []
    from src import data_loading                 # sub-project loader
    for r in rounds:
        slug, rnd = r["slug"], int(r["round"])
        try:
            session = data_loading.load_session(year, rnd, "Q")
        except Exception as exc:                 # noqa: BLE001
            print(f"  R{rnd} {slug}: cannot load Q ({exc!r}) - skipping race")
            continue
        names = _name_lookup(session.results)
        for pair in web_export.teammate_pairs(session.results):
            a, b = pair["a"], pair["b"]
            key = web_export.matchup_key(slug, a, b)
            base = {"key": key, "race": slug, "team": pair["team"],
                    "teamColor": pair["teamColor"], "a": a, "b": b}
            try:
                res = run.run_pipeline(year=year, gp=rnd, session="Q",
                                       driver_a=a, driver_b=b)
            except Exception as exc:             # RuntimeError / AssertionError / load
                entries.append({**base, "valid": False, "reason": str(exc)})
                print(f"  {key}: EXCLUDED - {exc}")
                continue
            meta = {"slug": slug, "eventName": r["eventName"], "round": rnd,
                    "year": year, "session": "Q",
                    "driverAName": names.get(a, a), "driverBName": names.get(b, b),
                    "team": pair["team"], "teamColor": pair["teamColor"]}
            payload = web_export.matchup_payload(res, meta)
            write_json_if_changed(DATA_DIR / f"{key}.json", payload)
            entries.append({**base, "valid": True,
                            "officialGapS": payload["meta"]["officialGapS"],
                            "significantCount": sum(1 for s in payload["sectors"]
                                                    if s["significant"])})
            print(f"  {key}: ok ({payload['meta']['officialGapS']:+.3f}s)")

    hero_key = web_export.matchup_key(HERO_SLUG, HERO_A, HERO_B)
    write_json_if_changed(DATA_DIR / "index.json",
                          web_export.build_index(hero_key, races, entries))
    print(f"\nDone. {sum(e['valid'] for e in entries)}/{len(entries)} matchups valid. "
          f"Review `git status web/public/data/decomp`, then commit.")


if __name__ == "__main__":
    main()
