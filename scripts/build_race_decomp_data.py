#!/usr/bin/env python3
"""Pre-compute race-win decomposition JSON for the web flagship.

Per completed round: resolve winner vs P2, compute the start/pace/tyre factors
(factor 1 "where on track" is added by a later pass), assign a signal-vs-noise
verdict to each, and write web/public/data/race/<slug>.json + an index with
honest exclusion of races we can't decompose.

    python scripts/build_race_decomp_data.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import race as race_mod, race_win, teams      # noqa: E402
from src.loaders import setup_cache                     # noqa: E402

DATA_DIR = ROOT / "web" / "public" / "data" / "race"
CACHE = ROOT / "fastf1_cache"
HERO_SLUG = "monaco"   # a clean pole-to-flag win; NOT canadian (inherited)
DECOMP_ROOT = ROOT / "f1-performance-decomposition"


def _where_factor(year: int, rnd: int, winner: str, p2: str) -> dict:
    """Run the where-on-track engine via subprocess and return a factors.where dict."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "src.race_where",
             "--year", str(year), "--gp", str(rnd), "--a", winner, "--b", p2],
            cwd=str(DECOMP_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            return {
                "verdict": "insufficient",
                "magnitudeS": None,
                "headline": "where-on-track decomposition failed",
                "caveat": (r.stderr or "")[-300:],
                "decomp": None,
            }
        # Last line of stdout is the JSON (preceding lines may be log noise on stderr,
        # but we redirect logs there; still take last line defensively)
        last_line = r.stdout.strip().splitlines()[-1]
        payload = json.loads(last_line)
        v = race_win.verdict_from_where(payload)
        return {
            **v,
            "decomp": (None if payload.get("verdict") == "insufficient" else payload),
        }
    except Exception as exc:
        return {
            "verdict": "insufficient",
            "magnitudeS": None,
            "headline": "where-on-track decomposition errored",
            "caveat": str(exc),
            "decomp": None,
        }


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_json_if_changed(path: Path, obj) -> bool:
    text = _canonical(obj)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build_one_race(year: int, round_info: dict) -> dict:
    rnd, slug, name = round_info["round"], round_info["slug"], round_info["eventName"]
    session = race_mod.load_race_session(year, rnd)
    principals = race_win.principals_from_results(session.results)
    w, p2 = principals["winner"]["code"], principals["p2"]["code"]
    start_df = race_mod.start_summary(year, rnd, drv_a=w, drv_b=p2)
    stint_df = race_mod.stint_pace(year, rnd, [w, p2])
    deg_df = race_mod.tire_deg(year, rnd, [w, p2])
    gap_df = race_mod.gap_to_rival(year, rnd, w)
    payload = race_win.assemble_race(principals=principals, start_df=start_df, stint_df=stint_df,
                                     deg_df=deg_df, gap_df=gap_df, round_number=rnd, slug=slug,
                                     event_name=name, year=year)
    # Factor 1: where on track — computed via subprocess (non-fatal: failure → honest insufficient)
    print(f"  [{slug}] computing where-on-track factor (subprocess)…", flush=True)
    payload["factors"]["where"] = _where_factor(year, rnd, w, p2)
    return payload


def index_entry(*, slug, round_number, payload=None, reason=None) -> dict:
    if payload is not None:
        f = payload["factors"]
        return {"slug": slug, "round": int(round_number), "valid": True,
                "winner": payload["meta"]["winner"]["code"], "p2": payload["meta"]["p2"]["code"],
                "marginS": payload["meta"]["marginS"],
                "realFactorCount": sum(1 for k in f if f[k].get("verdict") == "real")}
    return {"slug": slug, "round": int(round_number), "valid": False, "reason": reason}


def main() -> None:
    argparse.ArgumentParser().parse_args()
    setup_cache(str(CACHE))
    season = 2026
    rounds = teams.list_completed_rounds(season)
    races = [{"slug": r["slug"], "name": r["eventName"], "round": r["round"]} for r in rounds]
    entries = []
    for ri in rounds:
        try:
            payload = build_one_race(season, ri)
        except Exception as exc:  # noqa: BLE001
            entries.append(index_entry(slug=ri["slug"], round_number=ri["round"], reason=str(exc)))
            print(f"  {ri['slug']}: EXCLUDED - {exc}")
            continue
        write_json_if_changed(DATA_DIR / f"{ri['slug']}.json", payload)
        entries.append(index_entry(slug=ri["slug"], round_number=ri["round"], payload=payload))
        print(f"  {ri['slug']}: ok ({payload['meta']['winner']['code']} by "
              f"{payload['meta']['marginS']}s)")
    index = {"hero": HERO_SLUG, "races": sorted(races, key=lambda r: r["round"]),
             "entries": sorted(entries, key=lambda e: e["round"])}
    write_json_if_changed(DATA_DIR / "index.json", index)
    print(f"\nDone. {sum(e['valid'] for e in entries)}/{len(entries)} races decomposed.")


if __name__ == "__main__":
    main()
