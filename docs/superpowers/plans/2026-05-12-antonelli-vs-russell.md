# Antonelli vs Russell — v1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the v1 portfolio analysis: a segment-level comparison of Antonelli vs Russell across the first 4 rounds of 2026 qualifying, with a fully-populated notebook, two saved figures, a backfilled README, and one passing end-to-end consistency test.

**Architecture:** Pure-math segment functions in `src/segments.py`; orchestration + Q-session derivation + category labels in `src/benchmarks.py`; plotting helpers in `src/plotting.py`; the notebook is the narrative driver that calls into `src/` and saves figures. One end-to-end test in `tests/test_segments.py` asserts that the sum of per-segment deltas matches the lap-time delta within 0.1s.

**Tech Stack:** Python 3.12, FastF1, pandas, numpy, matplotlib, seaborn, pytest, Jupyter Lab.

**Reference spec:** [docs/superpowers/specs/2026-05-12-antonelli-vs-russell-design.md](../specs/2026-05-12-antonelli-vs-russell-design.md). Anything ambiguous, the spec is the source of truth.

**Working directory for all commands:** `/Users/mcoler/Documents/project-folder/f1_project`

---

## Chunk 1: Foundation — repo setup, smoke-test, deps, cleanup

### Task 1: Initialize git and configure ignores

**Files:**
- Create: `.gitignore` (overwrite, currently empty)
- Init: `.git/` (via `git init`)

- [ ] **Step 1: Initialize the git repo**

Run from the project root:

```bash
git init
```

Expected: `Initialized empty Git repository in /Users/mcoler/Documents/project-folder/f1_project/.git/`

- [ ] **Step 2: Populate `.gitignore`**

Overwrite `.gitignore` with:

```
fastf1_cache/
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
.venv/
.env
```

- [ ] **Step 3: Delete the stale notebook**

```bash
rm ant_vs_all.ipynb
```

Confirm with `ls *.ipynb 2>/dev/null` — expected: no output (no top-level notebooks remaining).

- [ ] **Step 4: First commit**

```bash
git add .gitignore
git commit -m "chore: init repo, add gitignore, drop stale notebook"
```

---

### Task 2: Smoke-confirm FastF1 works against all 4 races

**Files:**
- Read-only: `src/loaders.py`, `fastf1_cache/2026/...`

This is a one-off sanity check; no source changes. The goal is to fail fast if the installed FastF1 version can't open 2026 sessions, before pinning versions or writing code that depends on it.

- [ ] **Step 1: Run the smoke load from the repo root**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.loaders import setup_cache, load_qualifying_session, get_fastest_valid_lap, get_lap_telemetry
setup_cache('./fastf1_cache')
for race in ['Australia', 'China', 'Japan', 'Miami']:
    s = load_qualifying_session(2026, race)
    for drv in ['ANT', 'RUS']:
        lap = get_fastest_valid_lap(s, drv)
        tel = get_lap_telemetry(lap)
        print(f'{race} {drv}: lap={lap[\"LapTime\"]} tel_rows={len(tel)} max_d={tel[\"Distance\"].max():.0f}m')
print('OK')
"
```

Expected: 8 lines (4 races × 2 drivers) followed by `OK`. Any traceback means FastF1 needs a version bump before continuing.

- [ ] **Step 2: If the smoke fails, bump FastF1**

If Step 1 raises (likely a FastF1 internal API mismatch on 2026 data), upgrade:

```bash
pip install --upgrade fastf1
```

Re-run Step 1. If it still fails, stop and report to user — likely an upstream FastF1 issue.

- [ ] **Step 3: Capture installed versions for the next task**

```bash
pip freeze | grep -E "^(fastf1|pandas|numpy|matplotlib|jupyterlab|pytest)=="
```

Save the output — Task 3 will use it.

---

### Task 3: Rewrite `requirements.txt` with confirmed versions

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Overwrite `requirements.txt`**

Replace its contents with the exact pinned versions from Task 2 Step 3. Format:

```
fastf1==X.Y.Z
pandas==X.Y.Z
numpy==X.Y.Z
matplotlib==X.Y.Z
jupyterlab==X.Y.Z
pytest==X.Y.Z
```

(Use the exact versions from the smoke output. If any of these aren't installed, install them first with `pip install <name>` and re-run `pip freeze`. Note: seaborn is intentionally omitted — no code in this plan imports it.)

- [ ] **Step 2: Verify a clean install works**

Run:

```bash
pip install -r requirements.txt
```

Expected: "Requirement already satisfied" for everything, or fresh installs without errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: pin requirements after smoke-testing 2026 data load"
```

---

## Chunk 2: Core math — `segments.py` additions

### Task 4: Add `compute_segment_times` to `src/segments.py`

**Files:**
- Modify: `src/segments.py` (append new function; existing `resample_to_distance_grid` and `build_segments_from_corners` untouched)

**Spec reference:** §3 function signatures, §4 time-delta math.

- [ ] **Step 1: Append the function to `src/segments.py`**

Add at the bottom of the file:

```python
def compute_segment_times(
    telem_resampled: pd.DataFrame,
    segments: pd.DataFrame,
    step_m: float = DEFAULT_GRID_STEP_M,
) -> pd.DataFrame:
    """
    Compute per-segment time and min-speed from resampled telemetry.

    Args:
        telem_resampled: output of resample_to_distance_grid; must have
            Distance (meters), Speed (kph).
        segments: output of build_segments_from_corners; must have
            Segment, start_m, end_m, kind.
        step_m: distance grid step in meters; must match the step used when
            resampling.

    Returns:
        The input `segments` frame with two added columns:
          - min_speed (kph): min of Speed within [start_m, end_m).
          - time_s (seconds): sum of (step_m / speed_m_per_s) within [start_m, end_m).
    """
    speed_m_per_s = telem_resampled['Speed'].values * (1000.0 / 3600.0)
    distance = telem_resampled['Distance'].values

    min_speeds = []
    times = []
    for row in segments.itertuples():
        mask = (distance >= row.start_m) & (distance < row.end_m)
        seg_speed_kph = telem_resampled['Speed'].values[mask]
        seg_speed_mps = speed_m_per_s[mask]
        if len(seg_speed_mps) == 0:
            min_speeds.append(float('nan'))
            times.append(0.0)
            continue
        min_speeds.append(float(seg_speed_kph.min()))
        times.append(float((step_m / seg_speed_mps).sum()))

    out = segments.copy()
    out['min_speed'] = min_speeds
    out['time_s'] = times
    return out
```

- [ ] **Step 2: Validate on real Miami data**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.loaders import setup_cache, load_qualifying_session, get_fastest_valid_lap, get_lap_telemetry
from src.segments import resample_to_distance_grid, build_segments_from_corners, compute_segment_times
setup_cache('./fastf1_cache')
s = load_qualifying_session(2026, 'Miami')
lap = get_fastest_valid_lap(s, 'ANT')
tel = get_lap_telemetry(lap)
resampled = resample_to_distance_grid(tel)
segs = build_segments_from_corners(s.get_circuit_info(), tel['Distance'].max())
times = compute_segment_times(resampled, segs)
print(times[['Segment', 'kind', 'min_speed', 'time_s']].to_string())
print(f'Total reconstructed lap time: {times[\"time_s\"].sum():.3f}s')
print(f'Actual lap time: {lap[\"LapTime\"].total_seconds():.3f}s')
"
```

Expected:
- All segments have `time_s > 0` and finite `min_speed`.
- Total reconstructed lap time is within ~0.5s of actual lap time (resampling/Riemann error; the consistency test in Task 9 uses the much-tighter delta-of-deltas tolerance).
- `min_speed` values look plausible: slow corners ~80–130 kph, fast corners 200+, straights at the top of the speed range.

- [ ] **Step 3: Commit**

```bash
git add src/segments.py
git commit -m "feat(segments): add compute_segment_times"
```

---

### Task 5: Add `compute_segment_deltas` to `src/segments.py`

**Files:**
- Modify: `src/segments.py` (append)

**Spec reference:** §3 function signatures, §4 time-delta math (sign convention).

- [ ] **Step 1: Append the function**

Add at the bottom of `src/segments.py`:

```python
def compute_segment_deltas(
    times_a: pd.DataFrame,
    times_b: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute per-segment time delta between two drivers.

    Args:
        times_a: output of compute_segment_times for driver A.
        times_b: output of compute_segment_times for driver B.
            Both must have the same Segment values in the same order.

    Returns:
        DataFrame with columns:
          Segment, kind, start_m, end_m, min_speed, time_a_s, time_b_s, delta_s
        where:
          - min_speed = elementwise min(times_a.min_speed, times_b.min_speed)
            (the deeper of the two; used for category classification).
          - delta_s = time_b_s - time_a_s.
            POSITIVE = driver A faster than driver B.
    """
    if not (times_a['Segment'].values == times_b['Segment'].values).all():
        raise ValueError("times_a and times_b must have identical Segment ordering")

    out = times_a[['Segment', 'kind', 'start_m', 'end_m']].copy()
    out['min_speed'] = np.minimum(times_a['min_speed'].values, times_b['min_speed'].values)
    out['time_a_s'] = times_a['time_s'].values
    out['time_b_s'] = times_b['time_s'].values
    out['delta_s'] = out['time_b_s'] - out['time_a_s']
    return out
```

- [ ] **Step 2: Validate on real Miami data (ANT vs RUS)**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.loaders import setup_cache, load_qualifying_session, get_fastest_valid_lap, get_lap_telemetry
from src.segments import resample_to_distance_grid, build_segments_from_corners, compute_segment_times, compute_segment_deltas
setup_cache('./fastf1_cache')
s = load_qualifying_session(2026, 'Miami')
segs = build_segments_from_corners(s.get_circuit_info(), get_lap_telemetry(get_fastest_valid_lap(s, 'ANT'))['Distance'].max())
def times_for(drv):
    lap = get_fastest_valid_lap(s, drv)
    tel = get_lap_telemetry(lap)
    return compute_segment_times(resample_to_distance_grid(tel), segs), lap['LapTime'].total_seconds()
ta, lt_a = times_for('ANT')
tb, lt_b = times_for('RUS')
d = compute_segment_deltas(ta, tb)
print(d[['Segment', 'kind', 'min_speed', 'delta_s']].to_string())
print(f'sum(delta_s): {d[\"delta_s\"].sum():.3f}s')
print(f'actual lap delta (RUS - ANT): {lt_b - lt_a:.3f}s')
print(f'difference (should be < 0.1): {abs(d[\"delta_s\"].sum() - (lt_b - lt_a)):.3f}s')
"
```

Expected: the "difference" line prints a value below 0.1. If it's larger, there's a bug in `compute_segment_times` or `compute_segment_deltas`.

- [ ] **Step 3: Commit**

```bash
git add src/segments.py
git commit -m "feat(segments): add compute_segment_deltas"
```

---

### Task 6: Fix the stale docstring on `build_segments_from_corners`

**Files:**
- Modify: `src/segments.py` lines around `build_segments_from_corners` docstring

The existing docstring claims the function returns `'Position'` and `'Compound'` columns — neither is actually returned. This was flagged by the spec review.

- [ ] **Step 1: Edit the docstring**

Replace the docstring of `build_segments_from_corners` with:

```python
    """
    Build a DataFrame of track segments by clustering corners and filling the
    straights between them.

    Args:
        circuit_info: FastF1 CircuitInfo object (has a `corners` DataFrame with
            a `Distance` column).
        lap_distance_m: Total lap distance in meters.
        threshold_m: Corners within this distance of each other are merged into
            a single segment.

    Returns:
        DataFrame with columns:
          - Segment: label (e.g. 'C1', 'S2')
          - start_m, end_m: segment bounds in meters
          - kind: 'corner' or 'straight'
        Sorted by start_m.
    """
```

- [ ] **Step 2: Commit**

```bash
git add src/segments.py
git commit -m "docs(segments): fix stale docstring on build_segments_from_corners"
```

---

## Chunk 3: Orchestration — `benchmarks.py`

### Task 7: Add `_derive_q_session` helper in `src/benchmarks.py`

**Files:**
- Create: `src/benchmarks.py`

**Spec reference:** §4 Q-session derivation.

- [ ] **Step 1: Create `src/benchmarks.py` with imports and the helper**

```python
"""
Teammate comparison orchestration: ties loaders + segments together and adds
the interpretive layer (segment categories, Q-session derivation, metadata).
"""

from __future__ import annotations
from typing import Optional
import warnings

import numpy as np
import pandas as pd

from src.loaders import (
    load_qualifying_session,
    get_fastest_valid_lap,
    get_lap_telemetry,
)
from src.segments import (
    resample_to_distance_grid,
    build_segments_from_corners,
    compute_segment_times,
    compute_segment_deltas,
)

SLOW_CORNER_MAX_KPH = 130.0
FAST_CORNER_MIN_KPH = 200.0


def _derive_q_session(session, lap) -> Optional[int]:
    """
    Determine which Q-segment (1, 2, or 3) a given lap belongs to.

    Strategy:
      1. Preferred: use session.session_status to find the 'Started' transitions
         for each Q-segment and bucket lap.LapStartTime accordingly.
      2. Fallback: cluster all drivers' LapStartTimes and split on the two
         largest gaps (the Q1->Q2 and Q2->Q3 breaks).

    Returns:
        1, 2, or 3 if derivation succeeds; None if neither strategy works.
    """
    lap_start = lap.get('LapStartTime')
    if pd.isna(lap_start):
        return None

    # Strategy 1: session.session_status transitions.
    try:
        status = session.session_status
        if status is not None and len(status) > 0 and 'Status' in status.columns:
            starts = status[status['Status'].astype(str).str.lower().eq('started')]
            if len(starts) >= 3:
                boundaries = sorted(starts['Time'].iloc[:3].tolist())
                # boundaries[0] = Q1 start, [1] = Q2 start, [2] = Q3 start
                if lap_start >= boundaries[2]:
                    return 3
                if lap_start >= boundaries[1]:
                    return 2
                if lap_start >= boundaries[0]:
                    return 1
    except Exception:
        pass

    # Strategy 2: cluster all lap start times, split on the two biggest gaps.
    try:
        all_starts = session.laps['LapStartTime'].dropna().sort_values().tolist()
        if len(all_starts) < 3:
            return None
        gaps = [(all_starts[i+1] - all_starts[i], i) for i in range(len(all_starts)-1)]
        gaps.sort(reverse=True, key=lambda x: x[0])
        # Two biggest gaps mark Q1->Q2 and Q2->Q3 boundaries.
        cut_idxs = sorted(idx for _, idx in gaps[:2])
        q2_start = all_starts[cut_idxs[0] + 1]
        q3_start = all_starts[cut_idxs[1] + 1]
        if lap_start >= q3_start:
            return 3
        if lap_start >= q2_start:
            return 2
        return 1
    except Exception:
        return None
```

- [ ] **Step 2: Validate the helper on Miami**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.loaders import setup_cache, load_qualifying_session, get_fastest_valid_lap
from src.benchmarks import _derive_q_session
setup_cache('./fastf1_cache')
s = load_qualifying_session(2026, 'Miami')
for drv in ['ANT', 'RUS']:
    lap = get_fastest_valid_lap(s, drv)
    print(f'{drv}: Q{_derive_q_session(s, lap)}  lap_time={lap[\"LapTime\"]}')
"
```

Expected: both drivers print Q1, Q2, or Q3 (likely Q3 for Mercedes drivers at Miami). If either prints `None`, the derivation gracefully degraded — note which strategy failed and continue.

- [ ] **Step 3: Commit**

```bash
git add src/benchmarks.py
git commit -m "feat(benchmarks): add _derive_q_session helper with fallback"
```

---

### Task 8: Add `compare_teammates` in `src/benchmarks.py`

**Files:**
- Modify: `src/benchmarks.py` (append)

**Spec reference:** §3 function signatures, §4 segment categories.

- [ ] **Step 1: Append `_classify_segment` and `compare_teammates`**

Add to `src/benchmarks.py`:

```python
def _classify_segment(kind: str, min_speed: float) -> str:
    """Map (kind, min_speed) -> category. See spec §4 for thresholds."""
    if kind == 'straight':
        return 'straight'
    if pd.isna(min_speed):
        return 'unknown'
    if min_speed < SLOW_CORNER_MAX_KPH:
        return 'slow_corner'
    if min_speed < FAST_CORNER_MIN_KPH:
        return 'medium_corner'
    return 'fast_corner'


def compare_teammates(
    year: int,
    round_or_name,
    drv_a: str = 'ANT',
    drv_b: str = 'RUS',
    threshold_m: float = 250.0,
) -> dict:
    """
    End-to-end teammate comparison for one qualifying session.

    Returns:
        {
          "segments": DataFrame with columns
              [Segment, kind, start_m, end_m, min_speed,
               time_a_s, time_b_s, delta_s, category],
          "meta": {
              "year", "round", "event_name",
              "lap_time_a_s", "lap_time_b_s", "lap_delta_s",
              "q_session_a", "q_session_b", "q_mismatch",
          },
        }

    Sign convention: delta_s = time_b_s - time_a_s, so POSITIVE = drv_a faster.
    """
    session = load_qualifying_session(year, round_or_name)
    lap_a = get_fastest_valid_lap(session, drv_a)
    lap_b = get_fastest_valid_lap(session, drv_b)
    tel_a = get_lap_telemetry(lap_a)
    tel_b = get_lap_telemetry(lap_b)

    # Shared segments built from circuit info; use the longer of the two
    # telemetry distances as the lap length.
    lap_distance_m = max(tel_a['Distance'].max(), tel_b['Distance'].max())
    segs = build_segments_from_corners(
        session.get_circuit_info(),
        lap_distance_m=lap_distance_m,
        threshold_m=threshold_m,
    )

    resampled_a = resample_to_distance_grid(tel_a)
    resampled_b = resample_to_distance_grid(tel_b)
    times_a = compute_segment_times(resampled_a, segs)
    times_b = compute_segment_times(resampled_b, segs)
    deltas = compute_segment_deltas(times_a, times_b)
    deltas['category'] = [
        _classify_segment(k, m) for k, m in zip(deltas['kind'], deltas['min_speed'])
    ]

    q_a = _derive_q_session(session, lap_a)
    q_b = _derive_q_session(session, lap_b)
    q_mismatch = (q_a is not None) and (q_b is not None) and (q_a != q_b)

    lap_time_a_s = lap_a['LapTime'].total_seconds()
    lap_time_b_s = lap_b['LapTime'].total_seconds()

    meta = {
        'year': year,
        'round': int(session.event['RoundNumber']),
        'event_name': str(session.event['EventName']),
        'lap_time_a_s': lap_time_a_s,
        'lap_time_b_s': lap_time_b_s,
        'lap_delta_s': lap_time_b_s - lap_time_a_s,
        'q_session_a': q_a,
        'q_session_b': q_b,
        'q_mismatch': q_mismatch,
    }
    return {'segments': deltas, 'meta': meta}
```

- [ ] **Step 2: Validate on Miami**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.loaders import setup_cache
from src.benchmarks import compare_teammates
setup_cache('./fastf1_cache')
r = compare_teammates(2026, 'Miami')
print('--- meta ---')
for k, v in r['meta'].items():
    print(f'  {k}: {v}')
print('--- segments (head) ---')
print(r['segments'].head(8).to_string())
print(f'--- consistency: sum(delta_s) - lap_delta_s = {r[\"segments\"][\"delta_s\"].sum() - r[\"meta\"][\"lap_delta_s\"]:.4f}s ---')
print('--- category counts ---')
print(r['segments']['category'].value_counts().to_string())
"
```

Expected:
- meta dict prints with sensible values
- consistency line shows a difference well below 0.1s
- category counts include at least 'slow_corner', 'medium_corner', 'straight'; 'fast_corner' may or may not appear depending on the circuit

- [ ] **Step 3: Run the same check on the other 3 races**

Change `'Miami'` to `'Australia'`, `'China'`, `'Japan'` in the above command (one at a time). Confirm:
- Each one returns a meta dict and segments frame.
- Each consistency line stays below 0.1s.
- The combined category counts across all 4 races include all 4 categories. If `fast_corner` never appears or `slow_corner` dominates everywhere, threshold tuning may be needed (note for Chunk 6).

- [ ] **Step 4: Commit**

```bash
git add src/benchmarks.py
git commit -m "feat(benchmarks): add compare_teammates with category classification"
```

---

## Chunk 4: The consistency test

### Task 9: Write the end-to-end test

**Files:**
- Modify: `tests/test_segments.py` (currently empty)
- Create: `tests/__init__.py` if absent

**Spec reference:** §6.

- [ ] **Step 1: Confirm `tests/__init__.py`**

```bash
ls tests/__init__.py 2>/dev/null || touch tests/__init__.py
```

- [ ] **Step 2: Write `tests/test_segments.py`**

```python
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
```

- [ ] **Step 3: Run the test**

```bash
pytest tests/test_segments.py -v
```

Expected: `1 passed`. If it fails with the "diverges by ..." assertion, there's a bug in segments.py or benchmarks.py — investigate before continuing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_segments.py tests/__init__.py
git commit -m "test: add end-to-end segment-delta consistency check"
```

---

## Chunk 5: Plotting helpers

### Task 10: Implement `plot_category_deltas` in `src/plotting.py`

**Files:**
- Create: `src/plotting.py`

**Spec reference:** §3 plotting, §4 aggregation (headline chart).

- [ ] **Step 1: Create `src/plotting.py`**

```python
"""
Styled chart helpers for the Antonelli-vs-Russell analysis. Plotting functions
take pre-shaped DataFrames — no FastF1 imports, no filesystem awareness.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CATEGORY_ORDER = ['slow_corner', 'medium_corner', 'fast_corner', 'straight']
CATEGORY_LABELS = {
    'slow_corner': 'Slow corners\n(<130 kph min)',
    'medium_corner': 'Medium corners\n(130–200 kph)',
    'fast_corner': 'Fast corners\n(>200 kph min)',
    'straight': 'Straights',
}


def plot_category_deltas(
    all_races_df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Headline chart: per-category mean delta across races, with each race
    overlaid as a small dot.

    Args:
        all_races_df: concatenated per-segment frames across all races.
            Required columns: category, delta_s, event_name.
        save_path: if given, save PNG to this path at 150 dpi.

    Returns:
        The matplotlib Figure.

    Sign convention: positive delta_s = driver A faster.
    """
    cats_present = [c for c in CATEGORY_ORDER if c in all_races_df['category'].unique()]
    means = (
        all_races_df.groupby('category')['delta_s']
        .mean()
        .reindex(cats_present)
    )
    fig, ax = plt.subplots(figsize=(9, 5.5))

    x = np.arange(len(cats_present))
    ax.bar(x, means.values, width=0.55, color='#1f77b4', alpha=0.85, zorder=2)
    ax.axhline(0, color='black', linewidth=0.8, zorder=1)

    # Per-race dots
    events = sorted(all_races_df['event_name'].unique())
    for i, cat in enumerate(cats_present):
        per_race = all_races_df[all_races_df['category'] == cat].groupby('event_name')['delta_s'].mean()
        ax.scatter(
            [i + 0.18] * len(per_race),
            per_race.values,
            color='black', s=22, zorder=3, alpha=0.7,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_LABELS[c] for c in cats_present])
    ax.set_ylabel('Time delta per category (s)\npositive → Antonelli faster')
    ax.set_title('Where does Antonelli gain or lose time vs Russell?\n2026 Qualifying, first 4 rounds')
    ax.grid(axis='y', linestyle='--', alpha=0.35, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig
```

- [ ] **Step 2: Validate by rendering with combined real data**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from src.loaders import setup_cache
from src.benchmarks import compare_teammates
from src.plotting import plot_category_deltas
setup_cache('./fastf1_cache')
parts = []
for race in ['Australia', 'China', 'Japan', 'Miami']:
    r = compare_teammates(2026, race)
    df = r['segments'].copy()
    df['event_name'] = r['meta']['event_name']
    parts.append(df)
all_df = pd.concat(parts, ignore_index=True)
fig = plot_category_deltas(all_df, save_path='figures/_plotting_test.png')
print('Saved figures/_plotting_test.png')
print(all_df['category'].value_counts())
"
```

Expected: PNG written without error. Open `figures/_plotting_test.png` and confirm:
- 4 bars (or fewer if a category is absent), labeled, with 0-line visible
- Per-race dots overlaid
- No clipping or overlap problems
- Title and y-axis label readable

Delete the test PNG (`rm figures/_plotting_test.png`) once verified.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py
git commit -m "feat(plotting): add plot_category_deltas (headline chart)"
```

---

### Task 11: Implement `plot_lap_delta_by_round` in `src/plotting.py`

**Files:**
- Modify: `src/plotting.py` (append)

- [ ] **Step 1: Append the function**

```python
def plot_lap_delta_by_round(
    meta_df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Trajectory chart: total lap-time delta by race round.

    Args:
        meta_df: one row per race. Required columns: round, event_name, lap_delta_s.
        save_path: if given, save PNG at 150 dpi.
    """
    df = meta_df.sort_values('round').reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df['round'], df['lap_delta_s'], marker='o', color='#1f77b4', linewidth=2, markersize=8)
    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(df['round'])
    ax.set_xticklabels([f"R{r}\n{n}" for r, n in zip(df['round'], df['event_name'])])
    ax.set_ylabel('Lap-time delta (s)\npositive → Antonelli faster')
    ax.set_title('Antonelli vs Russell — total qualifying lap delta by round')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig
```

- [ ] **Step 2: Validate**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from src.loaders import setup_cache
from src.benchmarks import compare_teammates
from src.plotting import plot_lap_delta_by_round
setup_cache('./fastf1_cache')
metas = []
for race in ['Australia', 'China', 'Japan', 'Miami']:
    metas.append(compare_teammates(2026, race)['meta'])
meta_df = pd.DataFrame(metas)
fig = plot_lap_delta_by_round(meta_df, save_path='figures/_traj_test.png')
print('Saved figures/_traj_test.png')
print(meta_df[['round', 'event_name', 'lap_delta_s']].to_string())
"
```

Open `figures/_traj_test.png`, verify the chart has 4 labeled points and looks readable. Delete the test PNG.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py
git commit -m "feat(plotting): add plot_lap_delta_by_round (trajectory chart)"
```

---

## Chunk 6: The notebook

### Task 12: Populate `notebooks/01_antonelli_vs_russell.ipynb`

**Files:**
- Modify: `notebooks/01_antonelli_vs_russell.ipynb` (currently empty)
- Create: `figures/headline_segment_delta.png`, `figures/lap_delta_by_round.png`

**Spec reference:** §5 notebook structure.

The notebook is best built up by hand in Jupyter Lab (rather than written as raw JSON). Below is the cell-by-cell content to enter, in order. Use `jupyter lab notebooks/01_antonelli_vs_russell.ipynb` to open.

- [ ] **Step 1: Cell 1 — title (markdown)**

```markdown
# Antonelli vs Russell — 2026 Qualifying, First Four Rounds

Where is Kimi Antonelli closing the gap to George Russell, and where is he still losing time? This notebook compares both Mercedes drivers' fastest qualifying laps across the first four rounds of 2026, broken down by track segment. See the [project README](../README.md) for full method and limitations.
```

- [ ] **Step 2: Cell 2 — setup (code)**

```python
%matplotlib inline
import sys
sys.path.insert(0, '..')
import pandas as pd
import matplotlib.pyplot as plt

from src.loaders import setup_cache
from src.benchmarks import compare_teammates
from src.plotting import plot_category_deltas, plot_lap_delta_by_round

setup_cache('../fastf1_cache')
RACES = ['Australia', 'China', 'Japan', 'Miami']
```

- [ ] **Step 3: Cell 3 — method (markdown)**

```markdown
## Method (briefly)

For each race: load qualifying, take each driver's fastest valid lap, resample telemetry onto a 5 m distance grid, and segment the track from FastF1's `circuit_info.corners` (corners within 250 m grouped together, straights filled in between). Per-segment time is the sum of `step / speed` across the grid points inside that segment; the delta is `time(Russell) − time(Antonelli)`, so **positive = Antonelli faster**.

Each segment is classified into one of four categories by its minimum speed: slow corner (<130 kph), medium corner (130–200 kph), fast corner (>200 kph), or straight.
```

- [ ] **Step 4: Cell 4 — load all races (code)**

```python
results = {race: compare_teammates(2026, race) for race in RACES}

meta_df = pd.DataFrame([results[r]['meta'] for r in RACES])
summary = meta_df[['round', 'event_name', 'lap_time_a_s', 'lap_time_b_s', 'lap_delta_s', 'q_session_a', 'q_session_b', 'q_mismatch']]
summary.columns = ['Round', 'Race', 'ANT lap (s)', 'RUS lap (s)', 'Δ lap (s)', 'ANT Q', 'RUS Q', 'Q mismatch']
summary
```

Run this cell. Expected: a tidy 4-row table.

- [ ] **Step 4b: Cell 4b — explicit Q-mismatch warnings (code)**

Add a cell immediately after Cell 4 that surfaces any per-race Q-mismatch as a visible warning (the table column flags it, but a callout is more readable):

```python
mismatch_races = [r['meta']['event_name'] for r in results.values() if r['meta']['q_mismatch']]
unknown_races = [r['meta']['event_name'] for r in results.values() if r['meta']['q_session_a'] is None or r['meta']['q_session_b'] is None]
if mismatch_races:
    print("⚠ Q-session mismatch — drivers' fastest valid laps came from different Q-segments at:")
    for race in mismatch_races:
        meta = next(r['meta'] for r in results.values() if r['meta']['event_name'] == race)
        print(f"    {race}: ANT Q{meta['q_session_a']} vs RUS Q{meta['q_session_b']} — track evolution likely confounds this delta")
if unknown_races:
    print("⚠ Q-session could not be determined for:", ", ".join(unknown_races))
if not mismatch_races and not unknown_races:
    print("No Q-session mismatches across the 4 races.")
```

- [ ] **Step 5: Cell 5 — sanity check (markdown + code)**

Markdown cell:

```markdown
## Sanity check

The segmentation logic is only useful if the segment deltas sum back to the actual lap-time delta. The table below verifies this on real telemetry: any `|Δ|` above 0.1 s would indicate a bug.
```

Code cell:

```python
sanity = []
for race, r in results.items():
    sum_deltas = float(r['segments']['delta_s'].sum())
    lap_delta = float(r['meta']['lap_delta_s'])
    sanity.append({
        'Race': r['meta']['event_name'],
        'Σ segment Δ (s)': round(sum_deltas, 4),
        'Lap-time Δ (s)': round(lap_delta, 4),
        '|residual| (s)': round(abs(sum_deltas - lap_delta), 5),
    })
pd.DataFrame(sanity)
```

Run. Expected: all `|residual|` values well below 0.1 s.

- [ ] **Step 6: Cell 6 — category counts per circuit (code)**

```python
cat_check = pd.concat([
    r['segments'].assign(event_name=r['meta']['event_name'])
    for r in results.values()
])
cat_check.groupby(['event_name', 'category']).size().unstack(fill_value=0)
```

Run. Sanity: every circuit should have at least one slow corner and one straight. If `fast_corner` is empty across all circuits, the speed threshold may need adjustment — note this and discuss in the caveats section.

- [ ] **Step 7: Cell 7 — headline chart (markdown + code)**

Markdown:

```markdown
## Headline finding — where does the time go?

Each bar is the mean per-category delta across all four races. Black dots show each individual race's per-category mean — they tell you whether the average reflects a consistent pattern or a noisy one.
```

Code:

```python
all_segs = pd.concat([
    r['segments'].assign(event_name=r['meta']['event_name'])
    for r in results.values()
], ignore_index=True)

fig = plot_category_deltas(all_segs, save_path='../figures/headline_segment_delta.png')
plt.show()
```

Run and confirm the figure renders and saves.

- [ ] **Step 8: Cell 8 — headline interpretation (markdown)**

Write a 2–3 sentence interpretation based on what the chart actually shows. Template (fill in real numbers after running):

```markdown
The pattern is consistent across rounds: Antonelli loses **{X} s/lap** on average in slow corners and **{Y} s/lap** in medium corners, but is essentially level with Russell on straights and in fast corners. Slow-corner gap is the dominant driver of the overall lap-time deficit — see the per-race dots to confirm this isn't being pulled by a single outlier race.
```

Replace `{X}` and `{Y}` with the values from Cell 7.

- [ ] **Step 9: Cell 9 — trajectory (markdown + code)**

Markdown:

```markdown
## Trajectory — is the gap closing?
```

Code:

```python
fig = plot_lap_delta_by_round(meta_df, save_path='../figures/lap_delta_by_round.png')
plt.show()
```

- [ ] **Step 10: Cell 10 — trajectory interpretation (markdown)**

Template:

```markdown
Over four rounds, the lap-time gap has gone from {X1} s at Australia to {X4} s at Miami — {a narrowing | flat | widening} trend. Four data points is too few to claim a real trajectory, but it's not inconsistent with the expected rookie-progression direction.
```

- [ ] **Step 11: Cell 11 — per-race detail (markdown + code, collapsible)**

Markdown:

```markdown
## Per-race detail (appendix)

For each race, the raw per-segment delta. Useful for curious readers; not the main story.
```

Code (one cell, loops over races):

```python
fig, axes = plt.subplots(len(RACES), 1, figsize=(11, 2.6 * len(RACES)), sharex=False)
for ax, race in zip(axes, RACES):
    r = results[race]
    segs = r['segments'].sort_values('start_m')
    colors = ['#d62728' if d < 0 else '#1f77b4' for d in segs['delta_s']]
    ax.bar(segs['Segment'], segs['delta_s'], color=colors)
    ax.axhline(0, color='black', linewidth=0.6)
    ax.set_title(f"{r['meta']['event_name']} — Δ per segment (positive = ANT faster)", loc='left', fontsize=10)
    ax.set_ylabel('Δ (s)')
    ax.tick_params(axis='x', rotation=45)
fig.tight_layout()
plt.show()
```

- [ ] **Step 12: Cell 12 — caveats (markdown)**

```markdown
## Caveats

- **Sample size: four races.** Findings are directional, not conclusive.
- **Q-session timing.** Q1 / Q2 / Q3 happen on an evolving track. The summary table flags any race where the two drivers' fastest valid laps came from different Q-segments; treat the delta on those races with extra skepticism.
- **Setup divergence.** Mercedes drivers do not always run identical setups. Public telemetry can't separate driver from setup.
- **Traffic and tire age within Q.** Out-laps, in-laps, and intra-session tire age all affect achievable lap time.

These caveats are why the README frames this as a "careful look at what the telemetry shows," not a verdict on relative driver skill.
```

- [ ] **Step 13: Cell 13 — conclusion (markdown)**

Write a 3–4 sentence conclusion that matches what the data actually shows. Template:

```markdown
## What we learned

Across the first four rounds of 2026 qualifying, Antonelli's deficit to Russell is concentrated in {category}, while he matches his teammate in {other category}. {Trajectory observation}. The honest read is that {one sentence on what this means for the rookie-evaluation question}.

The same framework will get re-run after each race for the rest of 2026 — see [What's next](../README.md#whats-next) for the extensions.
```

- [ ] **Step 14: Run all cells top-to-bottom**

In Jupyter Lab: Kernel → Restart and Run All. Confirm:
- No errors
- Two PNGs appear in `figures/`
- Every markdown interpretation cell has been filled with real numbers (not `{X}` placeholders)

- [ ] **Step 15: Verify saved figures look right**

```bash
ls -la figures/
```

Expected: `headline_segment_delta.png` and `lap_delta_by_round.png` both present. Open both in Preview and sanity-check titles, labels, no clipping.

- [ ] **Step 16: Commit**

```bash
git add notebooks/01_antonelli_vs_russell.ipynb figures/
git commit -m "feat: populate v1 analysis notebook and save figures"
```

---

## Chunk 7: README backfill and final polish

### Task 13: Backfill `README.md`

**Files:**
- Modify: `README.md`

Replace every `{TBD}` and `{placeholder}` with real values from the notebook run.

- [ ] **Step 1: Backfill the "Headline findings" section**

Read your notebook's Cells 8 and 10 — those have the real numbers. Edit `README.md` lines 9–17:

- Replace `{TBD}` for "Lap-time gap to Russell" with the mean of `meta_df['lap_delta_s']`, sign-flipped to make it a positive gap statement (e.g., "0.36 s on average across qualifying").
- Replace `{TBD — e.g. ...}` for "Where Antonelli loses time" with the dominant slow/medium category finding.
- Replace `{TBD — e.g. ...}` for "Where he's already competitive" with the categories where the delta is near zero.
- Replace `{TBD — e.g. ...}` for "Trajectory" with the round-1 vs round-4 observation.

- [ ] **Step 2: Backfill the "Method" section**

In `README.md`:
- Replace `{race list}` (line 32) with: "Australia, China, Japan, Miami".

- [ ] **Step 3: Backfill the "Reproducing" section**

- Replace `{X}MB` with the actual cache size: run `du -sh fastf1_cache/` and use the output.
- Replace `{version}` with the FastF1 version from `requirements.txt`.
- Add `pytest tests/` as a verify step:

```markdown
After install, verify the math wires correctly:
\`\`\`bash
pytest tests/
\`\`\`
```

- [ ] **Step 4: Backfill the "Limitations" section**

- Replace `{N}` in "Sample size. {N} qualifying sessions." with `4`.

- [ ] **Step 5: Update the "About" section**

- Replace `{TBD}` for LinkedIn with the actual URL or remove the placeholder if you'd rather not link.

- [ ] **Step 6: Verify no `{TBD}` or `{X}` placeholders remain**

```bash
grep -nE '\{(TBD|X|N|version|race list|your-handle)' README.md
```

Expected: no output (every placeholder filled). The `{your-handle}` in the git-clone line can either be filled with the eventual GitHub handle or left as-is if not yet pushed; if leaving as-is, note it as a known TODO in the commit message.

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: backfill README with v1 findings, race list, and version pins"
```

---

### Task 14: Final end-to-end verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the test suite**

```bash
pytest tests/ -v
```

Expected: `1 passed`.

- [ ] **Step 2: Restart and re-run the notebook**

Open `notebooks/01_antonelli_vs_russell.ipynb`, Kernel → Restart and Run All. Confirm:
- All cells execute without errors
- All markdown interpretation cells contain real numbers (no `{X}` left)
- Both PNGs in `figures/` were regenerated

- [ ] **Step 3: Confirm `ant_vs_all.ipynb` is gone**

```bash
ls ant_vs_all.ipynb 2>/dev/null || echo "deleted"
```

Expected: `deleted`.

- [ ] **Step 4: Confirm the repo state is clean**

```bash
git status
```

Expected: `nothing to commit, working tree clean`. If any unexpected files appear (e.g., `.ipynb_checkpoints/` slipped in), update `.gitignore` and commit separately.

- [ ] **Step 5: Final summary commit (optional, only if anything was tidied in Step 4)**

```bash
git add -A
git commit -m "chore: final cleanup pass"
```

- [ ] **Step 6: Print done**

The project is now complete per the v1 spec. Stop here. Do not start on any "What's next" extensions — those are explicitly out of scope.

---

## Done

Final deliverables checklist (verify all true):

- [ ] `tests/test_segments.py` passes via `pytest tests/`
- [ ] `notebooks/01_antonelli_vs_russell.ipynb` runs top-to-bottom with no errors
- [ ] `figures/headline_segment_delta.png` exists and is referenced in README
- [ ] `figures/lap_delta_by_round.png` exists
- [ ] `README.md` has no `{TBD}` / `{X}` / `{N}` placeholders left (`{your-handle}` may remain pending push)
- [ ] `requirements.txt` has the pinned versions confirmed by the smoke test
- [ ] `ant_vs_all.ipynb` is deleted
- [ ] `.gitignore` excludes `fastf1_cache/`, `__pycache__/`, `.ipynb_checkpoints/`, `.DS_Store`
- [ ] Git history has incremental commits, one per task
