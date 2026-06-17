"""Single source of truth for the project's race list and historical window.

To bring the project current after a new Grand Prix:
  1. Append the new race name to RACES (must match the FastF1 event name well
     enough for fastf1.get_session(year, name, ...) to resolve it).
  2. Run `python scripts/refresh.py`.
  3. Commit the regenerated figures, notebooks, and PDFs.

Both notebooks and scripts/refresh.py import RACES/YEARS from here, so this is
the ONLY place to edit per new race.
"""

# 2026 season, in calendar order, through the most recent completed round.
# NOTE: round 7 is the *Barcelona* Grand Prix; do NOT use 'Spain', which FastF1
# resolves to the separate Madrid round (Spanish GP, R14, Sept 13).
RACES = ['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco', 'Barcelona']

# Historical window for the cross-year track-history chapter (inclusive).
YEARS = list(range(2010, 2026))  # 2010..2025
