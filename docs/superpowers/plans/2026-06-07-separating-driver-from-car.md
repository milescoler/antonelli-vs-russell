# Separating the Driver from the Car — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the f1_project portfolio piece under one thesis — *"Separating the driver from the car: how good is Antonelli, really?"* — by (1) extending the qualifying chapter through Monaco (R6), (2) building the already-planned race-winning chapter through Monaco, (3) adding a new cross-year per-track overperformance chapter that controls for the car across seasons, and (4) making the whole pipeline refreshable after each race from a single `RACES` source.

**Architecture:** A single `src/season.py` holds the `RACES` list + default `years` window, imported by all notebooks and the refresh script. Chapter 2 reuses the existing `src/race.py` plan verbatim (two small deltas). A new isolated `src/track_history.py` computes overperformance-vs-season-baseline from results-only loads. Three new plotting functions, a new notebook `03`, a `scripts/refresh.py` orchestrator, and a reframed README tie it together. Pure functions return tidy DataFrames; plotting stays FastF1-free.

**Tech Stack:** Python 3.12, FastF1 3.8.x, pandas, numpy, matplotlib, pytest, Jupyter/nbconvert.

**Spec:** [docs/superpowers/specs/2026-06-07-separating-driver-from-car-design.md](../specs/2026-06-07-separating-driver-from-car-design.md)

---

## Conventions used throughout

- **Sign convention:** **positive = better.** Qualifying delta `RUS − ANT` (positive = ANT faster); race metrics positive = ANT better; track overperformance `baseline − track` (positive = better than season norm, since lower position number is better).
- **`RACES` master list:** `['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco']` — lives in `src/season.py`, imported everywhere. Adding a future race = one edit here.
- **Historical window:** `YEARS = list(range(2010, 2026))` — also in `src/season.py`.
- **Classified driver-year** (Ch3): `Status == "Finished"` or `Status` starts with `"+"` (lapped). Everything else (Accident, Engine, Retired, Disqualified, DNS, …) is a DNF and excluded from finish-based metrics.
- **Cache:** Canada 2026 + earlier 2026 races and 2023/2025 are cached. Monaco 2026 and the deep historical window download on first run (results-only, fast per session, but many sessions — the first Ch3 run is slow).
- **Don't trust numbers written in this plan** for prose: every figure carried into a notebook/README is recomputed live during implementation (see Chunk 6 Step 0).
- **Live-number rule:** any place this plan quotes a metric (e.g. a 6-race mean), treat it as a placeholder; the recomputed value wins.

---

## File structure

| File | Responsibility | Action |
|------|----------------|--------|
| `src/season.py` | Single source of truth: `RACES`, `YEARS` | Create |
| `src/race.py` | All race-session logic (Ch2) | Create — per 2026-05-29 plan |
| `tests/test_race.py` | Race invariants + Canada & Monaco anchors | Create — per 2026-05-29 plan + Monaco |
| `src/track_history.py` | Cross-year per-track overperformance (Ch3) | Create |
| `tests/test_track_history.py` | Overperformance invariants, DNF exclusion, small-n | Create |
| `src/plotting.py` | + 4 race plots (Ch2) + 3 track-history plots (Ch3) | Modify |
| `notebooks/02_how_antonelli_wins_races.ipynb` | Ch2 narrative + charts | Create — per 2026-05-29 plan |
| `notebooks/03_driver_vs_car_track_history.ipynb` | Ch3 narrative + charts | Create |
| `notebooks/01_antonelli_vs_russell.ipynb` | Extend to Monaco via `season.py`; fix prose | Modify |
| `scripts/refresh.py` | One-command season refresh | Create |
| `README.md` | Reframe around the single thesis; refresh section | Modify |
| `case_study.pdf` | Regenerate to new framing | Regen |

---

## Chunk 1: `src/season.py` — single source of truth

### Task 1: Create the shared season constants

**Files:**
- Create: `src/season.py`
- Test: `tests/test_season.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_season.py
"""The single source of truth for which races and which historical years drive
the whole project. Kept trivially simple on purpose — this is the one file you
edit when a new race happens."""
from src import season


def test_races_through_monaco_in_order():
    assert season.RACES == ['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco']


def test_years_window_is_2010_through_2025():
    assert season.YEARS[0] == 2010
    assert season.YEARS[-1] == 2025
    assert len(season.YEARS) == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_season.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.season'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/season.py
"""Single source of truth for the project's race list and historical window.

To bring the project current after a new Grand Prix:
  1. Append the new race name to RACES (must match the FastF1 event name well
     enough for fastf1.get_session(year, name, ...) to resolve it).
  2. Run `python scripts/refresh.py`.
  3. Commit the regenerated figures, notebooks, and PDFs.

Both notebooks and scripts/refresh.py import RACES/YEARS from here, so this is
the ONLY place to edit per new race."""

# 2026 season, in calendar order, through the most recent completed round.
RACES = ['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco']

# Historical window for the cross-year track-history chapter (inclusive).
YEARS = list(range(2010, 2026))  # 2010..2025
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_season.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/season.py tests/test_season.py
git commit -m "feat: add src/season.py single source of truth for RACES/YEARS"
```

---

## Chunk 2: Chapter 2 — race-winning analysis (reuse the 2026-05-29 plan)

Chapter 2's `src/race.py`, its four plotting functions, `tests/test_race.py`, and
`notebooks/02_how_antonelli_wins_races.ipynb` are **already fully specified, task by task
(TDD, with code)**, in:

> [docs/superpowers/plans/2026-05-29-how-antonelli-wins-races.md](2026-05-29-how-antonelli-wins-races.md) — **Chunks 1, 2, 3, and 5.**

Execute those chunks **verbatim**, with exactly these modifications. Do **not** re-derive
the code here; that plan is correct.

### Task 2: Build `src/race.py` + plots + tests + notebook 02 from the 2026-05-29 plan

**Files:** (as listed in the 2026-05-29 plan)
- Create: `src/race.py`, `tests/test_race.py`, `notebooks/02_how_antonelli_wins_races.ipynb`
- Modify: `src/plotting.py` (4 race plots)

- [ ] **Step 1:** Execute 2026-05-29 plan **Chunk 1** (Tasks 1–2: `load_race_session`, `get_clean_laps`) exactly as written.

- [ ] **Step 2:** Execute 2026-05-29 plan **Chunk 2** (Tasks 3–6: `_pn_finisher`/`start_summary`, `stint_pace`, `tire_deg`, `gap_to_rival`) exactly as written.

- [ ] **Step 3: Add the Monaco regression anchor** to `tests/test_race.py` (new test alongside the existing Canada anchor):

```python
def test_start_summary_monaco_anchor():
    # Monaco is the cleanest "pure win" case: pole to victory, no inheritance.
    df = race.start_summary(2026, "Monaco")
    ant = df[df["driver"] == "ANT"].iloc[0]
    assert int(ant["grid"]) == 1
    assert int(ant["lap1_pos"]) == 1
    assert int(ant["finish"]) == 1
    # Field reference (per-race P2 finisher) is present and is HAM at Monaco.
    p2 = df[df["driver"] == "P2"].iloc[0]
    assert p2["code"] == "HAM"
```

Add a Monaco-dir guard to the cache fixture in `tests/test_race.py` so the module skips cleanly if Monaco isn't cached yet:

```python
MONACO_DIR = CACHE_DIR / "2026" / "2026-06-07_Monaco_Grand_Prix"
# in the fixture, skip if not (CANADA_DIR.exists() and MONACO_DIR.exists())
```

Run: `python -m pytest tests/test_race.py -v`
Expected: all race tests PASS (including both Canada and Monaco anchors). If Monaco isn't cached, the module skips — run `scripts/refresh.py`'s fetch step first, or fetch Monaco R manually, then re-run.

- [ ] **Step 4:** Execute 2026-05-29 plan **Chunk 3** (Tasks 7–10: the four `plot_*` race functions) exactly as written.

- [ ] **Step 5:** Execute 2026-05-29 plan **Chunk 5** (Task 12: build `notebooks/02_how_antonelli_wins_races.ipynb`) **with one change**: the notebook header imports the race list from the new single source instead of hard-coding it:

```python
import sys; sys.path.insert(0, '..')
import pandas as pd
import matplotlib.pyplot as plt
from src.loaders import setup_cache
from src import race
from src.season import RACES                      # <-- single source of truth
from src.plotting import (plot_start_conversion, plot_stint_pace,
                          plot_gap_trace, plot_tire_deg)
setup_cache('../fastf1_cache')
# RACES now includes Monaco (R6); Monaco is the pure pole-to-win centerpiece.
```

Everything else in that task (results table, the three chapters, honest-accounting + closing markdown, execution, PDF export, commit) is unchanged — but the narrative now spans **6** races through Monaco, and Monaco (pole → flag-to-flag win) becomes the cleanest "no inheritance" counterpart to Canada's inherited win. Update the chapter prose to name Monaco explicitly.

- [ ] **Step 6: Commit** (the 2026-05-29 plan's per-task commits cover most of this; this is the final Ch2 commit)

```bash
git add src/race.py tests/test_race.py src/plotting.py notebooks/02_how_antonelli_wins_races*.* figures/
git commit -m "feat: build race-winning chapter (Ch2) through Monaco"
```

> **Note:** the 2026-05-29 plan's Chunk 4 (notebook 01) and Chunk 6 (README/case study) are **superseded** by Chunks 6 and 8 of THIS plan, which carry the unified three-chapter framing and the 6-race numbers. Do not run the old Chunk 4/6.

---

## Chunk 3: `src/track_history.py` — cross-year overperformance (Ch3)

The new chapter's engine. Results-only loads; overperformance = a driver's (or team's)
result at a track vs their **own season baseline computed over the other rounds**, so car
quality divides out. `metric` ∈ {`'finish'`, `'grid'`}; finish excludes DNFs, grid is the
DNF-free cross-check.

### Task 3: `_is_classified` + `load_results` (single-race results loader)

**Files:**
- Create: `src/track_history.py`
- Test: `tests/test_track_history.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_track_history.py
"""Cross-year track-history tests. Invariants on real cached/loadable results
(no brittle magic numbers except deliberate definitional checks). Skips if the
historical cache can't be reached.

NOTE: this analysis runs on the project's synthetic '2026-world' data source;
assertions check the METRIC DEFINITIONS, not real-world F1 history."""
import math
import pytest
import pandas as pd

from src.loaders import setup_cache
from src import track_history as th

CACHE = "fastf1_cache"


@pytest.fixture(scope="module", autouse=True)
def _cache():
    setup_cache(CACHE)


def test_load_results_columns_and_classification():
    try:
        df = th.load_results(2024, "Monaco")
    except Exception as e:
        pytest.skip(f"Historical results unavailable: {e!r}")
    for col in ["year", "round", "track", "driver", "team", "grid",
                "finish", "status", "classified"]:
        assert col in df.columns
    assert df["classified"].dtype == bool
    # A finisher (P1) must be classified.
    p1 = df[df["finish"] == 1].iloc[0]
    assert bool(p1["classified"]) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_track_history.py::test_load_results_columns_and_classification -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.track_history'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/track_history.py
"""Cross-year, per-track overperformance — the project's car-control layer
ACROSS seasons (the teammate comparison controls for the car WITHIN a season).

Core idea: a great car flatters a driver everywhere, so a driver's result at one
track is only informative RELATIVE TO their own season baseline. We compute, per
driver-year, (season baseline over the OTHER rounds) - (result at this track);
positive = better than their usual that year. Averaging across years gives a
driver's track affinity with car quality largely divided out. The same arithmetic
on teams reveals track-specific CAR strengths.

metric='finish' excludes DNF rounds (a retirement's classified position is not
pace); metric='grid' is the DNF-free qualifying cross-check.

Data note: runs on the project's synthetic '2026-world' source; results are
internally consistent but not real F1 history. Keep claims data-driven.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import fastf1

from src.loaders import setup_cache  # noqa: F401  (re-exported for convenience)

MIN_TRACK_YEARS = 3  # below this, a driver/team's affinity is flagged small-n


def _is_classified(status) -> bool:
    """Running at the flag: 'Finished' or lapped ('+1 Lap', '+2 Laps', ...).
    Everything else (Accident, Engine, Retired, Disqualified, DNS) is a DNF."""
    s = str(status)
    return s == "Finished" or s.startswith("+")


def load_results(year: int, track: str) -> pd.DataFrame:
    """Results-only load of one Race (R) session as tidy rows. No telemetry/laps
    (fast). `track` is matched by FastF1's partial event-name resolution."""
    session = fastf1.get_session(year, track, "R")
    session.load(telemetry=False, weather=False, messages=False, laps=False)
    res = session.results
    return pd.DataFrame({
        "year": year,
        "round": int(session.event["RoundNumber"]),
        "track": track,
        "driver": res["Abbreviation"].astype(str).values,
        "team": res["TeamName"].astype(str).values,
        "grid": pd.to_numeric(res["GridPosition"], errors="coerce").values,
        "finish": pd.to_numeric(res["Position"], errors="coerce").values,
        "status": res["Status"].astype(str).values,
        "classified": [_is_classified(s) for s in res["Status"]],
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_track_history.py::test_load_results_columns_and_classification -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/track_history.py tests/test_track_history.py
git commit -m "feat: add track_history.load_results + classification"
```

### Task 4: `season_table` (all rounds of a season)

**Files:**
- Modify: `src/track_history.py`
- Test: `tests/test_track_history.py`

- [ ] **Step 1: Write the failing test**

```python
def test_season_table_spans_multiple_rounds():
    try:
        st = th.season_table(2024)
    except Exception as e:
        pytest.skip(f"Historical schedule/results unavailable: {e!r}")
    assert st["round"].nunique() > 5          # a full season has many rounds
    assert set(["year", "round", "driver", "team", "grid", "finish",
                "classified"]).issubset(st.columns)
    # Each (round, driver) appears at most once.
    assert not st.duplicated(subset=["round", "driver"]).any()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_track_history.py::test_season_table_spans_multiple_rounds -v`
Expected: FAIL — `season_table` not defined.

- [ ] **Step 3: Write minimal implementation** (append to `src/track_history.py`)

```python
def season_table(year: int) -> pd.DataFrame:
    """Every completed round of a season as tidy rows — the basis for season
    baselines. Results-only loads; rounds that fail to load are skipped (a
    schedule entry may have no results in this data source)."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    frames = []
    for _, ev in schedule.iterrows():
        rnd = int(ev["RoundNumber"])
        try:
            session = fastf1.get_session(year, rnd, "R")
            session.load(telemetry=False, weather=False, messages=False, laps=False)
        except Exception:
            continue
        if session.results is None or len(session.results) == 0:
            continue
        res = session.results
        frames.append(pd.DataFrame({
            "year": year,
            "round": rnd,
            "track": str(ev["EventName"]),
            "driver": res["Abbreviation"].astype(str).values,
            "team": res["TeamName"].astype(str).values,
            "grid": pd.to_numeric(res["GridPosition"], errors="coerce").values,
            "finish": pd.to_numeric(res["Position"], errors="coerce").values,
            "status": res["Status"].astype(str).values,
            "classified": [_is_classified(s) for s in res["Status"]],
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_track_history.py::test_season_table_spans_multiple_rounds -v`
Expected: PASS. (First run downloads a full season results-only — may take a minute.)

- [ ] **Step 5: Commit**

```bash
git add src/track_history.py tests/test_track_history.py
git commit -m "feat: add track_history.season_table"
```

### Task 5: `driver_track_affinity` (the core overperformance metric)

**Files:**
- Modify: `src/track_history.py`
- Test: `tests/test_track_history.py`

- [ ] **Step 1: Write the failing tests** (definition invariants — the heart of Ch3)

```python
def _toy_season(year, track_round=2):
    """Hand-built season table to test the metric arithmetic exactly.
    DRV1: finishes 2 at the track, [4,6] elsewhere -> baseline 5, delta +3.
    DRV2: DNF at the track (excluded), finishes elsewhere -> no delta.
    DRV3: only ran the track round -> no baseline -> dropped."""
    rows = [
        # driver, round, finish, classified
        ("DRV1", track_round, 2, True),
        ("DRV1", 1, 4, True),
        ("DRV1", 3, 6, True),
        ("DRV2", track_round, 18, False),   # DNF at track
        ("DRV2", 1, 5, True),
        ("DRV3", track_round, 1, True),      # only appears at the track
    ]
    return pd.DataFrame([
        {"year": year, "round": r, "track": "TrackX" if r == track_round else f"R{r}",
         "driver": d, "team": d + "team", "grid": f, "finish": f,
         "status": "Finished" if c else "Accident", "classified": c}
        for d, r, f, c in rows
    ])


def test_driver_affinity_arithmetic_and_dnf_and_baseline(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.driver_track_affinity("TrackX", [2099], metric="finish")
    by = df.set_index("driver")
    # DRV1: baseline mean(4,6)=5, track=2 -> affinity +3.
    assert math.isclose(by.loc["DRV1", "affinity"], 3.0)
    assert int(by.loc["DRV1", "n_years"]) == 1
    # DRV2 (DNF at track) and DRV3 (no baseline) must NOT appear.
    assert "DRV2" not in by.index
    assert "DRV3" not in by.index


def test_driver_affinity_small_n_flag(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.driver_track_affinity("TrackX", [2099], metric="finish")
    assert bool(df.set_index("driver").loc["DRV1", "small_n"]) is True  # 1 < 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_track_history.py -k driver_affinity -v`
Expected: FAIL — `driver_track_affinity` not defined.

- [ ] **Step 3: Write minimal implementation** (append to `src/track_history.py`)

```python
def _affinity_rows(track: str, years, metric: str, group_col: str):
    """Shared engine for driver_/team_ affinity. For each year, find the track's
    round, then for each group (driver or team) compute:
        track value  = group's metric at the track round
                       (finish: classified only; grid: grid>=1)
        baseline     = group's mean metric over the OTHER rounds
                       (finish: classified only; grid: grid>=1)
        delta        = baseline - track value   (positive = better than usual)
    Groups with no usable baseline that year contribute no row."""
    is_finish = metric == "finish"
    col = "finish" if is_finish else "grid"
    rows = []
    for y in years:
        st = season_table(y)
        if st.empty:
            continue
        trk = st[st["track"].str.contains(track, case=False, na=False)]
        if trk.empty:
            continue
        trk_round = int(trk["round"].iloc[0])

        def _usable(frame):
            if is_finish:
                return frame[frame["classified"] & frame[col].notna()]
            return frame[(frame["grid"] >= 1) & frame[col].notna()]

        for key, g in st.groupby(group_col):
            here = _usable(g[g["round"] == trk_round])
            if here.empty:
                continue
            track_val = float(here[col].mean())  # mean handles team's two cars
            others = _usable(g[g["round"] != trk_round])
            if others.empty:
                continue  # no baseline -> drop (spec edge case)
            baseline = float(others[col].mean())
            rows.append({group_col: key, "year": y,
                         "track_val": track_val, "baseline": baseline,
                         "delta": baseline - track_val})
    return pd.DataFrame(rows)


def _aggregate(rows: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if rows.empty:
        return rows
    agg = (rows.groupby(group_col)
                .agg(affinity=("delta", "mean"),
                     n_years=("delta", "size"),
                     mean_track=("track_val", "mean"))
                .reset_index())
    agg["small_n"] = agg["n_years"] < MIN_TRACK_YEARS
    return agg.sort_values("affinity", ascending=False).reset_index(drop=True)


def driver_track_affinity(track: str, years, metric: str = "finish") -> pd.DataFrame:
    """Per driver: mean overperformance vs own-season baseline at `track` across
    `years`, with n_years and a small_n flag (n_years < MIN_TRACK_YEARS).
    metric in {'finish','grid'}. Sorted best (most positive) first."""
    return _aggregate(_affinity_rows(track, years, metric, "driver"), "driver")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_track_history.py -k driver_affinity -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/track_history.py tests/test_track_history.py
git commit -m "feat: add driver_track_affinity overperformance metric"
```

### Task 6: `team_track_affinity` + `track_leaderboard`

**Files:**
- Modify: `src/track_history.py`
- Test: `tests/test_track_history.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_team_affinity_uses_shared_engine(monkeypatch):
    monkeypatch.setattr(th, "season_table", lambda y: _toy_season(y))
    df = th.team_track_affinity("TrackX", [2099], metric="finish")
    # Each toy driver is its own team; DRV1team mirrors DRV1's +3.
    assert math.isclose(df.set_index("team").loc["DRV1team", "affinity"], 3.0)


def test_track_leaderboard_columns_and_sort():
    try:
        lb = th.track_leaderboard("Monaco", [2022, 2023, 2024])
    except Exception as e:
        pytest.skip(f"Historical results unavailable: {e!r}")
    for col in ["driver", "n_starts", "wins", "podiums", "mean_finish", "mean_grid"]:
        assert col in lb.columns
    # Wins are non-negative ints and the board is sorted wins-desc.
    assert (lb["wins"] >= 0).all()
    assert lb["wins"].is_monotonic_decreasing
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_track_history.py -k "team_affinity or leaderboard" -v`
Expected: FAIL — functions not defined.

- [ ] **Step 3: Write minimal implementation** (append to `src/track_history.py`)

```python
def team_track_affinity(track: str, years, metric: str = "finish") -> pd.DataFrame:
    """As driver_track_affinity, aggregated by team — track-specific CAR
    strength. A team's per-round value is the mean over its (classified) cars."""
    return _aggregate(_affinity_rows(track, years, metric, "team"), "team")


def track_leaderboard(track: str, years) -> pd.DataFrame:
    """Raw 'who owns this track' board over the window: wins, podiums, mean
    finish, mean grid, starts per driver. NOT car-controlled — the accessible
    hook before the overperformance metric. Sorted wins, then podiums, then
    mean finish."""
    frames = []
    for y in years:
        try:
            frames.append(load_results(y, track))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    allr = pd.concat(frames, ignore_index=True)
    cls = allr[allr["classified"]]
    out = pd.DataFrame({"n_starts": allr.groupby("driver").size()})
    out["wins"] = cls[cls["finish"] == 1].groupby("driver").size()
    out["podiums"] = cls[cls["finish"] <= 3].groupby("driver").size()
    out["mean_finish"] = cls.groupby("driver")["finish"].mean()
    out["mean_grid"] = allr[allr["grid"] >= 1].groupby("driver")["grid"].mean()
    out = out.fillna({"wins": 0, "podiums": 0}).reset_index()
    out["wins"] = out["wins"].astype(int)
    out["podiums"] = out["podiums"].astype(int)
    return out.sort_values(["wins", "podiums", "mean_finish"],
                           ascending=[False, False, True]).reset_index(drop=True)
```

- [ ] **Step 4: Run the full module to verify it passes**

Run: `python -m pytest tests/test_track_history.py -v`
Expected: all track-history tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/track_history.py tests/test_track_history.py
git commit -m "feat: add team_track_affinity + track_leaderboard"
```

---

## Chunk 4: Chapter 3 plots

All follow the existing `src/plotting.py` contract: take a tidy df, optional `save_path`,
return `fig`; no FastF1 imports; 150 dpi; `bbox_inches='tight'`; hidden top/right spines;
`fig.tight_layout()`. Reuse the existing save block. Exercised by being called on real
data and eyeballed, not pixel-tested.

### Task 7: `plot_track_affinity`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — horizontal bar leaderboard of overperformance (`affinity`); positive (better-than-baseline) to the right; small-n entries de-emphasized; an optional `highlight` code (e.g. `"ANT"`) drawn in the project accent color.

```python
def plot_track_affinity(affinity_df: pd.DataFrame, group_col: str = "driver",
                        title: str = "", highlight: Optional[str] = None,
                        top_n: int = 12, save_path: Optional[Path] = None) -> plt.Figure:
    """Horizontal bars of overperformance vs season baseline at one track.
    Positive = finishes/qualifies better here than their season norm (car divided
    out). Small-n rows (small_n==True) are drawn lighter. `highlight` (a value in
    group_col) is accented. Shows the top_n by affinity.

    Required columns: <group_col>, affinity, n_years, small_n."""
    df = affinity_df.head(top_n).iloc[::-1]  # best at top
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(df))))
    for _, row in df.iterrows():
        base = "#1f77b4" if not row["small_n"] else "#b8cfe5"
        color = "#d62728" if (highlight is not None and row[group_col] == highlight) else base
        ax.barh(row[group_col], row["affinity"], color=color)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Overperformance vs season baseline (positions; + = better here)")
    ax.set_title(title or f"Who overperforms at this track ({group_col})")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
```

- [ ] **Step 2: Smoke-check**

```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import track_history as th
from src.plotting import plot_track_affinity
from src.season import YEARS
setup_cache('fastf1_cache')
df = th.driver_track_affinity('Monaco', YEARS, metric='finish')
plot_track_affinity(df, 'driver', 'Monaco: driver overperformance', highlight='ANT',
                    save_path='figures/track_affinity_monaco.png'); print('OK', len(df))
" 2>&1 | tail -2
```
Expected: prints `OK <n>`; `figures/track_affinity_monaco.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/track_affinity_monaco.png
git commit -m "feat: add plot_track_affinity chart"
```

### Task 8: `plot_driver_vs_car_spread`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — side-by-side: top driver affinities vs top team affinities at one track. The visual read: if the team panel has larger, more persistent positive bars than any driver, it's a *car track*; if specific drivers carry positive affinity, it's a *driver track*.

```python
def plot_driver_vs_car_spread(driver_df: pd.DataFrame, team_df: pd.DataFrame,
                              track: str = "", top_n: int = 8,
                              save_path: Optional[Path] = None) -> plt.Figure:
    """Two stacked horizontal-bar panels for one track: top driver overperformance
    (left/top) vs top team overperformance (right/bottom). Lets the reader judge
    whether the track is driver-dependent (drivers carry the signal) or
    car-dependent (teams do). Required columns: driver/team, affinity, small_n."""
    fig, (ax_d, ax_t) = plt.subplots(1, 2, figsize=(12, max(3, 0.5 * top_n)))
    for ax, df, gcol, label in [(ax_d, driver_df, "driver", "Drivers"),
                                (ax_t, team_df, "team", "Teams")]:
        d = df.head(top_n).iloc[::-1]
        colors = ["#1f77b4" if not s else "#b8cfe5" for s in d["small_n"]]
        ax.barh(d[gcol].astype(str), d["affinity"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(label)
        ax.set_xlabel("Overperformance (+ = better than baseline)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(f"{track}: is it a driver track or a car track?", fontsize=12)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
```

- [ ] **Step 2: Smoke-check**

```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import track_history as th
from src.plotting import plot_driver_vs_car_spread
from src.season import YEARS
setup_cache('fastf1_cache')
d = th.driver_track_affinity('Monaco', YEARS); t = th.team_track_affinity('Monaco', YEARS)
plot_driver_vs_car_spread(d, t, 'Monaco', save_path='figures/driver_vs_car_monaco.png'); print('OK')
" 2>&1 | tail -1
```
Expected: prints `OK`; `figures/driver_vs_car_monaco.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/driver_vs_car_monaco.png
git commit -m "feat: add plot_driver_vs_car_spread chart"
```

### Task 9: `plot_track_summary` (the 6-track season summary)

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — one row per 2026 track; show Mercedes' historical team affinity (the car-strength bar) and Antonelli's own overperformance marker, so each of his wins gets "driver track or car track, and is the car historically strong here?" context. Input is a pre-shaped summary df built in the notebook (Chunk 5 Step 4).

```python
def plot_track_summary(summary_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Compact per-2026-track context. For each track: a bar = Mercedes historical
    team overperformance (car strength here), and a marker = Antonelli's own
    overperformance. Reading: Mercedes-strong tracks vs tracks where ANT himself
    carries the result.

    Required columns: track, merc_affinity, ant_overperf (NaN allowed),
    driver_track (bool: is this a driver-dependent track?)."""
    df = summary_df.copy()
    fig, ax = plt.subplots(figsize=(9, max(3, 0.6 * len(df))))
    ypos = range(len(df))
    bar_colors = ["#9b59b6" if dt else "#7f7f7f" for dt in df["driver_track"]]
    ax.barh(list(ypos), df["merc_affinity"], color=bar_colors, alpha=0.7,
            label="Mercedes hist. overperf (car)")
    ax.scatter(df["ant_overperf"], list(ypos), color="#d62728", zorder=3,
               label="Antonelli overperf (driver)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(df["track"])
    ax.set_xlabel("Overperformance vs season baseline (+ = better)")
    ax.set_title("Each 2026 track: car strength vs Antonelli's own edge\n"
                 "(purple bar = driver-dependent track)")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
```

- [ ] **Step 2: Smoke-check** — built from real data in the notebook (Chunk 5). Minimal direct check with a tiny synthetic df:

```bash
python -c "
import sys; sys.path.insert(0,'.'); import pandas as pd
from src.plotting import plot_track_summary
df = pd.DataFrame({'track':['Monaco','Miami'],'merc_affinity':[1.2,-0.3],
                   'ant_overperf':[2.0, float('nan')],'driver_track':[True, False]})
plot_track_summary(df, save_path='figures/track_summary.png'); print('OK')
" 2>&1 | tail -1
```
Expected: prints `OK`; `figures/track_summary.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/track_summary.png
git commit -m "feat: add plot_track_summary chart"
```

---

## Chunk 5: notebook 03 — the track-history chapter

### Task 10: Create `notebooks/03_driver_vs_car_track_history.ipynb`

**Files:**
- Create: `notebooks/03_driver_vs_car_track_history.ipynb`

Follow notebooks 01/02 voice (question → method → finding → caveat). Author cell by cell, then execute.

- [ ] **Step 1: Header + setup**

```python
import sys; sys.path.insert(0, '..')
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.loaders import setup_cache
from src import track_history as th
from src.season import RACES, YEARS
from src.plotting import (plot_track_affinity, plot_driver_vs_car_spread,
                          plot_track_summary)
setup_cache('../fastf1_cache')

# Cache each season table once (a full season is 20+ results-only loads;
# every track/metric call below reuses these frames).
SEASONS = {y: th.season_table(y) for y in YEARS}
```

> Make the affinity calls use the cached `SEASONS` rather than reloading: in the notebook, monkeypatch-free reuse by calling a thin local wrapper, e.g. `th.season_table = lambda y, _c=SEASONS: _c[y]` set once after building `SEASONS`. (Acceptable in a notebook; the module default stays the network version.)

- [ ] **Step 2: Intro markdown** — the chapter's role: chapters 1–2 control for the car *within* a season (same teammate); this controls for it *across* seasons. State the overperformance definition in one plain sentence, the synthetic-data note (claims are "in this dataset"), and that finish excludes DNFs with grid as the DNF-free cross-check.

- [ ] **Step 3: Monaco centerpiece**

```python
# Raw "who owns Monaco" board (accessible hook; NOT car-controlled).
lb = th.track_leaderboard('Monaco', YEARS)
display(lb.head(10))

# Controlled metric: overperformance vs season baseline.
mon_drv = th.driver_track_affinity('Monaco', YEARS, metric='finish')
mon_team = th.team_track_affinity('Monaco', YEARS, metric='finish')
plot_track_affinity(mon_drv, 'driver', 'Monaco: driver overperformance (finish)',
                    highlight='ANT', save_path='../figures/track_affinity_monaco.png'); plt.show()
plot_driver_vs_car_spread(mon_drv, mon_team, 'Monaco',
                          save_path='../figures/driver_vs_car_monaco.png'); plt.show()

# DNF-free cross-check on grid.
mon_drv_grid = th.driver_track_affinity('Monaco', YEARS, metric='grid')
display(mon_drv_grid.head(8))
```
Markdown: read whether Monaco is a driver track or car track; whether finish and grid agree; where Mercedes sits historically; where Antonelli lands (tiny sample — directional).

- [ ] **Step 4: 6-track season summary** — build the `summary_df` for `plot_track_summary`:

```python
MERC = 'Mercedes'
rows = []
for trk in RACES:
    dteam = th.team_track_affinity(trk, YEARS, metric='finish')
    ddrv  = th.driver_track_affinity(trk, YEARS, metric='finish')
    merc = dteam[dteam['team'] == MERC]['affinity']
    ant  = ddrv[ddrv['driver'] == 'ANT']['affinity']
    # Driver-vs-car heuristic: best driver affinity exceeds best team affinity
    # by a margin -> driver-dependent. (Descriptive; caveated in prose.)
    best_drv = ddrv['affinity'].max() if len(ddrv) else np.nan
    best_team = dteam['affinity'].max() if len(dteam) else np.nan
    rows.append({'track': trk,
                 'merc_affinity': float(merc.iloc[0]) if len(merc) else np.nan,
                 'ant_overperf': float(ant.iloc[0]) if len(ant) else np.nan,
                 'driver_track': bool(best_drv > best_team) if np.isfinite(best_drv) and np.isfinite(best_team) else False})
summary = pd.DataFrame(rows)
plot_track_summary(summary, save_path='../figures/track_summary.png'); plt.show()
display(summary)
```
Markdown: per-track context for each of Antonelli's 2026 results — is each win at a Mercedes-strong (car) track or a driver-dependent one, and does Antonelli himself overperform there?

- [ ] **Step 5: Synthesis + caveats markdown** — tie back to the thesis: across all three controls (teammate within season, race mechanisms, cross-year track history), what does the evidence say about how much is Antonelli vs the car? Caveats: synthetic history; DNF exclusion (grid corroborates); small samples (MIN_TRACK_YEARS, team-switcher counts, ANT's 1–2 years); team rebrands treated as-is; era drift mitigated by within-season baselines.

- [ ] **Step 6: Execute the notebook**

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/03_driver_vs_car_track_history.ipynb --ExecutePreprocessor.timeout=1800
```
Expected: executes cleanly (first run is slow — it downloads the historical window results-only); the three track-history figures are written.

- [ ] **Step 7: Export PDFs** (match notebooks 01/02 route)

```bash
python -m jupyter nbconvert --to pdf notebooks/03_driver_vs_car_track_history.ipynb
python -m jupyter nbconvert --to pdf --no-input --output 03_driver_vs_car_track_history_no_code notebooks/03_driver_vs_car_track_history.ipynb
```
(Same LaTeX/webpdf fallback note as the 2026-05-29 plan if `--to pdf` lacks LaTeX.)

- [ ] **Step 8: Commit**

```bash
git add notebooks/03_driver_vs_car_track_history*.* figures/track_affinity_monaco.png figures/driver_vs_car_monaco.png figures/track_summary.png
git commit -m "feat: add notebook 03 — cross-year track history (Ch3)"
```

---

## Chunk 6: Chapter 1 — extend qualifying through Monaco

### Task 11: Update notebook 01 to import `RACES` and span 6 rounds

**Files:**
- Modify: `notebooks/01_antonelli_vs_russell.ipynb`
- Modify: `src/plotting.py` (one title string)

> **Locate cells by content, not index** (numbers drift). Confirm with:
> `python -c "import json;nb=json.load(open('notebooks/01_antonelli_vs_russell.ipynb'));[print(i,c['cell_type'],''.join(c['source'])[:70]) for i,c in enumerate(nb['cells'])]"`

- [ ] **Step 0: Recompute the 6-race aggregates live** (every prose number below comes from THIS output, not the plan):

```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
import pandas as pd
from src.loaders import setup_cache
from src.benchmarks import compare_teammates
from src.season import RACES
setup_cache('fastf1_cache')
res={r:compare_teammates(2026,r) for r in RACES}
meta=pd.DataFrame([res[r]['meta'] for r in RACES])
print(meta[['round','event_name','lap_delta_s','q_mismatch']].to_string(index=False))
print('6-race mean lap delta:', round(meta['lap_delta_s'].mean(),4))
alls=pd.concat([res[r]['segments'] for r in RACES]); clean=alls[alls['sensor_ok']]
print('Category means:'); print(clean.groupby('category')['delta_s'].mean().round(4).to_string())
r25={r:compare_teammates(2025,r) for r in RACES}
gains=[res[r]['meta']['lap_delta_s']-r25[r]['meta']['lap_delta_s'] for r in RACES]
print('YoY gains:', [round(g,3) for g in gains], '| mean', round(sum(gains)/len(RACES),3))
print('Canada q_mismatch 25/26:', r25['Canada']['meta']['q_mismatch'], res['Canada']['meta']['q_mismatch'])
print('Monaco q_mismatch 25/26:', r25['Monaco']['meta']['q_mismatch'], res['Monaco']['meta']['q_mismatch'])
" 2>&1 | grep -vi 'info\|warning\|cache\|download\|req\|api\|core'
```
Record this output. Use these live values for every edit below.

- [ ] **Step 1: Replace the hard-coded race list with the shared source** (code cell defining `RACES`):

```python
from src.season import RACES   # ['Australia','China','Japan','Miami','Canada','Monaco']
```
Remove any literal `RACES = [...]` line in the notebook.

- [ ] **Step 2: Title/intro markdown** — "first four rounds" → "first six rounds"; add that this notebook is **Chapter 1 (qualifying — getting to the front)** of the unified "driver vs car" piece, with chapters 2 (race wins) and 3 (track history) following. One sentence: Canada (R5) is where qualifying and result first diverged (qualified slower, won the race); Monaco (R6) is the opposite extreme — pole by a margin and a flag-to-flag win.

- [ ] **Step 3: Trajectory prose** — replace any "monotone / faster every round" claim with the honest 6-round shape from Step 0 (the climb already broke at Canada; Monaco adds a large +ve). State R1…R6 from live values and the 6-race mean.

- [ ] **Step 4: Category prose** — update the four per-category numbers to the live 6-race values; keep the "essentially flat" framing if still true. "five/six races" wording consistent; Japan remains the only sensor-flagged race unless Step 0 says otherwise.

- [ ] **Step 5: Corner-cycle prose** — re-check whether Monaco (a low-speed circuit) added fast-corner points; update the "N fast-corner data points across M races" phrasing to the live count.

- [ ] **Step 6: YoY prose** — the chart now spans 6 tracks; update the mean YoY gain and range from Step 0; confirm Canada/Monaco `q_mismatch` flags so the hollow-marker set is intentional.

- [ ] **Step 7: Section titles** — any `'first 4 rounds'` cell title and the `plot_category_deltas` title in `src/plotting.py` → "first 6 rounds". Commit the plotting.py title change with this task.

- [ ] **Step 8: Re-execute and regenerate figures**

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_antonelli_vs_russell.ipynb --ExecutePreprocessor.timeout=600
```
Expected: executes without error; `headline_segment_delta.png`, `lap_delta_by_round.png`, `track_delta_map.png`, `year_over_year.png`, `corner_buckets.png` regenerated with R5+R6.

- [ ] **Step 9: Regenerate notebook 01 PDFs**

```bash
python -m jupyter nbconvert --to pdf notebooks/01_antonelli_vs_russell.ipynb
python -m jupyter nbconvert --to pdf --no-input --output 01_antonelli_vs_russell_no_code notebooks/01_antonelli_vs_russell.ipynb
```

- [ ] **Step 10: Commit**

```bash
git add notebooks/01_antonelli_vs_russell*.* src/plotting.py figures/
git commit -m "feat: extend qualifying chapter through Monaco (R6); fix trajectory prose"
```

---

## Chunk 7: `scripts/refresh.py` — one-command season refresh

### Task 12: Create the refresh orchestrator

**Files:**
- Create: `scripts/refresh.py`

- [ ] **Step 1: Implement** — reads `RACES`/`YEARS` from `src/season.py`, ensures each 2026 Q+R session is cached (fetch if missing), executes notebooks 01→02→03, regenerates PDFs, prints a summary. No new analysis logic — pure orchestration.

```python
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
```

- [ ] **Step 2: Smoke-check the fetch step only** (don't run full notebooks here — that's the execution phase):

```bash
python -c "
import sys; sys.path.insert(0,'.')
import scripts.refresh as r
r.ensure_sessions()
" 2>&1 | grep -E 'ok|FAIL'
```
Expected: an `ok` line for every race × {Q,R}; no `FAIL`. (Monaco downloads here if not already cached.)

- [ ] **Step 3: Commit**

```bash
git add scripts/refresh.py
git commit -m "feat: add scripts/refresh.py one-command season refresh"
```

---

## Chunk 8: README reframe + case study + final verification

### Task 13: Reframe `README.md` around the single thesis

**Files:**
- Modify: `README.md`

- [ ] **Step 1: New title + opening** — H1 to the unified thesis (working: "Separating the Driver from the Car: How Good Is Kimi Antonelli, Really?"). Opening states the 5-of-6 win record and the three-chapter structure (Ch1 qualifying = nb 01, Ch2 race wins = nb 02, Ch3 cross-year track history = nb 03), each an independent way to remove the car.

- [ ] **Step 2: Headline findings** — restructure under the three chapters. Ch1: out-qualifies Russell more often than not, trajectory not monotone (live 6-race numbers), YoY rookie-arc compression over 6 tracks. Ch2: race record table + start conversion / pace-control / tire findings with their figures inlined. Ch3: the Monaco driver-vs-car read + the 6-track summary figure + where Antonelli overperforms.

- [ ] **Step 3: Inline all figures** — `headline_segment_delta.png`, `track_delta_map.png`, `corner_buckets.png`, `year_over_year.png` (Ch1); `start_conversion.png`, `stint_pace.png`, `gap_trace.png`, `tire_deg.png` (Ch2); `track_affinity_monaco.png`, `driver_vs_car_monaco.png`, `track_summary.png` (Ch3).

- [ ] **Step 4: "Updating after a new race" section** — document the one-edit workflow: append the race to `RACES` in `src/season.py`, run `python scripts/refresh.py`, commit. Note the first Ch3 run is slow (downloads the historical window).

- [ ] **Step 5: Method + Limitations** — Method covers qualifying (fastest valid lap), race (clean green-flag laps, `TrackStatus=='1'`), and track history (overperformance vs season baseline, DNF-excluded, grid cross-check). Limitations add: 6-race sample; synthetic historical data (Ch3 claims are "in this dataset"); DNF handling; small samples; team-rebrand treatment; era drift. Keep the Japan sensor-freeze section.

- [ ] **Step 6: Kill stale "four"/"4 rounds"/"monotone" language** and update the project-structure tree (add `notebooks/02`, `notebooks/03`, `src/race.py`, `src/track_history.py`, `src/season.py`, `scripts/refresh.py`, new tests).

- [ ] **Step 7: Verify all figure links resolve**

```bash
grep -o "figures/[A-Za-z_]*\.png" README.md | sort -u | while read f; do test -f "$f" && echo "OK $f" || echo "MISSING $f"; done
```
Expected: every referenced figure prints `OK`.

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs: reframe README around the driver-vs-car thesis (6 rounds, 3 chapters)"
```

### Task 14: Refresh `case_study.pdf`

**Files:**
- Modify: `case_study.pdf`, `docs/case_study.md`

- [ ] **Step 1: Find the generation route**

```bash
git log --oneline -- case_study.pdf | head
```
Match how the current PDF is produced (likely an export of `docs/case_study.md`).

- [ ] **Step 2: Update `docs/case_study.md`** to the new framing (title, 5-of-6 wins, the three controls, live 6-race numbers) and regenerate `case_study.pdf` via that same route.

- [ ] **Step 3: Eyeball the PDF** — confirm the reframe shows; no stale "four rounds".

- [ ] **Step 4: Commit**

```bash
git add case_study.pdf docs/case_study.md
git commit -m "docs: refresh case study for driver-vs-car reframe"
```

### Task 15: Final verification

- [ ] **Step 1: Full test suite**

Run: `python -m pytest -v`
Expected: `tests/test_segments.py`, `tests/test_season.py`, `tests/test_race.py` (incl. Canada + Monaco anchors), `tests/test_track_history.py` all PASS (track-history/race skip only if their cache isn't populated — run `scripts/refresh.py` first to avoid skips).

- [ ] **Step 2: Grep for stale language**

Run: `grep -rin "four round\|first 4\|first four\|4 rounds\|monotone" README.md notebooks/*.ipynb docs/case_study.md`
Expected: no stale four-rounds/monotone claims (any "monotone" only in the "broke at Canada" context).

- [ ] **Step 3: Confirm all figures exist**

Run: `ls figures/headline_segment_delta.png figures/track_delta_map.png figures/corner_buckets.png figures/year_over_year.png figures/start_conversion.png figures/stint_pace.png figures/gap_trace.png figures/tire_deg.png figures/track_affinity_monaco.png figures/driver_vs_car_monaco.png figures/track_summary.png`
Expected: all present.

- [ ] **Step 4: Confirm the refresh contract** — `RACES` is imported (not hard-coded) in all three notebooks:

Run: `grep -L "from src.season import" notebooks/01_antonelli_vs_russell.ipynb notebooks/02_how_antonelli_wins_races.ipynb notebooks/03_driver_vs_car_track_history.ipynb`
Expected: no output (every notebook imports the shared source).

- [ ] **Step 5:** Use superpowers:requesting-code-review to review the whole branch.

- [ ] **Step 6:** Use superpowers:finishing-a-development-branch to decide on merge / PR.
