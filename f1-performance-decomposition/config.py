"""Central configuration for the lap-time decomposition pipeline.

Everything that defines *what* we analyse lives here so the analysis can be
re-pointed at a different race / session / pair of drivers with a single edit.
Nothing downstream hardcodes a year, a driver code, or a grid resolution.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# What to analyse
# --------------------------------------------------------------------------- #
# v1 scope (deliberately narrow): one weekend, one session, two drivers.
# Qualifying is chosen over a race so we sidestep fuel-burn entirely and get
# flat-out laps. Antonelli vs Russell are team-mates in the same car, which
# removes the machinery from the comparison and leaves (mostly) the driver.
# Canada 2026 (round 5): Russell took pole, Antonelli alongside ~0.07s back -
# about as closely matched as a session gets, so the signal-vs-noise question is
# genuinely live. Antonelli's first F1 season is 2025, so the year must be >=2025.
YEAR = 2026
GRAND_PRIX = "Canada"          # any name FastF1's schedule accepts (or a round int)
SESSION = "Q"                  # 'Q' qualifying; 'R' race; 'S' sprint; etc.

# Sign convention used *everywhere*: delta = t(DRIVER_A) - t(DRIVER_B).
# A positive delta means DRIVER_A took longer, i.e. DRIVER_B is faster there.
DRIVER_A = "RUS"   # George Russell
DRIVER_B = "ANT"   # Kimi Antonelli (the team-mate of interest)

# --------------------------------------------------------------------------- #
# Resampling grid
# --------------------------------------------------------------------------- #
# Telemetry is sampled irregularly in time, and the two cars cover the lap at
# different speeds, so samples never line up. We interpolate every channel onto
# a fixed *distance* grid; 2 m is fine-grained enough to resolve braking zones
# without over-interpolating the underlying ~10 Hz telemetry.
GRID_RESOLUTION_M = 2.0

# --------------------------------------------------------------------------- #
# Micro-sector segmentation
# --------------------------------------------------------------------------- #
# Spec asks for 15-25 micro-sectors. Corner-anchored boundaries are preferred
# when the circuit's corner data is available; we fall back to equal-distance
# bins otherwise.
N_MICRO_SECTORS = 20
SEGMENT_BY_CORNERS = True

# --------------------------------------------------------------------------- #
# Time basis (see delta.py / REPORT.md §Method)
# --------------------------------------------------------------------------- #
# 'telemetry_time' : interpolate the car's measured Time channel onto distance.
#                    Primary choice - it is the car's own clock, no integration.
# 'speed_integral' : integrate 1/Speed over distance. Used as an independent
#                    cross-check that should agree to a few hundredths.
TIME_BASIS = "telemetry_time"

# --------------------------------------------------------------------------- #
# Lap cleaning (see data_loading.py)
# --------------------------------------------------------------------------- #
QUICKLAP_THRESHOLD = 1.07   # keep laps within 107% of the driver's own fastest
MIN_CLEAN_LAPS = 2          # below this we can still draw a curve but warn on stats

# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
N_BOOTSTRAP = 5000
CONFIDENCE = 0.95
RANDOM_SEED = 20240619      # fixed so the bootstrap is reproducible

# --------------------------------------------------------------------------- #
# Reconciliation tolerance
# --------------------------------------------------------------------------- #
# The cumulative delta curve's value at the finish line must match the official
# lap-time gap to within this many seconds, otherwise the time basis is wrong.
RECONCILE_TOLERANCE_S = 0.05

# Number of top *significant* micro-sectors to write up in the attribution.
N_KEY_SECTORS = 3

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "fastf1_cache"
FIGURES_DIR = ROOT / "outputs" / "figures"
TABLES_DIR = ROOT / "outputs" / "tables"
REPORT_PATH = ROOT / "REPORT.md"
