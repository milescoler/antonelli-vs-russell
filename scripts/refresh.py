#!/usr/bin/env python3
"""One-command refresh after a new race.

Usage:
    python scripts/refresh.py            # fetch missing + execute all notebooks + PDFs
    python scripts/refresh.py --no-pdf   # skip PDF export (faster iteration)

Workflow each round: edit RACES in src/season.py, run this, commit the changes.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.loaders import setup_cache          # noqa: E402
from src.season import RACES                 # noqa: E402
import fastf1                                 # noqa: E402

CACHE = ROOT / "fastf1_cache"
NOTEBOOKS = [
    "notebooks/01_antonelli_vs_russell.ipynb",
    "notebooks/02_how_antonelli_wins_races.ipynb",
    "notebooks/03_driver_vs_car_track_history.ipynb",
]
PDF_STEMS = {
    "notebooks/01_antonelli_vs_russell.ipynb": "01_antonelli_vs_russell",
    "notebooks/02_how_antonelli_wins_races.ipynb": "02_how_antonelli_wins_races",
    "notebooks/03_driver_vs_car_track_history.ipynb": "03_driver_vs_car_track_history",
}


def ensure_sessions():
    """Make sure each 2026 race's Q and R are downloaded into the cache."""
    setup_cache(str(CACHE))
    for race in RACES:
        for stype in ("Q", "R"):
            try:
                s = fastf1.get_session(2026, race, stype)
                s.load(telemetry=False, weather=False, messages=False, laps=False)
                print(f"  ok   {race} {stype}")
            except Exception as e:
                print(f"  FAIL {race} {stype}: {e!r}")


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()

    print("== ensuring 2026 sessions are cached ==")
    ensure_sessions()

    print("== executing notebooks ==")
    for nb in NOTEBOOKS:
        run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
             "--execute", "--inplace", nb, "--ExecutePreprocessor.timeout=1800"])

    if not args.no_pdf:
        print("== exporting PDFs ==")
        for nb, stem in PDF_STEMS.items():
            run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "pdf", nb])
            run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "pdf",
                 "--no-input", "--output", f"{stem}_no_code", nb])

    print("\nDone. Review `git status`, then commit the regenerated artifacts.")


if __name__ == "__main__":
    main()
