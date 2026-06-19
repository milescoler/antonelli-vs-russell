# Lap-Decomposition Data Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the per-matchup decomposition JSON (hero + full teammate×race matrix, with honest exclusion) that the web flagship consumes, by parameterizing the existing decomposition core and adding a build step — without changing any statistical method.

**Architecture:** Extract a parameterized entry from the sub-project's `run.py` so any (race, driver pair) can be analyzed without editing `config.py`. Add pure, testable export helpers in a new `src/web_export.py` (teammate-pair derivation, `res`→JSON payload, index builder). A new `scripts/build_decomp_data.py` orchestrates: read the already-built `season.json` for round/slug identity, loop races × teammate pairs, call the core, write `web/public/data/decomp/index.json` + per-matchup files, recording failures as honest exclusions.

**Tech Stack:** Python 3.12, FastF1 3.8.x, numpy, pandas, pytest. No new dependencies.

## Global Constraints

- Sign convention everywhere: `delta = t(DRIVER_A) − t(DRIVER_B)`; positive ⇒ A slower ⇒ B faster. (verbatim from `config.py`)
- No new statistical methods — reuse the existing `decompose`/`bootstrap`/`reconcile` core unchanged. Tuning constants (`GRID_RESOLUTION_M`, `N_BOOTSTRAP=5000`, `CONFIDENCE=0.95`, `RANDOM_SEED=20240619`, `RECONCILE_TOLERANCE_S=0.05`, `N_MICRO_SECTORS=20`, `N_KEY_SECTORS=3`) stay in `config.py`.
- matplotlib plotting (`plotting.py`, `write_outputs`) is untouched and remains for the standalone CLI/report only.
- JSON is deterministic: sorted keys, fixed rounding, NaN/inf → `null` (mirror `scripts/build_site_data.py`'s `_canonical` + `write_json_if_changed`).
- Honest exclusion: a matchup that fails (no clean lap / reconciliation residual > tolerance / load error) is recorded in `index.json` with a human reason, never silently dropped.
- The sub-project package is imported via a `sys.path` shim pointing at `f1-performance-decomposition/`; the build script does NOT import the main repo's `src/` (it reads `season.json` for round identity instead), avoiding the dual-`src`/`config` name collision.
- All existing invariant tests in `f1-performance-decomposition/tests/test_pipeline.py` MUST stay green.

Paths in this plan are relative to repo root `/Users/mcoler/Documents/project-folder/f1_project`. The sub-project root is `f1-performance-decomposition/`; inside it the package is `src/` and tests run from the sub-project root (that is where `config.py` and `import config` resolve).

---

### Task 1: Parameterize the decomposition core

Make `run_pipeline` accept an explicit matchup (year, gp, session, driver_a, driver_b) instead of only reading `config`, so the build can call it per pair. Defaults preserve the existing CLI behavior.

**Files:**
- Modify: `f1-performance-decomposition/src/run.py` (`gather_inputs`, `run_pipeline`, `_findings_markdown`)
- Test: `f1-performance-decomposition/tests/test_pipeline.py` (add one test)

**Interfaces:**
- Produces:
  - `gather_inputs(use_synthetic: bool, *, year=None, gp=None, session=None, driver_a=None, driver_b=None) -> tuple[DriverLaps, DriverLaps, np.ndarray|None, str]`
  - `run_pipeline(use_synthetic: bool = False, *, year=None, gp=None, session=None, driver_a=None, driver_b=None) -> dict` — same `res` dict as today, now also carrying `res["driver_a"]`, `res["driver_b"]`.

- [ ] **Step 1: Write the failing test**

Add to `f1-performance-decomposition/tests/test_pipeline.py`:

```python
def test_run_pipeline_accepts_explicit_drivers():
    # Synthetic fixture, but driven by explicit codes rather than config defaults.
    res = run.run_pipeline(use_synthetic=True, driver_a="LEC", driver_b="HAM")
    assert res["driver_a"] == "LEC" and res["driver_b"] == "HAM"
    # Still reconciles (correctness gate) and attributes to the passed codes.
    assert abs(res["residual"]) <= config.RECONCILE_TOLERANCE_S
    if len(res["attrib"]):
        narr = " ".join(res["attrib"]["narrative"].tolist())
        assert ("LEC" in narr) or ("HAM" in narr)
```

Ensure the test module imports `run` and `config` (it already imports the pipeline; add `from src import run` / `import config` if absent).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_pipeline.py::test_run_pipeline_accepts_explicit_drivers -v`
Expected: FAIL — `run_pipeline()` got an unexpected keyword argument `driver_a` (or `res["driver_a"]` KeyError).

- [ ] **Step 3: Implement the parameterization**

In `f1-performance-decomposition/src/run.py`, replace `gather_inputs` and the head/attribution/return of `run_pipeline`:

```python
def gather_inputs(use_synthetic: bool, *, year=None, gp=None, session=None,
                  driver_a=None, driver_b=None):
    """Return (laps_a, laps_b, corner_distances, label)."""
    da = driver_a or config.DRIVER_A
    db = driver_b or config.DRIVER_B
    if use_synthetic:
        from src import synthetic
        a, b = synthetic.load_drivers(driver_a=da, driver_b=db)
        return a, b, synthetic.corner_distances(), "SYNTHETIC FIXTURE"
    session_obj = data_loading.load_session(year, gp, session)
    a = data_loading.select_clean_laps(session_obj, da)
    b = data_loading.select_clean_laps(session_obj, db)
    cd = _corner_distances_from_session(session_obj)
    label = f"{year or config.YEAR} {gp or config.GRAND_PRIX} {session or config.SESSION}"
    return a, b, cd, label


def run_pipeline(use_synthetic: bool = False, *, year=None, gp=None, session=None,
                 driver_a=None, driver_b=None) -> dict:
    da = driver_a or config.DRIVER_A
    db = driver_b or config.DRIVER_B
    laps_a, laps_b, corner_distances, label = gather_inputs(
        use_synthetic, year=year, gp=gp, session=session, driver_a=da, driver_b=db)
    if not laps_a.laps or not laps_b.laps:
        raise RuntimeError("No clean laps for one of the drivers - cannot decompose.")
    # ... existing body unchanged through `top = stats.top_significant_sectors(table)` ...
```

Then change the attribution call and the `return dict(...)` to thread the codes:

```python
    attrib = attribution.attribute(top, repr_a, repr_b, da, db) if len(top) else pd.DataFrame()

    return dict(
        label=label, use_synthetic=use_synthetic,
        driver_a=da, driver_b=db,
        grid=g, delta=dlt, edges=edges, corner_distances=corner_distances,
        decomp=decomp, table=table, top=top, attrib=attrib,
        repr_a=repr_a, repr_b=repr_b,
        official_gap=official_gap, endpoint=float(dlt[-1]), residual=residual,
        n_laps_a=len(laps_a.laps), n_laps_b=len(laps_b.laps),
        fastest_a=fa.lap_time, fastest_b=fb.lap_time,
    )
```

In `_findings_markdown`, change the first two lines from `a, b = config.DRIVER_A, config.DRIVER_B` to `a, b = res["driver_a"], res["driver_b"]` so the CLI report stays correct under explicit codes. `main()` is unchanged (it calls `run_pipeline()` with defaults).

- [ ] **Step 4: Run the new test and the full suite**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_pipeline.py -v`
Expected: PASS — the new test passes and all pre-existing invariant tests stay green.

- [ ] **Step 5: Commit**

```bash
git add f1-performance-decomposition/src/run.py f1-performance-decomposition/tests/test_pipeline.py
git commit -m "refactor(decomp): parameterize run_pipeline by matchup, keep config defaults"
```

---

### Task 2: Teammate-pair derivation

A pure function that, given a session results table, returns the teammate pairs to decompose (teams with exactly two classified drivers), ordered deterministically (better grid position = A).

**Files:**
- Create: `f1-performance-decomposition/src/web_export.py`
- Test: `f1-performance-decomposition/tests/test_web_export.py`

**Interfaces:**
- Produces: `teammate_pairs(results: pd.DataFrame) -> list[dict]` where each dict is
  `{"team": str, "teamColor": str|None, "a": str, "b": str}` (a = better/lower grid position).
  Input is a FastF1 `session.results`-shaped frame with columns `Abbreviation, TeamName, TeamColor, GridPosition` (or `Position`).

- [ ] **Step 1: Write the failing test**

Create `f1-performance-decomposition/tests/test_web_export.py`:

```python
import pandas as pd
from src import web_export


def _results():
    return pd.DataFrame([
        {"Abbreviation": "RUS", "TeamName": "Mercedes", "TeamColor": "27F4D2", "GridPosition": 1},
        {"Abbreviation": "ANT", "TeamName": "Mercedes", "TeamColor": "27F4D2", "GridPosition": 2},
        {"Abbreviation": "NOR", "TeamName": "McLaren",  "TeamColor": "FF8000", "GridPosition": 3},
        {"Abbreviation": "PIA", "TeamName": "McLaren",  "TeamColor": "FF8000", "GridPosition": 5},
        {"Abbreviation": "VER", "TeamName": "Red Bull", "TeamColor": "3671C6", "GridPosition": 4},
        # Red Bull second car DNS / not classified -> single driver, excluded as a pair.
    ])


def test_teammate_pairs_groups_by_team_and_orders_by_grid():
    pairs = web_export.teammate_pairs(_results())
    keys = {(p["team"], p["a"], p["b"]) for p in pairs}
    assert ("Mercedes", "RUS", "ANT") in keys      # RUS grid 1 < ANT grid 2 -> A=RUS
    assert ("McLaren", "NOR", "PIA") in keys
    # Single-car team yields no pair.
    assert all(p["team"] != "Red Bull" for p in pairs)
    # Color is hex-prefixed.
    merc = next(p for p in pairs if p["team"] == "Mercedes")
    assert merc["teamColor"] == "#27F4D2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py::test_teammate_pairs_groups_by_team_and_orders_by_grid -v`
Expected: FAIL — `ModuleNotFoundError: src.web_export` (module not yet created).

- [ ] **Step 3: Implement `teammate_pairs`**

Create `f1-performance-decomposition/src/web_export.py`:

```python
"""Export the decomposition `res` dict to the web JSON contract, and derive the
teammate matchups to run. Pure functions only — no FastF1, no file IO — so they
are unit-tested offline. The build script (scripts/build_decomp_data.py) does the
IO and calls these.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _hex(color) -> str | None:
    if isinstance(color, str) and color:
        return color if color.startswith("#") else f"#{color}"
    return None


def teammate_pairs(results: pd.DataFrame) -> list[dict]:
    """Teams with exactly two classified drivers -> one pair each.

    A is the better-placed driver (lower GridPosition; falls back to Position,
    then to alphabetical) so the ordering is deterministic.
    """
    rank_col = "GridPosition" if "GridPosition" in results.columns else (
        "Position" if "Position" in results.columns else None)
    pairs: list[dict] = []
    for team, grp in results.groupby("TeamName", sort=True):
        codes = [str(c) for c in grp["Abbreviation"].tolist()]
        if len(codes) != 2:
            continue
        if rank_col is not None:
            grp = grp.sort_values(rank_col, kind="stable")
        else:
            grp = grp.sort_values("Abbreviation", kind="stable")
        a, b = (str(grp.iloc[0]["Abbreviation"]), str(grp.iloc[1]["Abbreviation"]))
        pairs.append({
            "team": str(team),
            "teamColor": _hex(grp.iloc[0].get("TeamColor")),
            "a": a, "b": b,
        })
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add f1-performance-decomposition/src/web_export.py f1-performance-decomposition/tests/test_web_export.py
git commit -m "feat(decomp): derive teammate pairs from session results"
```

---

### Task 3: `res` → matchup JSON payload

A pure function turning a `run_pipeline` `res` dict + race metadata into the per-matchup JSON payload (downsampled curve/track, sector table, attribution, callouts).

**Files:**
- Modify: `f1-performance-decomposition/src/web_export.py`
- Test: `f1-performance-decomposition/tests/test_web_export.py` (add)

**Interfaces:**
- Consumes: `res` from `run.run_pipeline` (Task 1); `race_meta = {"slug","eventName","round","year","session","driverAName","driverBName","team","teamColor"}`.
- Produces: `matchup_payload(res: dict, race_meta: dict, *, max_points: int = 200) -> dict` matching the spec schema (`meta, deltaCurve, corners, sectors, attribution, callouts, track`).

- [ ] **Step 1: Write the failing test**

Add to `f1-performance-decomposition/tests/test_web_export.py`:

```python
from src import run
import config


def test_matchup_payload_shape_and_reconciliation():
    res = run.run_pipeline(use_synthetic=True, driver_a="RUS", driver_b="ANT")
    meta = {"slug": "canadian", "eventName": "Synthetic GP", "round": 5,
            "year": config.YEAR, "session": "Q",
            "driverAName": "George Russell", "driverBName": "Kimi Antonelli",
            "team": "Mercedes", "teamColor": "#27F4D2"}
    p = web_export.matchup_payload(res, meta, max_points=120)

    # meta echoes identity + reconciles
    assert p["meta"]["driverA"]["code"] == "RUS"
    assert p["meta"]["driverB"]["code"] == "ANT"
    assert abs(p["meta"]["reconResidualS"]) <= config.RECONCILE_TOLERANCE_S
    # curve is downsampled, ends at the official gap, starts at 0
    assert len(p["deltaCurve"]) <= 120
    assert p["deltaCurve"][0]["delta"] == 0.0
    assert abs(p["deltaCurve"][-1]["delta"] - p["meta"]["officialGapS"]) <= config.RECONCILE_TOLERANCE_S
    # one sector row per micro-sector, each carries a CI + significance flag
    assert len(p["sectors"]) == len(res["table"])
    s0 = p["sectors"][0]
    assert {"i", "midM", "deltaMean", "ciLow", "ciHigh", "significant"} <= set(s0)
    # callouts: noiseTrap is None or an int sector id; topSignificant is a list
    assert isinstance(p["callouts"]["topSignificant"], list)
    # track points carry x/y/rate
    assert {"x", "y", "rate"} <= set(p["track"][0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py::test_matchup_payload_shape_and_reconciliation -v`
Expected: FAIL — `module 'src.web_export' has no attribute 'matchup_payload'`.

- [ ] **Step 3: Implement `matchup_payload` (+ number helpers + downsampler)**

Append to `f1-performance-decomposition/src/web_export.py`:

```python
def _num(x, n: int = 4):
    """Round to n decimals; NaN/inf/None -> None (JSON null)."""
    if x is None:
        return None
    try:
        fx = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(fx) or math.isinf(fx)) else round(fx, n)


def _downsample_idx(n: int, max_points: int) -> list[int]:
    if n <= max_points:
        return list(range(n))
    step = max(1, n // max_points)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)          # always pin the finish line
    return idx


def _corner_labels(corner_distances) -> list[dict]:
    if corner_distances is None:
        return []
    cd = np.sort(np.asarray(corner_distances, dtype=float))
    return [{"d": _num(d, 1), "label": f"T{i + 1}"} for i, d in enumerate(cd)]


def matchup_payload(res: dict, race_meta: dict, *, max_points: int = 200) -> dict:
    grid = np.asarray(res["grid"], dtype=float)
    delta = np.asarray(res["delta"], dtype=float)
    repr_a = res["repr_a"]
    rate = np.gradient(delta, grid)             # s per m: slope of the curve

    ci = _downsample_idx(len(grid), max_points)
    delta_curve = [{"d": _num(grid[i], 1), "delta": _num(delta[i], 4)} for i in ci]
    track = [{"x": _num(repr_a["X"].to_numpy()[i], 1),
              "y": _num(repr_a["Y"].to_numpy()[i], 1),
              "rate": _num(rate[i], 6)} for i in ci]

    sectors = [{
        "i": int(r["sector"]),
        "startM": _num(r["start_m"], 1), "endM": _num(r["end_m"], 1),
        "midM": _num(r["mid_m"], 1),
        "deltaMean": _num(r["delta_s_mean"], 4),
        "ciLow": _num(r["ci_low"], 4), "ciHigh": _num(r["ci_high"], 4),
        "significant": bool(r["significant"]),
        "faster": (None if not np.isfinite(r["delta_s_mean"])
                   else (res["driver_a"] if r["delta_s_mean"] > 0 else res["driver_b"])),
    } for _, r in res["table"].sort_values("sector").iterrows()]
    # note: delta = t_A - t_B, so deltaMean > 0 => A slower => B faster in that sector.

    attribution = [{
        "sector": int(r["sector"]),
        "driverFaster": str(r["faster_driver"]),
        "deltaS": _num(r["delta_s"], 4),
        "significant": bool(r["significant"]),
        "narrative": str(r["narrative"]),
    } for _, r in res["attrib"].iterrows()] if len(res["attrib"]) else []

    table = res["table"]
    noise = table[~table["significant"]]
    callouts = {
        "topSignificant": [int(s) for s in res["top"]["sector"].tolist()] if len(res["top"]) else [],
        "noiseTrap": (int(noise.iloc[0]["sector"]) if len(noise) else None),
    }

    return {
        "meta": {
            "race": race_meta["slug"], "eventName": race_meta["eventName"],
            "round": int(race_meta["round"]), "year": int(race_meta["year"]),
            "session": race_meta["session"],
            "driverA": {"code": res["driver_a"], "name": race_meta["driverAName"],
                        "team": race_meta["team"], "color": race_meta["teamColor"]},
            "driverB": {"code": res["driver_b"], "name": race_meta["driverBName"],
                        "team": race_meta["team"], "color": race_meta["teamColor"]},
            "officialGapS": _num(res["official_gap"], 3),
            "reconResidualS": _num(res["residual"], 4),
            "nCleanLapsA": int(res["n_laps_a"]), "nCleanLapsB": int(res["n_laps_b"]),
        },
        "deltaCurve": delta_curve,
        "corners": _corner_labels(res["corner_distances"]),
        "sectors": sectors,
        "attribution": attribution,
        "callouts": callouts,
        "track": track,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add f1-performance-decomposition/src/web_export.py f1-performance-decomposition/tests/test_web_export.py
git commit -m "feat(decomp): serialize a matchup to the web JSON payload"
```

---

### Task 4: Index builder with honest exclusion

A pure function assembling `index.json`: hero key, race list, and every matchup tagged valid (with headline stats) or excluded (with a reason).

**Files:**
- Modify: `f1-performance-decomposition/src/web_export.py`
- Test: `f1-performance-decomposition/tests/test_web_export.py` (add)

**Interfaces:**
- Produces:
  - `matchup_key(slug: str, a: str, b: str) -> str` → `f"{slug}__{a}_{b}"`
  - `build_index(hero_key: str, races: list[dict], entries: list[dict]) -> dict`. Each `entry` is either
    `{"key","race","team","teamColor","a","b","valid":True,"officialGapS","significantCount"}`
    or `{"key","race","team","teamColor","a","b","valid":False,"reason"}`.

- [ ] **Step 1: Write the failing test**

Add to `f1-performance-decomposition/tests/test_web_export.py`:

```python
def test_build_index_separates_valid_and_excluded():
    races = [{"slug": "canadian", "name": "Canadian Grand Prix", "round": 5}]
    entries = [
        {"key": "canadian__RUS_ANT", "race": "canadian", "team": "Mercedes",
         "teamColor": "#27F4D2", "a": "RUS", "b": "ANT",
         "valid": True, "officialGapS": -0.07, "significantCount": 3},
        {"key": "barcelona__RUS_ANT", "race": "barcelona", "team": "Mercedes",
         "teamColor": "#27F4D2", "a": "RUS", "b": "ANT",
         "valid": False, "reason": "No clean laps for one of the drivers"},
    ]
    idx = web_export.build_index("canadian__RUS_ANT", races, entries)
    assert idx["hero"] == "canadian__RUS_ANT"
    assert idx["matchups"][0]["key"] == "barcelona__RUS_ANT"   # sorted by key
    excluded = [m for m in idx["matchups"] if not m["valid"]]
    assert excluded and "reason" in excluded[0]


def test_matchup_key():
    assert web_export.matchup_key("canadian", "RUS", "ANT") == "canadian__RUS_ANT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py -k "index or matchup_key" -v`
Expected: FAIL — `web_export` has no attribute `build_index` / `matchup_key`.

- [ ] **Step 3: Implement**

Append to `f1-performance-decomposition/src/web_export.py`:

```python
def matchup_key(slug: str, a: str, b: str) -> str:
    return f"{slug}__{a}_{b}"


def build_index(hero_key: str, races: list[dict], entries: list[dict]) -> dict:
    return {
        "hero": hero_key,
        "races": sorted(races, key=lambda r: r["round"]),
        "matchups": sorted(entries, key=lambda e: e["key"]),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py -v`
Expected: PASS (all web_export tests).

- [ ] **Step 5: Commit**

```bash
git add f1-performance-decomposition/src/web_export.py f1-performance-decomposition/tests/test_web_export.py
git commit -m "feat(decomp): build the matchup index with honest exclusion"
```

---

### Task 5: Build script orchestration (`scripts/build_decomp_data.py`)

The IO layer: read `season.json` for round identity, loop races × teammate pairs, call the core, write JSON, record exclusions. Includes a `--synthetic` smoke mode that runs one matchup from the fixture (no network) so the wiring is testable offline.

**Files:**
- Create: `scripts/build_decomp_data.py`
- Test: `f1-performance-decomposition/tests/test_web_export.py` (add an offline integration test invoking the script's `build_synthetic_demo`)

**Interfaces:**
- Consumes: `run.run_pipeline` (Task 1); `web_export.*` (Tasks 2–4).
- Produces (importable from the script for testing):
  - `build_synthetic_demo(out_dir: Path) -> Path` — writes `index.json` + one hero matchup file from the synthetic fixture; returns `out_dir`. (No FastF1.)
  - `main()` — the live build (reads `season.json`, hits FastF1).

- [ ] **Step 1: Write the failing test**

Add to `f1-performance-decomposition/tests/test_web_export.py`:

```python
import json
from pathlib import Path
import importlib.util


def _load_build_script():
    # Import scripts/build_decomp_data.py by path (it lives outside the package).
    repo_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "build_decomp_data", repo_root / "scripts" / "build_decomp_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_synthetic_demo_writes_valid_json(tmp_path):
    build = _load_build_script()
    build.build_synthetic_demo(tmp_path)

    index = json.loads((tmp_path / "index.json").read_text())
    assert index["hero"] in {m["key"] for m in index["matchups"]}
    hero = next(m for m in index["matchups"] if m["key"] == index["hero"])
    assert hero["valid"] is True

    payload = json.loads((tmp_path / f"{index['hero']}.json").read_text())
    assert payload["deltaCurve"][0]["delta"] == 0.0
    assert "sectors" in payload and "callouts" in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py::test_synthetic_demo_writes_valid_json -v`
Expected: FAIL — `scripts/build_decomp_data.py` does not exist.

- [ ] **Step 3: Implement the build script**

Create `scripts/build_decomp_data.py`:

```python
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
    import data_loading_guard  # noqa: F401  (placeholder import removed below)
```

Now replace that final placeholder `if args.synthetic` tail with the real live build body:

```python
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
```

When writing the file, do NOT include the `import data_loading_guard` placeholder line — it is only marking where the live body goes; the file should contain `build_synthetic_demo`, then a `main()` whose body is `if args.synthetic: ... return` followed directly by the live build block above.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd f1-performance-decomposition && python -m pytest tests/test_web_export.py::test_synthetic_demo_writes_valid_json -v`
Expected: PASS — the synthetic demo writes a valid `index.json` + hero payload to `tmp_path`.

Also run the whole sub-project suite to confirm nothing regressed:
Run: `cd f1-performance-decomposition && python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_decomp_data.py f1-performance-decomposition/tests/test_web_export.py
git commit -m "feat: build_decomp_data writes per-matchup JSON + honest-exclusion index"
```

---

### Task 6: Generate real data, wire CI, populate the report

Produce the real JSON locally if FastF1 is reachable (else rely on CI), wire the build into the deploy workflow, and populate the sub-project REPORT.md stub.

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Generated (committed): `web/public/data/decomp/*.json`
- Modify: `f1-performance-decomposition/REPORT.md` (AUTOGEN block, via the CLI)

**Interfaces:** none (operational task).

- [ ] **Step 1: Probe FastF1 reachability**

Run: `cd f1-performance-decomposition && timeout 120 python -m src.run --no-report 2>&1 | tail -5`
Expected: either a successful reconciliation log (network OK) OR a connection error (network blocked).

- [ ] **Step 2: Generate data**

If network OK:
Run: `python scripts/build_decomp_data.py 2>&1 | tail -20`
Expected: per-matchup `ok`/`EXCLUDED` lines; files appear under `web/public/data/decomp/`.

If network blocked locally: skip — CI (Step 4) generates the real data. Generate the offline demo so the web build has *something* to render during development:
Run: `python scripts/build_decomp_data.py --synthetic`
Expected: `web/public/data/decomp/index.json` + one hero file written. (Mark these as demo; CI overwrites with real data.)

- [ ] **Step 3: Populate the standalone report**

If network OK: `cd f1-performance-decomposition && python -m src.run` (writes figures + injects REPORT.md findings).
If blocked: `cd f1-performance-decomposition && python -m src.run --synthetic` (clearly labels the findings as synthetic).
Expected: the AUTOGEN block in `f1-performance-decomposition/REPORT.md` is no longer the placeholder.

- [ ] **Step 4: Wire CI**

In `.github/workflows/deploy.yml`, immediately AFTER the existing `python scripts/build_site_data.py` step (so `season.json` exists first) and BEFORE the commit/build steps, add:

```yaml
      - name: Build decomposition data
        run: python scripts/build_decomp_data.py
```

Keep it in the same job, reusing the restored `fastf1_cache`. The existing "commit if changed" step will pick up `web/public/data/decomp/`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/deploy.yml web/public/data/decomp f1-performance-decomposition/REPORT.md
git commit -m "build: generate decomposition JSON, wire CI, populate report"
```

---

## Self-Review

- **Spec coverage:** parameterized core (Task 1) ✓; teammate-pair derivation (Task 2) ✓; per-matchup JSON matching the contract (Task 3) ✓; index + honest exclusion (Task 4) ✓; full-matrix build + offline smoke (Task 5) ✓; CI wiring + report population + real data (Task 6) ✓. The `web/public/data/decomp/` contract here is exactly what the Web plan consumes.
- **Placeholder scan:** the only literal placeholder is the intentionally-flagged `import data_loading_guard` marker in Task 5, with explicit instructions to omit it and what the real tail is. No other TBDs.
- **Type consistency:** `res` keys (`driver_a/driver_b/grid/delta/edges/corner_distances/table/top/attrib/repr_a/official_gap/residual/n_laps_a/n_laps_b`) match `run.py`. Table columns (`sector/start_m/end_m/mid_m/delta_s_mean/ci_low/ci_high/significant`) match `stats.assemble_sector_table`. Attribution columns (`sector/faster_driver/delta_s/significant/narrative`) match `attribution.attribute_sector`. `web_export` function names (`teammate_pairs/matchup_payload/matchup_key/build_index`) are consistent across tasks.

## Execution note
This plan is independently shippable: after Task 6 the repo emits validated decomposition JSON with green tests. The Web plan (`2026-06-18-lap-decomposition-web.md`) consumes `web/public/data/decomp/`.
