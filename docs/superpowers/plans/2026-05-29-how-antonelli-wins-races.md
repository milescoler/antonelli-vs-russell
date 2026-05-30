# How Antonelli Keeps Winning — Race-Result Analysis Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the f1_project portfolio piece around "Antonelli has won 4 of the last 4 races — how?", adding a race-result analysis (start, race pace, tire degradation) on top of the existing qualifying comparison, and updating the qualifying chapter to include Canada (Round 5).

**Architecture:** A new isolated module `src/race.py` holds all race-session logic (loading R sessions, filtering to clean green-flag laps, and computing start / pace / tire / gap metrics), mirroring how `src/benchmarks.py` wraps qualifying. Four new plotting functions go in `src/plotting.py`. A new notebook `02` narrates the race chapters; notebook `01` is updated to add Canada and regenerate its figures; `README.md` is reframed and `case_study.pdf` refreshed. Pure functions take/return tidy DataFrames; plotting stays FastF1-free.

**Tech Stack:** Python 3.12, FastF1 3.8.x, pandas, numpy, matplotlib, pytest, Jupyter/nbconvert.

**Spec:** [docs/superpowers/specs/2026-05-29-how-antonelli-wins-races-design.md](../specs/2026-05-29-how-antonelli-wins-races-design.md)

---

## Conventions used throughout

- **Sign convention (race chapters):** stated once and held everywhere — **positive = Antonelli better** (more positions gained, faster pace, lower degradation). Matches the qualifying chapter (`delta = RUS − ANT`, positive = ANT faster).
- **Reference drivers:** `ANT` (Antonelli, controlled teammate spine), `RUS` (Russell, teammate control), and the **per-race actual P2 finisher** (field context — varies by race; e.g. Canada P2 = HAM).
- **Clean lap = green-flag racing lap:** `TrackStatus == '1'` exactly (any multi-digit value means the status changed mid-lap → excluded), not an in-lap / out-lap / pit lap, and not lap 1.
- **`RACES` master list:** `['Australia', 'China', 'Japan', 'Miami', 'Canada']` — drives both notebooks.
- **Cache:** all five 2026 race sessions and the 2025 Canada qualifying session are already in `fastf1_cache/`. No network needed.

---

## File structure

| File | Responsibility | Action |
|------|---------------|--------|
| `src/race.py` | All race-session logic: load R session, clean-lap filter, start/pace/tire/gap metrics | Create |
| `tests/test_race.py` | Invariant tests + Canada end-to-end regression anchor | Create |
| `src/plotting.py` | + `plot_start_conversion`, `plot_stint_pace`, `plot_gap_trace`, `plot_tire_deg` | Modify |
| `notebooks/02_how_antonelli_wins_races.ipynb` | Race chapters narrative + charts | Create |
| `notebooks/01_antonelli_vs_russell.ipynb` | Add `'Canada'` to `RACES`; fix monotone-trend prose; regenerate | Modify |
| `README.md` | Reframe around winning; 5-race numbers; new race chapters | Modify |
| `figures/*.png` | 4 new race figures + 5 regenerated qualifying figures | Create/regen |
| `case_study.pdf` | Refresh to new framing | Regen |

---

## Chunk 1: `src/race.py` core — session load + clean-lap filter

### Task 1: `load_race_session`

**Files:**
- Create: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_race.py
"""
Race-session analysis tests. Invariant checks on real cached telemetry
(no exact-value brittleness), plus one Canada end-to-end regression anchor —
Canada is the race the whole "how he wins" reframe hinges on (ANT started P2,
led by lap 2, won after Russell retired).
"""
from pathlib import Path
import pytest

from src.loaders import setup_cache
from src import race

CACHE_DIR = Path(__file__).resolve().parent.parent / "fastf1_cache"
CANADA_DIR = CACHE_DIR / "2026" / "2026-05-24_Canadian_Grand_Prix"


@pytest.fixture(scope="module", autouse=True)
def _enable_cache():
    if not CANADA_DIR.exists():
        pytest.skip("FastF1 cache not populated for Canada 2026.")
    setup_cache(str(CACHE_DIR))


def test_load_race_session_has_laps():
    session = race.load_race_session(2026, "Canada")
    assert session.laps is not None
    assert len(session.laps) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_load_race_session_has_laps -v`
Expected: FAIL with `AttributeError: module 'src.race' has no attribute 'load_race_session'` (or ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/race.py
"""
Race-session analysis: how Antonelli converts grid position into wins.
Loads FastF1 Race (R) sessions and computes start, race-pace, tire-degradation,
and gap-to-rival metrics. Mirrors src/benchmarks.py (qualifying) in spirit:
pure-ish functions returning tidy DataFrames; plotting lives in src/plotting.py.

Sign convention: positive = Antonelli better (positions gained, pace, low deg).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import fastf1

from src.loaders import setup_cache  # noqa: F401  (re-exported for convenience)


def load_race_session(year: int, round_or_name) -> fastf1.core.Session:
    """Load a Race (R) session with laps. Parallels load_qualifying_session,
    but for the race. Telemetry is not needed for the race metrics, so we load
    laps only (faster)."""
    session = fastf1.get_session(year, round_or_name, "R")
    session.load(telemetry=False, weather=False, messages=False)
    return session
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_load_race_session_has_laps -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add load_race_session for race-result analysis"
```

### Task 2: `get_clean_laps` (the shared green-flag filter)

**Files:**
- Modify: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test**

```python
def test_get_clean_laps_are_green_and_exclude_lap1_and_pits():
    session = race.load_race_session(2026, "Canada")
    clean = race.get_clean_laps(session, "ANT")
    # Every clean lap is fully green (no mid-lap status change).
    assert (clean["TrackStatus"] == "1").all()
    # No lap 1.
    assert (clean["LapNumber"] != 1).all()
    # No in-laps / out-laps (pit times present mark those).
    assert clean["PitInTime"].isna().all()
    assert clean["PitOutTime"].isna().all()
    # Returns a non-empty, valid-laptime frame for a normal stint.
    assert len(clean) > 0
    assert clean["LapTime"].notna().all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_get_clean_laps_are_green_and_exclude_lap1_and_pits -v`
Expected: FAIL — `get_clean_laps` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/race.py`:

```python
def get_clean_laps(session, driver: str) -> pd.DataFrame:
    """Green-flag racing laps for one driver, as a plain DataFrame.

    A clean lap:
      - has TrackStatus == '1' for the WHOLE lap (FastF1 concatenates per-lap
        status codes; any multi-character value means the status changed
        mid-lap, e.g. a safety car was deployed — those laps are excluded),
      - is not an in-lap or out-lap (PitInTime / PitOutTime are NaT),
      - is not lap 1 (standing-start lap is not representative race pace),
      - has a valid LapTime.

    This is the shared filter every race-pace / tire metric builds on.
    """
    laps = session.laps.pick_drivers(driver)
    clean = laps[
        (laps["TrackStatus"] == "1")
        & (laps["LapNumber"] != 1)
        & (laps["PitInTime"].isna())
        & (laps["PitOutTime"].isna())
        & (laps["LapTime"].notna())
    ].copy()
    clean["LapTimeSeconds"] = clean["LapTime"].dt.total_seconds()
    return clean.reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_get_clean_laps_are_green_and_exclude_lap1_and_pits -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add get_clean_laps green-flag filter"
```

---

## Chunk 2: `src/race.py` metrics — start, pace, tire, gap

### Task 3: `_pn_finisher` helper + `start_summary`

**Files:**
- Modify: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test** (this is also the Canada end-to-end regression anchor)

```python
def test_start_summary_canada_anchor():
    df = race.start_summary(2026, "Canada")
    ant = df[df["driver"] == "ANT"].iloc[0]
    # The case the whole reframe hinges on: ANT started P2, ran P2 on lap 1,
    # and finished P1.
    assert int(ant["grid"]) == 2
    assert int(ant["lap1_pos"]) == 2
    assert int(ant["finish"]) == 1
    # Invariant: positions_gained is grid minus lap-1 position.
    assert int(ant["positions_gained"]) == int(ant["grid"]) - int(ant["lap1_pos"])
    # The field reference (per-race P2 finisher) is present and is HAM at Canada.
    assert "P2" in set(df["driver"])
    p2 = df[df["driver"] == "P2"].iloc[0]
    assert p2["code"] == "HAM"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_start_summary_canada_anchor -v`
Expected: FAIL — `start_summary` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/race.py`:

```python
def _pn_finisher(session, n: int) -> str:
    """Driver code (abbreviation) of the car classified Pn in the race."""
    res = session.results
    row = res[res["Position"] == float(n)]
    if row.empty:
        raise ValueError(f"No P{n} finisher found in this race.")
    return str(row["Abbreviation"].iloc[0])


def _lap1_position(session, code: str) -> float:
    """Position at the end of lap 1 for a driver code."""
    laps = session.laps.pick_drivers(code)
    lap1 = laps[laps["LapNumber"] == 1]
    if lap1.empty:
        return float("nan")
    return float(lap1["Position"].iloc[0])


def start_summary(year: int, race_name, drv_a: str = "ANT", drv_b: str = "RUS") -> pd.DataFrame:
    """One row per reference driver (ANT, RUS, and the per-race P2 finisher):
    grid position, position at end of lap 1, positions gained on lap 1, and
    final classified position.

    'driver' column is the ROLE ('ANT' / 'RUS' / 'P2'); 'code' is the actual
    three-letter code (so the field reference's identity is visible — it
    varies by race).

    positions_gained = grid - lap1_pos  (positive = gained places off the line).
    """
    session = load_race_session(year, race_name)
    res = session.results

    p2_code = _pn_finisher(session, 2)
    roles = [("ANT", drv_a), ("RUS", drv_b), ("P2", p2_code)]

    rows = []
    for role, code in roles:
        r = res[res["Abbreviation"] == code]
        if r.empty:
            continue
        grid = float(r["GridPosition"].iloc[0])
        finish = float(r["Position"].iloc[0])
        lap1 = _lap1_position(session, code)
        rows.append({
            "race": str(session.event["EventName"]),
            "driver": role,
            "code": code,
            "grid": grid,
            "lap1_pos": lap1,
            "positions_gained": grid - lap1,
            "finish": finish,
            "status": str(r["Status"].iloc[0]),
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_start_summary_canada_anchor -v`
Expected: PASS.

> **Edge-case note (no extra test needed for the 5 races in scope):** `_pn_finisher`
> resolves the classified P2 from `session.results`, and `start_summary` skips a role
> whose code has no results row (`if r.empty: continue`). Across all 5 races in scope the
> P2 finisher is always classified, so the P2 row is always present. If this analysis is
> ever extended to a race where the P2 has no results row, the P2 row (and its downstream
> field reference) drops silently — acceptable graceful degradation per spec §8, but worth
> remembering.

- [ ] **Step 5: Commit**

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add start_summary with Canada regression anchor"
```

### Task 4: `stint_pace`

**Files:**
- Modify: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test**

```python
def test_stint_pace_columns_and_compounds():
    df = race.stint_pace(2026, "Canada", ["ANT", "RUS"])
    assert set(["driver", "stint", "compound", "median_laptime_s", "n_clean"]).issubset(df.columns)
    # ANT ran SOFT then MEDIUM at Canada — both should appear.
    ant_comps = set(df[df["driver"] == "ANT"]["compound"])
    assert {"SOFT", "MEDIUM"}.issubset(ant_comps)
    # Median lap times are plausible race laps for Montreal (~70-95 s).
    assert df["median_laptime_s"].between(60, 110).all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_stint_pace_columns_and_compounds -v`
Expected: FAIL — `stint_pace` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/race.py`:

```python
def stint_pace(year: int, race_name, drivers: list[str]) -> pd.DataFrame:
    """Per driver per stint: median CLEAN-lap time, compound, and clean-lap
    count. Built on get_clean_laps, so safety-car/pit/lap-1 laps are excluded.
    Use for like-compound pace comparison between ANT, RUS, and the field ref;
    the caller is responsible for only comparing matching compounds."""
    session = load_race_session(year, race_name)
    rows = []
    for code in drivers:
        clean = get_clean_laps(session, code)
        if clean.empty:
            continue
        for stint, grp in clean.groupby("Stint"):
            rows.append({
                "race": str(session.event["EventName"]),
                "driver": code,
                "stint": int(stint),
                "compound": str(grp["Compound"].iloc[0]),
                "median_laptime_s": float(grp["LapTimeSeconds"].median()),
                "n_clean": int(len(grp)),
            })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_stint_pace_columns_and_compounds -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add stint_pace race-pace metric"
```

### Task 5: `tire_deg` (with the ≥5-clean-lap small-n guard)

**Files:**
- Modify: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test**

```python
MIN_DEG_LAPS = 5  # mirror of race.MIN_DEG_LAPS, asserted explicitly below


def test_tire_deg_small_n_guard_and_slope_units():
    df = race.tire_deg(2026, "Canada", ["ANT", "RUS"])
    assert race.MIN_DEG_LAPS == MIN_DEG_LAPS
    assert set(["driver", "stint", "compound", "deg_slope_s_per_lap", "n_clean"]).issubset(df.columns)
    # Small-n guard: any stint with < MIN_DEG_LAPS clean laps must have NaN slope.
    short = df[df["n_clean"] < MIN_DEG_LAPS]
    assert short["deg_slope_s_per_lap"].isna().all()
    # Stints with enough laps produce a finite slope.
    enough = df[df["n_clean"] >= MIN_DEG_LAPS]
    assert enough["deg_slope_s_per_lap"].notna().all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_tire_deg_small_n_guard_and_slope_units -v`
Expected: FAIL — `tire_deg` / `MIN_DEG_LAPS` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/race.py` (add the constant near the top of the file, under the imports):

```python
MIN_DEG_LAPS = 5  # minimum clean laps in a stint to fit a degradation slope
```

```python
def tire_deg(year: int, race_name, drivers: list[str]) -> pd.DataFrame:
    """Per driver per clean stint: linear slope of clean-lap time vs TyreLife
    (seconds lost per lap of tire age), the compound, and the clean-lap count.

    Stints with fewer than MIN_DEG_LAPS clean laps yield deg_slope_s_per_lap =
    NaN (a fitted slope on 2-3 points is noise, not signal). Fuel burn lowers
    lap times through a stint and partially offsets real degradation — this is
    NOT corrected for; it is named as a caveat in the narrative."""
    session = load_race_session(year, race_name)
    rows = []
    for code in drivers:
        clean = get_clean_laps(session, code)
        if clean.empty:
            continue
        for stint, grp in clean.groupby("Stint"):
            n = len(grp)
            if n >= MIN_DEG_LAPS:
                slope = float(
                    np.polyfit(grp["TyreLife"].astype(float),
                               grp["LapTimeSeconds"].astype(float), 1)[0]
                )
            else:
                slope = float("nan")
            rows.append({
                "race": str(session.event["EventName"]),
                "driver": code,
                "stint": int(stint),
                "compound": str(grp["Compound"].iloc[0]),
                "deg_slope_s_per_lap": slope,
                "n_clean": int(n),
            })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_tire_deg_small_n_guard_and_slope_units -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add tire_deg with small-n guard"
```

### Task 6: `gap_to_rival` (one semantics for leader and chaser)

**Files:**
- Modify: `src/race.py`
- Test: `tests/test_race.py`

- [ ] **Step 1: Write the failing test**

```python
def test_gap_to_rival_leading_flag_and_columns():
    df = race.gap_to_rival(2026, "Canada", "ANT")
    assert set(["lap", "gap_s", "leading"]).issubset(df.columns)
    # ANT led most of Canada — there must be laps flagged leading.
    assert df["leading"].any()
    # When leading, gap_s is the (negative) margin ahead of P2; when chasing,
    # it's the (positive) gap behind the leader. So leading rows are <= 0.
    assert (df.loc[df["leading"], "gap_s"] <= 0).all()
    # One row per racing lap, sorted by lap.
    assert df["lap"].is_monotonic_increasing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race.py::test_gap_to_rival_leading_flag_and_columns -v`
Expected: FAIL — `gap_to_rival` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `src/race.py`:

```python
def gap_to_rival(year: int, race_name, driver: str) -> pd.DataFrame:
    """Per-lap race-control trace for `driver`, with a single consistent
    semantics so the notebook never special-cases the leader:

      - When `driver` is NOT leading at the end of a lap: gap_s is the time
        gap BEHIND the leader (positive = behind), and leading=False.
      - When `driver` IS leading: gap_s is the gap AHEAD of P2, expressed as a
        NEGATIVE number (so 'lower is better/further ahead' holds across the
        whole trace), and leading=True.

    Gaps are derived from each lap's cumulative session Time at the timing
    line: gap to a rival on a given lap = our Time(lap) - their Time(lap).
    Laps where the needed Time values are missing are skipped.
    """
    session = load_race_session(year, race_name)
    laps = session.laps

    # Pivot: cumulative Time at the end of each lap, per driver code.
    # session.laps['Time'] is the session clock at lap completion.
    t = laps[["LapNumber", "DriverNumber", "Position", "Time"]].copy()
    t["Time_s"] = t["Time"].dt.total_seconds()

    drv_num = session.get_driver(driver)["DriverNumber"]

    rows = []
    for lap_no, grp in t.groupby("LapNumber"):
        grp = grp.dropna(subset=["Time_s", "Position"])
        if grp.empty:
            continue
        me = grp[grp["DriverNumber"] == drv_num]
        if me.empty:
            continue
        my_time = float(me["Time_s"].iloc[0])
        my_pos = float(me["Position"].iloc[0])

        if my_pos == 1.0:
            # Leading: gap ahead of P2 (negative).
            p2 = grp[grp["Position"] == 2.0]
            if p2.empty:
                continue
            gap = my_time - float(p2["Time_s"].iloc[0])  # <= 0
            leading = True
        else:
            # Chasing: gap behind leader (positive).
            leader = grp[grp["Position"] == 1.0]
            if leader.empty:
                continue
            gap = my_time - float(leader["Time_s"].iloc[0])  # >= 0
            leading = False

        rows.append({
            "race": str(session.event["EventName"]),
            "lap": int(lap_no),
            "gap_s": gap,
            "leading": leading,
        })
    return pd.DataFrame(rows).sort_values("lap").reset_index(drop=True)
```

> **Implementer note:** verify `session.get_driver(driver)["DriverNumber"]` returns the same dtype stored in `laps["DriverNumber"]` (both are strings in FastF1 3.8). If a mismatch appears in the test, cast both to `str` before comparing. This is the one interface detail flagged in spec §8.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_race.py::test_gap_to_rival_leading_flag_and_columns -v`
Expected: PASS.

- [ ] **Step 5: Run the full race test module and commit**

Run: `python -m pytest tests/test_race.py -v`
Expected: all tests PASS.

```bash
git add src/race.py tests/test_race.py
git commit -m "feat: add gap_to_rival race-control trace"
```

---

## Chunk 3: plotting functions

All four follow the existing `src/plotting.py` contract: take a pre-shaped DataFrame, optional `save_path`, return the `plt.Figure`; no FastF1 imports; save at 150 dpi with `bbox_inches='tight'`; hide top/right spines; `fig.tight_layout()`. Reuse the existing save block:

```python
if save_path is not None:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
```

These are visual helpers — they are exercised by being called in notebook `02` (Chunk 5) and eyeballed, not unit-tested for pixels. Each task's check is "import and call on real data without error, and the PNG is written."

### Task 7: `plot_start_conversion`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement**

Add to `src/plotting.py`. A grid→lap1→finish slope chart, one panel per race, ANT/RUS/P2 lines. Lower y = better track position, so **invert the y-axis** (P1 at top).

```python
def plot_start_conversion(start_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Per race, a 3-point slope line (grid -> end of lap 1 -> finish) for
    ANT, RUS, and the per-race P2 finisher. Y-axis is track position, inverted
    so P1 sits at the top. Highlights Canada (ANT P2->led->win) and Australia
    (ANT P2->P2, the loss).

    Required columns: race, driver, code, grid, lap1_pos, finish.
    """
    races = list(dict.fromkeys(start_df["race"]))  # preserve order
    role_color = {"ANT": "#1f77b4", "RUS": "#7f7f7f", "P2": "#d62728"}
    fig, axes = plt.subplots(1, len(races), figsize=(3.2 * len(races), 4.2), sharey=True)
    if len(races) == 1:
        axes = [axes]
    stages = ["grid", "lap1_pos", "finish"]
    stage_labels = ["Grid", "End L1", "Finish"]
    for ax, rc in zip(axes, races):
        sub = start_df[start_df["race"] == rc]
        for _, row in sub.iterrows():
            ys = [row[s] for s in stages]
            label = row["driver"] if row["driver"] != "P2" else f"P2 ({row['code']})"
            ax.plot(range(3), ys, marker="o", color=role_color[row["driver"]], label=label)
        ax.set_title(rc.replace(" Grand Prix", ""), fontsize=10)
        ax.set_xticks(range(3))
        ax.set_xticklabels(stage_labels, fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Track position (P1 = top)")
    axes[-1].legend(fontsize=8, loc="lower right")
    fig.suptitle("Grid → lap 1 → finish: how Antonelli's races unfold", fontsize=12)
    fig.tight_layout()
    # (save block here)
    return fig
```
(Insert the shared save block before `return fig`.)

- [ ] **Step 2: Smoke-check**

Run:
```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import race
from src.plotting import plot_start_conversion
import pandas as pd
setup_cache('fastf1_cache')
df = pd.concat([race.start_summary(2026,r) for r in ['Australia','China','Japan','Miami','Canada']], ignore_index=True)
plot_start_conversion(df, save_path='figures/start_conversion.png')
print('OK')
"
```
Expected: prints `OK`; `figures/start_conversion.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/start_conversion.png
git commit -m "feat: add plot_start_conversion chart"
```

### Task 8: `plot_stint_pace`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — grouped bars of `median_laptime_s` per stint, grouped by race, colored by driver role; annotate each bar with its compound. Lower bar = faster.

```python
def plot_stint_pace(pace_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Median clean-lap time per stint, ANT vs RUS vs field (P2 finisher code),
    grouped by race. Each bar annotated with its tire compound. Lower = faster.
    Compare bars WITHIN a race and only across matching compounds.

    Required columns: race, driver, stint, compound, median_laptime_s.
    'driver' here is the actual code (ANT/RUS/<P2 code>)."""
    # Implementation: one subplot per race (pace scale differs per circuit),
    # x = stint index, grouped bars per driver, compound text above each bar.
    races = list(dict.fromkeys(pace_df["race"]))
    fig, axes = plt.subplots(1, len(races), figsize=(3.4 * len(races), 4.2))
    if len(races) == 1:
        axes = [axes]
    drivers = list(dict.fromkeys(pace_df["driver"]))
    colors = plt.cm.tab10.colors
    dcolor = {d: colors[i % 10] for i, d in enumerate(drivers)}
    for ax, rc in zip(axes, races):
        sub = pace_df[pace_df["race"] == rc]
        stints = sorted(sub["stint"].unique())
        width = 0.8 / max(len(drivers), 1)
        for j, d in enumerate(drivers):
            ds = sub[sub["driver"] == d].set_index("stint")
            xs, ys, comps = [], [], []
            for k, st in enumerate(stints):
                if st in ds.index:
                    xs.append(k + j * width)
                    ys.append(ds.loc[st, "median_laptime_s"])
                    comps.append(ds.loc[st, "compound"][:1])
            ax.bar(xs, ys, width=width, color=dcolor[d], label=d)
            for x, y, c in zip(xs, ys, comps):
                ax.text(x, y, c, ha="center", va="bottom", fontsize=7)
        ax.set_title(rc.replace(" Grand Prix", ""), fontsize=10)
        ax.set_xticks([k + width for k in range(len(stints))])
        ax.set_xticklabels([f"Stint {s}" for s in stints], fontsize=8)
        ax.set_ylabel("Median clean lap (s)")
        # Zoom y to the data band so small pace gaps are visible.
        lo, hi = sub["median_laptime_s"].min(), sub["median_laptime_s"].max()
        ax.set_ylim(lo - 0.5, hi + 1.0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[-1].legend(fontsize=8)
    fig.suptitle("Race pace by stint (lower = faster); letter = compound", fontsize=12)
    fig.tight_layout()
    # (save block)
    return fig
```

- [ ] **Step 2: Smoke-check** — same pattern as Task 7, building `pace_df` per race for `['ANT','RUS', <P2 code>]`. For the field driver, resolve the P2 code per race via `race.start_summary(...)`’s `code` where `driver=='P2'`, or just call `stint_pace(2026, r, ['ANT','RUS'])` for the teammate comparison and add the P2 code per race. Minimal smoke test may use `['ANT','RUS']` only.

Run:
```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import race
from src.plotting import plot_stint_pace
import pandas as pd
setup_cache('fastf1_cache')
df = pd.concat([race.stint_pace(2026,r,['ANT','RUS']) for r in ['Australia','China','Japan','Miami','Canada']], ignore_index=True)
plot_stint_pace(df, save_path='figures/stint_pace.png'); print('OK')
"
```
Expected: `OK`; `figures/stint_pace.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/stint_pace.png
git commit -m "feat: add plot_stint_pace chart"
```

### Task 9: `plot_gap_trace`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — a per-lap line of `gap_s` over `lap`, one line per race (or small multiples). Draw `y=0` reference. Negative = ANT leading/ahead; positive = behind. Shade leading vs chasing differently if convenient.

```python
def plot_gap_trace(gap_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Per-lap race-control trace. y = gap_s (negative when ANT leads/ahead of
    P2, positive when chasing the leader). One line per race. The y=0 line is
    the lead/chase boundary.

    Required columns: race, lap, gap_s, leading."""
    races = list(dict.fromkeys(gap_df["race"]))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = plt.cm.tab10.colors
    for i, rc in enumerate(races):
        sub = gap_df[gap_df["race"] == rc]
        ax.plot(sub["lap"], sub["gap_s"], color=colors[i % 10],
                label=rc.replace(" Grand Prix", ""))
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Lap")
    ax.set_ylabel("Gap (s): negative = Antonelli leading / ahead of P2")
    ax.set_title("How Antonelli controls the race: gap trace per round")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8)
    fig.tight_layout()
    # (save block)
    return fig
```

- [ ] **Step 2: Smoke-check**

Run:
```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import race
from src.plotting import plot_gap_trace
import pandas as pd
setup_cache('fastf1_cache')
df = pd.concat([race.gap_to_rival(2026,r,'ANT') for r in ['China','Japan','Miami','Canada']], ignore_index=True)
plot_gap_trace(df, save_path='figures/gap_trace.png'); print('OK')
"
```
Expected: `OK`; `figures/gap_trace.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/gap_trace.png
git commit -m "feat: add plot_gap_trace chart"
```

### Task 10: `plot_tire_deg`

**Files:**
- Modify: `src/plotting.py`

- [ ] **Step 1: Implement** — grouped bars of `deg_slope_s_per_lap` for comparable (same-compound) ANT vs RUS stints; skip NaN (small-n) stints with a visible "n too small" note. Lower slope = better tire management.

```python
def plot_tire_deg(deg_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Tire-degradation slope (s lost per lap of tire age) for comparable
    stints, ANT vs RUS. Lower = better tire management. Stints with NaN slope
    (fewer than MIN_DEG_LAPS clean laps) are omitted from bars and listed as a
    caption note rather than shown as zero.

    Required columns: race, driver, stint, compound, deg_slope_s_per_lap, n_clean."""
    fittable = deg_df.dropna(subset=["deg_slope_s_per_lap"]).copy()
    fittable["label"] = (fittable["race"].str.replace(" Grand Prix", "", regex=False)
                         + "\nS" + fittable["stint"].astype(str)
                         + " " + fittable["compound"].str[:1])
    drivers = list(dict.fromkeys(fittable["driver"]))
    labels = list(dict.fromkeys(fittable["label"]))
    colors = {"ANT": "#1f77b4", "RUS": "#7f7f7f"}
    fig, ax = plt.subplots(figsize=(max(8, 1.1 * len(labels)), 5))
    width = 0.8 / max(len(drivers), 1)
    for j, d in enumerate(drivers):
        ds = fittable[fittable["driver"] == d].set_index("label")
        xs = [k + j * width for k, lab in enumerate(labels) if lab in ds.index]
        ys = [ds.loc[lab, "deg_slope_s_per_lap"] for lab in labels if lab in ds.index]
        ax.bar(xs, ys, width=width, color=colors.get(d, "#999"), label=d)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks([k + width / 2 for k in range(len(labels))])
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Degradation (s lost per lap of tire age)\nlower = better")
    ax.set_title("Tire management by stint: Antonelli vs Russell")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8)
    fig.tight_layout()
    # (save block)
    return fig
```

- [ ] **Step 2: Smoke-check**

Run:
```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
from src.loaders import setup_cache; from src import race
from src.plotting import plot_tire_deg
import pandas as pd
setup_cache('fastf1_cache')
df = pd.concat([race.tire_deg(2026,r,['ANT','RUS']) for r in ['Australia','China','Japan','Miami','Canada']], ignore_index=True)
plot_tire_deg(df, save_path='figures/tire_deg.png'); print('OK')
"
```
Expected: `OK`; `figures/tire_deg.png` exists.

- [ ] **Step 3: Commit**

```bash
git add src/plotting.py figures/tire_deg.png
git commit -m "feat: add plot_tire_deg chart"
```

---

## Chunk 4: update qualifying chapter (notebook 01) to include Canada

### Task 11: Add Canada to `RACES` and fix the monotone-trend prose

**Files:**
- Modify: `notebooks/01_antonelli_vs_russell.ipynb`

> **Locating cells:** the cell numbers below (e.g. "cell 15") are from the plan author's
> snapshot and may drift. Locate each target cell by its **content** (the quoted phrase
> being replaced), not by index. Confirm with
> `python -c "import json;nb=json.load(open('notebooks/01_antonelli_vs_russell.ipynb'));[print(i,c['cell_type'],''.join(c['source'])[:70]) for i,c in enumerate(nb['cells'])]"`
> before editing.

- [ ] **Step 0: Compute and confirm the 5-race aggregates BEFORE editing any prose.** The numbers carried into the prose below (and into the README in Chunk 6) must be the live values, not assumed. Run this and record the printout; every prose edit in this task and Task 13 uses *these* numbers, not the ones written in the plan:

```bash
python -c "
import sys; sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore')
import pandas as pd
from src.loaders import setup_cache
from src.benchmarks import compare_teammates, compute_corner_signatures
setup_cache('fastf1_cache')
RACES=['Australia','China','Japan','Miami','Canada']
res={r:compare_teammates(2026,r) for r in RACES}
meta=pd.DataFrame([res[r]['meta'] for r in RACES])
print('Per-round lap delta (RUS-ANT; + = ANT faster):')
print(meta[['round','event_name','lap_delta_s','q_mismatch']].to_string(index=False))
print('5-race mean lap delta:', round(meta['lap_delta_s'].mean(),4))
alls=pd.concat([res[r]['segments'] for r in RACES]); clean=alls[alls['sensor_ok']]
print('Category means (clean):'); print(clean.groupby('category')['delta_s'].mean().round(4).to_string())
r25={r:compare_teammates(2025,r) for r in RACES}
gains=[res[r]['meta']['lap_delta_s']-r25[r]['meta']['lap_delta_s'] for r in RACES]
print('YoY gains:', [round(g,3) for g in gains], '| mean', round(sum(gains)/5,3))
print('2025 Canada q_mismatch:', r25['Canada']['meta']['q_mismatch'], '| 2026 Canada q_mismatch:', res['Canada']['meta']['q_mismatch'])
" 2>&1 | grep -v 'INFO\|WARNING\|core\|req\|_api\|cache'
```
Expected: a clean table of 5 per-round deltas, the 5-race mean, category means, YoY gains + mean, and both Canada `q_mismatch` flags. **If any value differs from the plan's "numbers to carry" table, the live value wins** — update the prose (and the Chunk 6 README table) to match what this prints.

- [ ] **Step 1: Update the RACES list (code cell 1)**

Change:
```python
RACES = ['Australia', 'China', 'Japan', 'Miami']
```
to:
```python
RACES = ['Australia', 'China', 'Japan', 'Miami', 'Canada']
```

- [ ] **Step 2: Update the title/intro markdown (cell 0)** — change "First Four Rounds" / "first four rounds" to "first five rounds" and note that this notebook is now Chapter 1 (qualifying) of the larger "how he keeps winning" piece. Add one sentence: "Canada (R5) is the round where qualifying and race results diverge — he qualified slower than Russell but won the race; see notebook 02."

- [ ] **Step 3: Fix the trajectory prose (cell 15)** — the current text claims a "monotone trend ... ahead on every subsequent round". Replace with the honest 5-race version:

> Across five rounds the qualifying gap went from −0.29 s (Russell faster) at Australia to a peak of +0.40 s (Antonelli faster) at Miami, then **back to −0.07 s at Canada** — so the early monotone climb did **not** continue. R1 −0.29 → R2 +0.22 → R3 +0.30 → R4 +0.40 → **R5 −0.07**. Five-race mean +0.11 s in Antonelli's favour. He out-qualifies Russell more often than not, but Canada is a clear reminder that the trend is noisy at this sample size — and, as notebook 02 shows, qualifying is not the whole story of how he wins races.

- [ ] **Step 4: Fix the headline-finding category prose (cell 12)** — update the four per-category numbers to the 5-race values: straights **+0.005**, slow **−0.001**, fast **−0.003**, medium **−0.014** s/lap. Keep the "essentially flat / within ±0.01–0.014" framing (still true). Update any "four races" → "five races" and "five Japan segments" wording remains correct (Japan is still the only sensor-flagged race).

- [ ] **Step 5: Fix the corner-cycle prose (cells 24/21 as needed)** — note that Canada (Montreal) added **no** fast-corner braking points, so the fast-corner signature is unchanged at 12 points (brakes ~21 m later, throttle ~23 m sooner). Update the "12 fast-corner data points across 4 races" phrasing to "across 5 races (Canada added none — it's a low-speed circuit)".

- [ ] **Step 6: Fix the YoY prose (cells 25/30)** — 5-track mean YoY gain is now **+0.51 s/track** (was +0.53), range 0.29–0.69, Canada +0.42. Keep the "compressing his rookie arc" conclusion. Confirm whether 2025 or 2026 Canada raises a `q_mismatch` flag and reflect the hollow-marker set honestly (per spec §2 load-bearing note).

- [ ] **Step 7: Fix the section titles** — cell 17 title string `'2026 Qualifying, first 4 rounds'` and `plot_category_deltas` title in `src/plotting.py:66` say "first 4 rounds"; update both to "first 5 rounds". (The plotting.py title change is a one-line edit — commit it with this task.)

- [ ] **Step 8: Re-run the notebook end to end and regenerate figures**

Run:
```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_antonelli_vs_russell.ipynb --ExecutePreprocessor.timeout=600
```
Expected: executes without error; `figures/headline_segment_delta.png`, `lap_delta_by_round.png`, `track_delta_map.png`, `year_over_year.png`, `corner_buckets.png` are regenerated with R5 data.

- [ ] **Step 9: Verify the figures changed**

Run: `git status --short figures/`
Expected: the five qualifying figures show as modified.

- [ ] **Step 10: Regenerate notebook 01 PDFs**

Run:
```bash
python -m jupyter nbconvert --to pdf notebooks/01_antonelli_vs_russell.ipynb
python -m jupyter nbconvert --to pdf --no-input --output 01_antonelli_vs_russell_no_code notebooks/01_antonelli_vs_russell.ipynb
```
Expected: `notebooks/01_antonelli_vs_russell.pdf` and `notebooks/01_antonelli_vs_russell_no_code.pdf` refreshed. (If `--to pdf` fails for lack of LaTeX, fall back to the project's existing PDF route — check how the current PDFs were produced, e.g. an `nbconvert --to webpdf` or a print-to-PDF step — and match it.)

- [ ] **Step 11: Commit**

```bash
git add notebooks/01_antonelli_vs_russell.ipynb notebooks/01_antonelli_vs_russell.pdf notebooks/01_antonelli_vs_russell_no_code.pdf src/plotting.py figures/
git commit -m "feat: add Canada (R5) to qualifying chapter; correct monotone-trend prose"
```

---

## Chunk 5: notebook 02 — the race chapters

### Task 12: Create `notebooks/02_how_antonelli_wins_races.ipynb`

**Files:**
- Create: `notebooks/02_how_antonelli_wins_races.ipynb`

Build the notebook cell by cell, following notebook 01's voice (question → method → finding → caveat). Use the same import/`setup_cache('../fastf1_cache')`/`RACES` header pattern. After authoring, execute it to render outputs and figures.

- [ ] **Step 1: Header + setup cell**

```python
import sys; sys.path.insert(0, '..')
import pandas as pd
import matplotlib.pyplot as plt
from src.loaders import setup_cache
from src import race
from src.plotting import (plot_start_conversion, plot_stint_pace,
                          plot_gap_trace, plot_tire_deg)
setup_cache('../fastf1_cache')
RACES = ['Australia', 'China', 'Japan', 'Miami', 'Canada']
```

- [ ] **Step 2: Intro markdown** — the reframe in miniature: ANT won 4 of the last 4 (China/Japan/Miami/Canada), lost only Australia. Qualifying (notebook 01) explains grid; this notebook asks how grids become wins. State the sign convention (positive = ANT better) and the teammate-control + P2-field framing.

- [ ] **Step 3: Results table cell** — build a per-race dict of start summaries (keyed by the `RACES` input name, so downstream cells can look up each race's P2 code *exactly* — never by fuzzy string match on the EventName), then display the ANT grid/finish table for all 5 races:

```python
# Keyed by the RACES input string ('China', 'Canada', ...) — NOT by EventName,
# so the P2 field reference can be looked up exactly in the pace cell below.
starts = {r: race.start_summary(2026, r) for r in RACES}
start = pd.concat(starts.values(), ignore_index=True)
start[start['driver'] == 'ANT'][['race','grid','lap1_pos','positions_gained','finish','status']]
```

- [ ] **Step 4: Chapter A — Start & lap 1**

```python
fig = plot_start_conversion(start, save_path='../figures/start_conversion.png'); plt.show()
```
Markdown after: Canada is the centerpiece (P2 → led by L2 → win); Australia is the honest counter-case (P2 → P2, front-row pace wasn't enough to pass Russell — a finishing-position loss, **not** a start failure, per spec).

- [ ] **Step 5: Chapter B — Race pace & control**

```python
# Teammate pace + the per-race P2 finisher as field reference. The P2 code is
# read from the per-race start summary built in Step 3 (exact lookup, no fuzzy
# string matching — this is what fixes the China/Canada drop-out).
pace_frames = []
for r in RACES:
    p2_rows = starts[r][starts[r]['driver'] == 'P2']
    field = [p2_rows['code'].iloc[0]] if len(p2_rows) else []
    pace_frames.append(race.stint_pace(2026, r, ['ANT', 'RUS'] + field))
pace = pd.concat(pace_frames, ignore_index=True)
fig = plot_stint_pace(pace, save_path='../figures/stint_pace.png'); plt.show()
```

> **Note:** if a race's classified P2 finisher retired or has no clean stints, `stint_pace` simply returns no rows for that code — the chart shows the teammate pair for that race rather than erroring (spec §8 "no comparable stint"). That's the intended graceful degradation, not a bug.
Then the gap trace (use the wins, where "control" is the story):
```python
gap = pd.concat([race.gap_to_rival(2026, r, 'ANT') for r in ['China','Japan','Miami','Canada']], ignore_index=True)
fig = plot_gap_trace(gap, save_path='../figures/gap_trace.png'); plt.show()
```
Markdown: pulled away vs managed/inherited; name the fuel/traffic caveat on raw medians; Canada's control was partly inherited (Russell DNF).

- [ ] **Step 6: Chapter C — Tire degradation**

```python
deg = pd.concat([race.tire_deg(2026, r, ['ANT', 'RUS']) for r in RACES], ignore_index=True)
fig = plot_tire_deg(deg, save_path='../figures/tire_deg.png'); plt.show()
deg  # show the table incl. NaN small-n stints
```
Markdown: interpret only comparable same-compound stints; name the fuel-burn caveat (uncorrected); note small-n stints reported as NaN, not zero.

- [ ] **Step 7: Honest accounting + caveats markdown** — Russell's Canada DNF named plainly (a win partly inherited); 5-race sample; SC/VSC laps excluded; no fuel/track-evolution correction; the three race mechanisms have even thinner data than qualifying.

- [ ] **Step 8: Closing markdown** — synthesise: qualifying gets him to the front (usually), he converts starts and controls races when he leads, tire management is [whatever the data shows] — and the YoY rookie-arc compression (notebook 01) remains the most durable signal.

- [ ] **Step 9: Execute the notebook**

Run:
```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/02_how_antonelli_wins_races.ipynb --ExecutePreprocessor.timeout=600
```
Expected: executes cleanly; the 4 race figures are written/overwritten.

- [ ] **Step 10: Export PDFs (match notebook 01's route)**

```bash
python -m jupyter nbconvert --to pdf notebooks/02_how_antonelli_wins_races.ipynb
python -m jupyter nbconvert --to pdf --no-input --output 02_how_antonelli_wins_races_no_code notebooks/02_how_antonelli_wins_races.ipynb
```
Expected: with-code and no-code PDFs created. (Same LaTeX/webpdf fallback note as Task 11 Step 10.)

- [ ] **Step 11: Commit**

```bash
git add notebooks/02_how_antonelli_wins_races.ipynb notebooks/02_how_antonelli_wins_races*.pdf figures/
git commit -m "feat: add notebook 02 — how Antonelli wins races (start/pace/tire)"
```

---

## Chunk 6: README reframe + case study refresh

### Task 13: Reframe `README.md` around winning

**Files:**
- Modify: `README.md`

- [ ] **Step 1: New title + opening** — change the H1 from "Antonelli vs Russell: A Segment-Level Look at the 2026 Mercedes Drivers" to a winning-framed title (finalize wording, e.g. "How Kimi Antonelli Keeps Winning — A Data Look at the 2026 Mercedes Driver"). New opening: the 4-of-5 win fact, and the structure (Chapter 1 qualifying = notebook 01; race analysis = notebook 02).

- [ ] **Step 2: New headline-findings section** — lead with the race record table (grid/finish, 5 races). Then the three race mechanisms (start conversion, pace/control, tire) each as a 1-3 sentence finding with its figure inlined (`figures/start_conversion.png`, `stint_pace.png`, `gap_trace.png`, `tire_deg.png`).

- [ ] **Step 3: Demote qualifying to "Chapter 1"** — keep the existing qualifying findings but updated to 5-race numbers and re-titled as the "get to the front" chapter. Carry over the corrected numbers (see table below). Explicitly state the monotone trend broke at Canada.

- [ ] **Step 4: Update every hard-coded "four"/"4 rounds"/"first four" → five**, and replace the monotone-trajectory bullet with the honest version. Update the YoY bullet to +0.51 s/track over 5 tracks.

- [ ] **Step 5: Honest accounting / limitations** — add Russell's Canada DNF; keep the Japan sensor section; add that the race chapters are a thinner 5-race sample with no fuel/strategy correction.

- [ ] **Step 6: Update "Method" and any figure links** — ensure all inlined figure paths resolve and the method section mentions both qualifying (fastest valid lap) and race (clean green-flag laps, `TrackStatus=='1'`) data.

**Numbers to carry into the README (verify against the freshly executed notebooks, do not trust these blindly):**

| Quantity | Value |
|---|---|
| Race record | Won China/Japan/Miami/Canada; P2 Australia (4 of 5) |
| Qualifying 5-race mean lap Δ | +0.11 s (ANT faster) |
| Qualifying trajectory | R1 −0.29 → R2 +0.22 → R3 +0.30 → R4 +0.40 → R5 −0.07 (not monotone) |
| Segment categories (5 races) | straight +0.005, slow −0.001, fast −0.003, medium −0.014 |
| YoY mean gain (5 tracks) | +0.51 s/track, range 0.29–0.69, Canada +0.42 |
| Corner-cycle fast signature | unchanged, 12 pts (Canada added none) |

- [ ] **Step 7: Verify all figure links resolve**

Run: `grep -o "figures/[A-Za-z_]*\.png" README.md | sort -u | while read f; do test -f "$f" && echo "OK $f" || echo "MISSING $f"; done`
Expected: every referenced figure prints `OK`.

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs: reframe README around how Antonelli wins races (5 rounds)"
```

### Task 14: Refresh `case_study.pdf`

**Files:**
- Modify: `case_study.pdf`

- [ ] **Step 1: Determine how the current case_study.pdf is produced** — check recent commits / docs for the generation route (it may be an export of the README or a dedicated notebook). Match that route.

Run: `git log --oneline -- case_study.pdf | head`

- [ ] **Step 2: Regenerate** the one-page case study using that same route, reflecting the new winning framing and 5-race numbers.

- [ ] **Step 3: Eyeball the PDF** — open and confirm it reflects the reframe (title, 4-of-5 wins, updated numbers), no stale "four rounds" text.

- [ ] **Step 4: Commit**

```bash
git add case_study.pdf
git commit -m "docs: refresh case study PDF for race-winning reframe"
```

---

## Final verification

- [ ] **Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests in `tests/test_segments.py` and `tests/test_race.py` PASS.

- [ ] **Grep for stale "four rounds" language across deliverables**

Run: `grep -rin "four round\|first 4\|first four\|4 rounds\|monotone" README.md notebooks/*.ipynb`
Expected: no stale monotone/four-rounds claims remain (any "monotone" mention should be in the "did NOT continue / broke at Canada" context).

- [ ] **Confirm all expected figures exist**

Run: `ls figures/start_conversion.png figures/stint_pace.png figures/gap_trace.png figures/tire_deg.png figures/headline_segment_delta.png figures/lap_delta_by_round.png figures/track_delta_map.png figures/year_over_year.png figures/corner_buckets.png`
Expected: all present.

- [ ] **Use superpowers:requesting-code-review** to review the whole branch before finishing.

- [ ] **Use superpowers:finishing-a-development-branch** to decide on merge / PR.
