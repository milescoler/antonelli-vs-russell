# Antonelli vs Russell — Segment-Level Teammate Comparison: Design Spec

**Date:** 2026-05-12
**Author:** Cole Richards (with Claude)
**Status:** Approved (pending spec review)

---

## 1. Purpose & context

Finish v1 of the Antonelli-vs-Russell project: a portfolio-quality segment-level
comparison of the two Mercedes drivers across the first 4 rounds of 2026 qualifying
(Australia, China, Japan, Miami).

The repo already has a finished-looking [README.md](../../../README.md) that
commits to a specific scope, method, and structure. Most surrounding scaffolding
(loaders, partial segment math, FastF1 cache for the 4 races) is in place. The
main notebook, plotting, benchmark glue, tests, and figures do not exist yet.
This spec defines exactly what gets built to ship that v1.

**Audience for the finished work:** technical recruiters and engineers visiting
the portfolio. Non-F1 readers must be able to follow the README and notebook.

**Non-goals (already in README "What's next", explicitly out of scope here):**
- Race-pace / stint-level comparison
- Multi-year rookie comparison (Russell 2022, Hamilton 2007)
- Comparison to drivers outside Mercedes

## 2. Scope

Ship exactly what the README promises:

- 4 races (2026 AU, China, Japan, Miami), qualifying sessions only
- Two drivers: ANT (Antonelli), RUS (Russell)
- Fastest valid lap per driver per session
- Per-segment time delta (positive = ANT faster)
- Headline finding by segment **category** (slow corner / medium corner / fast
  corner / straight), aggregated across the 4 races
- Trajectory finding: total lap delta by race round
- README backfilled with real numbers, real chart inlined

## 3. Architecture

### Module boundaries

| File | Responsibility | Status |
|------|---------------|--------|
| [src/loaders.py](../../../src/loaders.py) | FastF1 session, lap, telemetry loading | done |
| [src/segments.py](../../../src/segments.py) | Pure segment math: resample, build, compute times, compute deltas | partial — needs `compute_segment_times` and `compute_segment_deltas` |
| [src/benchmarks.py](../../../src/benchmarks.py) | High-level `compare_teammates(...)` returning tidy per-race DataFrame with categories + metadata | empty |
| [src/plotting.py](../../../src/plotting.py) | Two plot helpers: category-delta chart, lap-delta-by-round chart | empty |
| [tests/test_segments.py](../../../tests/test_segments.py) | One end-to-end consistency test | empty |
| [notebooks/01_antonelli_vs_russell.ipynb](../../../notebooks/01_antonelli_vs_russell.ipynb) | The portfolio artifact: loads, plots, narrates | empty |

### Function signatures

The existing `build_segments_from_corners(circuit_info, lap_distance_m, threshold_m=250)`
returns a DataFrame with columns `[Segment, start_m, end_m, kind]`. The new
functions described below add columns to that frame — they do not redefine its
shape.

```python
# src/segments.py — additions
def compute_segment_times(
    telem_resampled: pd.DataFrame,   # output of resample_to_distance_grid
                                     # must contain Distance, Speed
    segments: pd.DataFrame,          # output of build_segments_from_corners
                                     # must contain Segment, start_m, end_m, kind
    step_m: float = DEFAULT_GRID_STEP_M,   # must match the step used to resample
) -> pd.DataFrame:
    """Returns the input `segments` frame with two added columns:
       - `min_speed` (kph): min of telem.Speed where start_m <= Distance < end_m
       - `time_s` (seconds): sum of (step_m / speed_m_per_s) over the same rows
    """

def compute_segment_deltas(
    times_a: pd.DataFrame,   # output of compute_segment_times for driver A
    times_b: pd.DataFrame,   # output of compute_segment_times for driver B
                             # both must have the same Segment values, same order
) -> pd.DataFrame:
    """Returns DataFrame with columns:
       [Segment, kind, start_m, end_m, min_speed, time_a_s, time_b_s, delta_s]
       where:
       - min_speed = min(times_a.min_speed, times_b.min_speed) per segment
         (the deeper of the two drivers' minimums — used for category classification)
       - time_a_s = times_a.time_s, time_b_s = times_b.time_s
       - delta_s = time_b_s - time_a_s (positive = driver A faster)
    """
```

```python
# src/benchmarks.py
def compare_teammates(
    year: int,
    round_or_name,           # int (round number) or str (event name)
    drv_a: str = "ANT",
    drv_b: str = "RUS",
    threshold_m: float = 250.0,
) -> dict:
    """Pipeline:
       1. loaders.load_qualifying_session(year, round_or_name)
       2. For each driver: loaders.get_fastest_valid_lap, get_lap_telemetry
       3. segments.resample_to_distance_grid for each
       4. segments.build_segments_from_corners (shared segments from circuit_info)
       5. segments.compute_segment_times for each
       6. segments.compute_segment_deltas
       7. Add `category` column (see §4) based on min_speed + kind
       8. Derive q_session_* per driver (see §4 "Q-session derivation")

    Returns:
        {
          "segments": pd.DataFrame,    # output of compute_segment_deltas
                                       # plus a `category` column (str)
          "meta": {
              "year": int, "round": int, "event_name": str,
              "lap_time_a_s": float, "lap_time_b_s": float, "lap_delta_s": float,
              "q_session_a": Optional[int],   # None if derivation fails
              "q_session_b": Optional[int],
              "q_mismatch": bool,             # False if either is None
          },
        }

    delta_s sign convention: positive = drv_a faster.
    """
```

```python
# src/plotting.py
def plot_category_deltas(
    all_races_df: pd.DataFrame,   # concatenated segments across all 4 races
                                  #   with extra column: event_name
    save_path: Optional[Path] = None,
) -> matplotlib.figure.Figure: ...

def plot_lap_delta_by_round(
    meta_df: pd.DataFrame,        # rows of meta dicts from compare_teammates
    save_path: Optional[Path] = None,
) -> matplotlib.figure.Figure: ...
```

### Design rationale

- `segments.py` stays a pure-math module. No category names, no plotting, no
  FastF1 imports beyond what it already uses. Easier to test in isolation.
- The interpretive layer (mapping `min_speed + kind` → category names) lives
  in `benchmarks.py` so the math stays decoupled from labels.
- `compare_teammates` returns a structured dict with both the per-segment frame
  and metadata. The notebook concatenates the per-segment frames across races
  for the headline chart and stacks the metadata into a separate frame for the
  trajectory chart.
- Plotting takes pre-shaped DataFrames; no FastF1 or filesystem awareness.

## 4. Methodology

### Definition of "valid" lap

Reuse `loaders.get_fastest_valid_lap`, which uses FastF1's
`pick_quicklaps().pick_fastest()`. This filters to laps within 107% of the
fastest and is the heuristic the scratch notebook validated against. We do
not further filter for deleted laps; if track-limits enforcement removes a
lap from the timing sheet, FastF1's `pick_quicklaps` will not include it.

### Segment categories

Each segment is classified into one of 4 categories from `kind` + `min_speed`.
The `min_speed` used here is the one in the `compute_segment_deltas` output:
the deeper of the two drivers' min speeds in that segment.

| Category | Rule |
|----------|------|
| `slow_corner` | `kind == "corner"` AND `min_speed < 130` (kph) |
| `medium_corner` | `kind == "corner"` AND `130 ≤ min_speed < 200` |
| `fast_corner` | `kind == "corner"` AND `min_speed ≥ 200` |
| `straight` | `kind == "straight"` (min_speed irrelevant) |

Thresholds are fixed (not per-circuit quantiles). Rationale: a 100 kph corner is
a 100 kph corner everywhere; comparison across circuits is the whole point. The
notebook prints per-circuit category counts as a sanity check the first time
it runs — if any circuit has zero `fast_corner`s or all `slow_corner`s, that
flags miscalibration.

### Time-delta math

- Telemetry is resampled to a uniform 5m distance grid by
  `resample_to_distance_grid`. The resampled frame includes `Time` (in seconds,
  converted from the source Timedelta) interpolated onto the same grid.
- Segment time = `Time[last grid step in segment] − Time[first grid step in segment]`.
  This uses FastF1's reported sample times directly, rather than reconstructing
  time by integrating speed over distance.
- **Sign convention:** `delta_s = time_b - time_a`, so positive = driver A faster.
  Documented in a docstring on `compute_segment_deltas` and a comment in
  `compare_teammates`.

**Why not speed-based Riemann integration?** The original design integrated
`step_m / speed_m_per_s` per step. This produced residuals up to 0.3s on
circuits where the two drivers' telemetry distances differed substantially
(e.g., Japan 2026 had a 400m spread between ANT and RUS due to different
in-lap behavior). Using `Time` directly bypasses that error entirely:
verified residuals across all 4 cached 2026 races are ≤ 0.1s.

**Precision note for the sanity check:** the §6 test asserts
`|sum(segment_deltas) - (lap_time_b - lap_time_a)| < 0.1`. With the
Time-channel method, this holds across all 4 cached 2026 races.

### Q-session derivation

FastF1 does not directly tag each lap with Q1/Q2/Q3. We derive it as follows
for each driver's fastest valid lap:

1. Get the `LapStartTime` of the fastest lap (FastF1 lap attribute, timedelta
   from session start).
2. Get session Q-segment boundaries. Preferred source: `session.session_status`
   (DataFrame of status changes with `Time` and `Status`); transitions between
   Q1/Q2/Q3 sessions are visible there. Fallback: cluster lap start times
   across all drivers and split on the largest gaps (Q-session breaks).
3. Bucket the fastest lap's start time into the matching Q-segment (1, 2, or 3).

If derivation fails for any reason (status DataFrame missing the expected
transitions, etc.), set `q_session_*` to `None` and `q_mismatch` to `False`,
and the notebook prints a one-line warning that Q-session timing could not be
determined for that race. The analysis still proceeds; the Q-mismatch flag
just isn't available for that race.

### Q-session timing handling in the notebook

`compare_teammates` records which Q-session each driver's fastest lap came from
and sets `q_mismatch = True` when they differ and both are non-None. The
notebook renders a visible warning beside any race where this is true; the
race still contributes to the aggregate but the reader is informed.

### Aggregation across races (headline chart)

For each segment-category, average the per-segment `delta_s` across the 4 races
with equal weighting. The headline chart shows:
- x-axis: 4 categories
- y-axis: time delta (seconds), positive = ANT faster
- a horizontal bar at the mean per category
- a small dot per race overlaid at the category x-position
- a clearly drawn `y=0` reference line

This makes per-race variation visible rather than hidden under an average.

### Trajectory chart

- x-axis: race round number (1, 2, 3, 4) with event name labels
- y-axis: total lap time delta in seconds
- One line, 4 points

## 5. Notebook structure ([notebooks/01_antonelli_vs_russell.ipynb](../../../notebooks/01_antonelli_vs_russell.ipynb))

Section-by-section:

1. **Setup & imports** — short
2. **The question** — 2-3 sentence framing (why teammate, why segment-level)
3. **Method, briefly** — points to README for full method
4. **Load all 4 races** — loop calling `compare_teammates(2026, r)` for each
   race. Print a summary table: race, ANT lap time, RUS lap time, lap delta,
   Q-mismatch flag
5. **Sanity check** — print per-circuit category counts, and per-race
   `sum(segment_deltas) vs actual lap_time_delta` for the reader to see
6. **Headline finding — where does the time go?** — category-delta chart +
   2-3 sentences of interpretation
7. **Trajectory — is the gap closing?** — line chart + a sentence
8. **Per-race detail** *(collapsible appendix)* — one small per-segment bar
   chart per race, for curious readers
9. **Caveats** — restate README limitations, especially calling out any race
   with `q_mismatch == True`
10. **Conclusion** — what we learned, what's next

Charts saved to `figures/headline_segment_delta.png` and
`figures/lap_delta_by_round.png`.

## 6. Testing strategy

**One test only.** [tests/test_segments.py](../../../tests/test_segments.py):

```python
def test_segment_deltas_sum_matches_lap_delta():
    # Uses Miami 2026 Q from the FastF1 cache (already populated)
    # Calls benchmarks.compare_teammates(2026, "Miami") — the public API,
    #   so this is a contract test on the whole pipeline, not just segments
    # Asserts abs(sum(result.segments.delta_s) - result.meta.lap_delta_s) < 0.1
```

**Cache path:** `loaders.DEFAULT_CACHE_DIR = "../fastf1_cache"` is
notebook-relative. The test runs from repo root, so it must call
`loaders.setup_cache()` with an explicit path resolved from `__file__`
(e.g., `Path(__file__).parent.parent / "fastf1_cache"`).

**Cache missing:** if `fastf1_cache/2026/...Miami...` is absent, the test
skips with a clear message:
`pytest.skip("FastF1 cache not populated for Miami 2026 — run notebook 00 to populate")`.

No unit-level mocking, no parametrized matrix. One real-data end-to-end check
on the public API is the right amount for a 4-race portfolio analysis. Adding
more would be testing theater.

## 7. Deliverables & cleanup

### Deliverables

- [notebooks/01_antonelli_vs_russell.ipynb](../../../notebooks/01_antonelli_vs_russell.ipynb): runs top-to-bottom on a populated cache
- `figures/headline_segment_delta.png`: inlined in README
- `figures/lap_delta_by_round.png`: in notebook (optional in README)
- [README.md](../../../README.md): all `{TBD}` replaced with real numbers/findings;
  `{race list}` = "Australia, China, Japan, Miami"; `{N}` = 4; `{version}` =
  current FastF1; `{X}MB` = actual cache size on disk
- `src/segments.py`, `src/benchmarks.py`, `src/plotting.py`: populated per §3
- `tests/test_segments.py`: passes against the cached Miami session

### File state (existing vs to-create)

| Path | State |
|------|-------|
| `figures/` | exists (empty) — write PNGs into it |
| `tests/` | exists |
| `tests/test_segments.py` | exists (empty) — populate |
| `src/benchmarks.py` | exists (empty) — populate |
| `src/plotting.py` | exists (empty) — populate |
| `notebooks/01_antonelli_vs_russell.ipynb` | exists (empty) — populate |
| `notebooks/00_scratch_fastf1.ipynb` | exists — leave as-is (exploration record) |

### Cleanup

- Delete `ant_vs_all.ipynb` from project root (user-confirmed)
- Fix [requirements.txt](../../../requirements.txt): remove trailing comma,
  add `pandas`, `numpy`, `matplotlib`, `seaborn`, `jupyterlab`, `pytest`.
  **Sequencing with §8 fastf1-version risk:** first confirm the installed
  `fastf1` version actually works against 2026 data (run a smoke load of all
  4 races); only after that confirmation, pin versions in `requirements.txt`.
  If the installed version is broken on 2026, bump first, then pin.
- Populate [.gitignore](../../../.gitignore) with `fastf1_cache/`,
  `__pycache__/`, `.ipynb_checkpoints/`, `.DS_Store`
- Add a one-line "verify install" step to README Reproducing section:
  `pytest tests/`

## 8. Risks & open questions

- **`build_segments_from_corners` output unverified on all 4 circuits.** The
  scratch notebook only ran it on Miami. If a circuit produces degenerate
  segments (zero straights, or one huge segment), the sanity-check print in the
  notebook will surface it and we'll need a follow-up fix to the grouping
  threshold or the corner-list source.
- **FastF1 version pin.** `requirements.txt` currently says `fastf1==3.8.1,`.
  Need to confirm the installed version actually works against 2026 data
  (FastF1 occasionally requires version bumps for new seasons) before pinning
  in the final requirements file. This is resolved by the §7 smoke-load step
  (loading all 4 races end-to-end); not an independent open question.
- **Speed-band thresholds are judgment calls.** 130 / 200 kph splits are
  F1-conventional but not derived. If sanity-check counts come out lopsided
  on the real data, thresholds may need a one-time adjustment before the
  README writeup is finalized.

## 9. Out of scope (deferred to "What's next")

- Race-pace / stint-level comparison
- Historical rookie comparison (Russell 2022, Hamilton 2007 — note: 2023 cache
  exists but is unused in v1)
- Splitting corners into braking / apex / exit phases
- Setup-difference attribution
- Any non-Mercedes drivers
