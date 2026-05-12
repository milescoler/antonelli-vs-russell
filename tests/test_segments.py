"""
End-to-end consistency check: the sum of per-segment deltas across a real
qualifying lap must match the lap-time delta within 0.1 seconds.

This is the README's promised sanity check — if it fails, the segment-time
math has a bug.
"""

from pathlib import Path
import pytest

from src.loaders import setup_cache
from src.benchmarks import compare_teammates

CACHE_DIR = Path(__file__).resolve().parent.parent / "fastf1_cache"
MIAMI_DIR = CACHE_DIR / "2026" / "2026-05-03_Miami_Grand_Prix"


@pytest.fixture(scope="module", autouse=True)
def _enable_cache():
    if not MIAMI_DIR.exists():
        pytest.skip(
            "FastF1 cache not populated for Miami 2026 — "
            "run notebooks/00_scratch_fastf1.ipynb once to populate."
        )
    setup_cache(str(CACHE_DIR))


def test_segment_deltas_sum_matches_lap_delta():
    result = compare_teammates(2026, "Miami")
    sum_deltas = float(result["segments"]["delta_s"].sum())
    lap_delta = float(result["meta"]["lap_delta_s"])
    diff = abs(sum_deltas - lap_delta)
    assert diff < 0.1, (
        f"Segment-delta sum diverges from lap delta by {diff:.4f}s "
        f"(sum={sum_deltas:.4f}, lap_delta={lap_delta:.4f})"
    )
