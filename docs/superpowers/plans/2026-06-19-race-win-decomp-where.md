# Race-Win Decomposition — Factor 1 "Where on Track" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace the `factors.where` placeholder with a real corner-level decomposition of where the winner built the gap over P2, computed honestly on **comparable race laps** (same compound, similar tyre age & fuel) with bootstrap CIs per micro-sector.

**Architecture:** The decomposition runs **inside the `f1-performance-decomposition` engine** (which already has race telemetry loading + resample/delta/decompose/bootstrap), as a new `src/race_where.py` with a CLI. The main `scripts/build_race_decomp_data.py` invokes it **via subprocess** per race and embeds the emitted JSON into `factors.where` — this isolates the engine's `src`/`config` from the main repo's `src`/`config` (they collide if imported into one process). Comparable-pair selection + paired bootstrap are the new analytical pieces; everything else reuses engine primitives.

**Tech Stack:** Python 3.12, FastF1 3.8.x, numpy, pandas, pytest. No new deps.

## Global Constraints
- Probe confirmed comparable pairs are abundant (Monaco 213 / Japan 221 / Miami 259 at: same `Compound`, `|ΔTyreLife|≤3`, `|ΔLapNumber|≤5`). Those are the selection tolerances (engine `config.py` constants).
- Sign convention: `delta = t(winner) − t(P2)`; on the curve, rising = P2 pulling ahead, falling = winner pulling ahead. A sector is "real" iff its 95% bootstrap CI excludes 0.
- Reuse engine primitives: `resampling.{common_grid,resample_lap,build_distance_grid}`, `delta.{cumulative_delta,micro_sector_edges,decompose,segment_times,time_at_distance,reconcile}`, `stats` percentile-CI logic, `attribution.attribute`, `web_export.{matchup_payload,_num,_downsample_idx,_corner_labels}`.
- Do NOT use the engine's `data_loading.select_clean_laps` (107% quicklap filter — wrong for race). Use a race clean-lap filter: green-flag whole lap (`TrackStatus=='1'`), not lap 1, not in/out (`PitInTime`/`PitOutTime` NaT), valid `LapTime`.
- Race telemetry is heavy: `session.load(telemetry=True)` once per race; per-lap `get_telemetry()`. The factor-1 build will be slow — that's expected.
- Honest `undetermined`/`insufficient`: if a matchup has <`MIN_PAIRS` comparable pairs, `factors.where.verdict = "insufficient"` with a plain reason (no forced curve).
- Output payload mirrors the existing `DecompMatchup` shape the frontend already renders (`deltaCurve`, `corners`, `sectors[]` with `ciLow/ciHigh/significant/faster`, `attribution[]`, `callouts`, `track[]`), so Plan 3's web reuses `DeltaCurve`/`SectorVerdict`/`DecompTrackMap`/`AttributionList` unchanged.

Engine dir: `f1-performance-decomposition/` (its package is `src/`, `config.py` at its root; tests run from there). Main repo root for the build script + subprocess wiring.

---

### Task 1: Reconciliation-artifact fix (per-driver) in the engine

Replace the single cross-driver endpoint reconcile (which spuriously rejects valid decompositions because `common_grid` truncates to the shorter lap) with per-driver telemetry-vs-official checks. Needed before race pairs (race laps vary more in measured length).

**Files:**
- Modify: `f1-performance-decomposition/src/delta.py` (add `reconcile_driver`)
- Modify: `f1-performance-decomposition/src/run.py` (use it)
- Test: `f1-performance-decomposition/tests/test_pipeline.py` (add)

**Interfaces:**
- Produces: `delta.reconcile_driver(resampled_lap, official_lap_time, tolerance=None) -> tuple[bool,float]` — checks the lap's own telemetry time at its own finish vs its own official lap time (the tail cancels because it's per-driver).

- [ ] **Step 1: failing test** — add to `tests/test_pipeline.py`:
```python
def test_reconcile_driver_passes_when_telemetry_matches_official():
    import numpy as np, pandas as pd
    from src import delta as d
    grid = np.linspace(0, 1000, 501)
    # telemetry time linear in distance: 0..40s over the lap
    lap = pd.DataFrame({"Distance": grid, "Time": np.linspace(0, 40.0, 501),
                        "Speed": np.full(501, 90.0)})
    ok, resid = d.reconcile_driver(lap, official_lap_time=40.0, tolerance=0.05)
    assert ok and abs(resid) <= 0.05
    bad, resid2 = d.reconcile_driver(lap, official_lap_time=41.0, tolerance=0.05)
    assert not bad
```
- [ ] **Step 2: run → fail** `cd f1-performance-decomposition && python -m pytest tests/test_pipeline.py::test_reconcile_driver_passes_when_telemetry_matches_official -v` → FAIL (no attr).
- [ ] **Step 3: implement** — add to `delta.py`:
```python
def reconcile_driver(resampled_lap, official_lap_time, tolerance=None):
    """Per-driver gate: the lap's own measured telemetry time at its own finish
    must match its own official lap time. Independent of the other driver, so the
    grid-truncation tail does not enter the residual."""
    import config
    tol = config.RECONCILE_TOLERANCE_S if tolerance is None else tolerance
    t = time_at_distance(resampled_lap)
    resid = float(t[-1] - official_lap_time)
    return abs(resid) <= tol, resid
```
- [ ] **Step 4: run → pass.** Then in `run.py::run_pipeline`, replace the single `reconcile(float(dlt[-1]), official_gap)` gate with two per-driver checks: `ok_a,_ = delta_mod.reconcile_driver(repr_a, fa.lap_time)` and same for b; raise only if either driver's own telemetry time disagrees with their own official time. Keep `residual = float(dlt[-1]) - official_gap` in the returned res for reporting (no longer a hard gate). Run the FULL engine suite: `cd f1-performance-decomposition && python -m pytest -q` → all pass.
- [ ] **Step 5: commit**
```bash
git add f1-performance-decomposition/src/delta.py f1-performance-decomposition/src/run.py f1-performance-decomposition/tests/test_pipeline.py
git commit -m "fix(engine): per-driver reconciliation (stops grid-truncation false rejections)"
```

---

### Task 2: Comparable-lap-pair selection (pure)

**Files:**
- Create: `f1-performance-decomposition/src/race_where.py`
- Test: `f1-performance-decomposition/tests/test_race_where.py`
- Modify: `f1-performance-decomposition/config.py` (add tolerances)

**Interfaces:**
- Produces: `comparable_pairs(winner_meta, p2_meta, *, age_tol, lap_tol) -> list[tuple[int,int]]` where each input is a list of dicts `{"idx","compound","tyre_life","lap_number"}` and the output is index pairs `(winner_idx, p2_idx)` meeting: same compound, `|Δtyre_life|≤age_tol`, `|Δlap_number|≤lap_tol`. Deterministic order.

- [ ] **Step 1: failing test** — `tests/test_race_where.py`:
```python
from src import race_where as rw

def _m(rows):  # rows = (idx, compound, tyre_life, lap_number)
    return [{"idx": i, "compound": c, "tyre_life": t, "lap_number": l} for i, c, t, l in rows]

def test_comparable_pairs_matches_compound_age_lap():
    w = _m([(0, "MEDIUM", 5, 10), (1, "SOFT", 3, 30)])
    p = _m([(0, "MEDIUM", 7, 12), (1, "HARD", 5, 11), (2, "SOFT", 20, 31)])
    pairs = rw.comparable_pairs(w, p, age_tol=3, lap_tol=5)
    assert (0, 0) in pairs          # MEDIUM, |5-7|=2<=3, |10-12|=2<=5
    assert (1, 2) not in pairs      # SOFT but |3-20|=17 age too far
    assert all(w[a]["compound"] == p[b]["compound"] for a, b in pairs)
```
- [ ] **Step 2: run → fail** (no module).
- [ ] **Step 3: implement** — `config.py`: add `COMPARABLE_AGE_TOL = 3`, `COMPARABLE_LAP_TOL = 5`, `MIN_COMPARABLE_PAIRS = 4`. `race_where.py`:
```python
"""Factor 1 for the race-win decomposition: where on track the winner built the
gap over P2, on COMPARABLE race laps (same compound, similar tyre age & fuel),
with per-sector bootstrap CIs. Runs in the engine namespace; emits JSON via CLI.
"""
from __future__ import annotations
import numpy as np
import config


def comparable_pairs(winner_meta, p2_meta, *, age_tol=None, lap_tol=None):
    age_tol = config.COMPARABLE_AGE_TOL if age_tol is None else age_tol
    lap_tol = config.COMPARABLE_LAP_TOL if lap_tol is None else lap_tol
    pairs = []
    for w in winner_meta:
        for p in p2_meta:
            if (w["compound"] == p["compound"]
                    and abs(w["tyre_life"] - p["tyre_life"]) <= age_tol
                    and abs(w["lap_number"] - p["lap_number"]) <= lap_tol):
                pairs.append((w["idx"], p["idx"]))
    return pairs
```
- [ ] **Step 4: run → pass.** - [ ] **Step 5: commit**
```bash
git add f1-performance-decomposition/src/race_where.py f1-performance-decomposition/src/config.py f1-performance-decomposition/tests/test_race_where.py
git commit -m "feat(engine): comparable race-lap pair selection"
```

---

### Task 3: Paired per-sector bootstrap (pure)

**Files:** Modify `f1-performance-decomposition/src/race_where.py`; Test `tests/test_race_where.py` (add).

**Interfaces:**
- Produces: `paired_sector_bootstrap(pair_deltas, *, n_boot=None, confidence=None, seed=None) -> list[dict]`. Input `pair_deltas` is an `(n_pairs, n_sectors)` array of per-pair per-sector deltas (winner−P2). Returns one dict per sector: `{"sector","deltaMean","ciLow","ciHigh","significant"}` — bootstrap resamples PAIR rows (preserving matching), 2.5/97.5 percentile CI, `significant = CI excludes 0`.

- [ ] **Step 1: failing test**:
```python
import numpy as np
def test_paired_bootstrap_flags_real_and_noise_sectors():
    rng = np.random.default_rng(0)
    n = 40
    s_real = -0.10 + 0.01 * rng.standard_normal(n)   # consistent winner gain
    s_noise = 0.0 + 0.10 * rng.standard_normal(n)     # centred on zero, wide
    mat = np.column_stack([s_real, s_noise])
    out = rw.paired_sector_bootstrap(mat, n_boot=2000, confidence=0.95, seed=1)
    assert out[0]["significant"] is True and out[0]["ciHigh"] < 0   # real winner gain
    assert out[1]["significant"] is False                           # noise straddles 0
```
- [ ] **Step 2: run → fail.**
- [ ] **Step 3: implement** — add to `race_where.py`:
```python
def paired_sector_bootstrap(pair_deltas, *, n_boot=None, confidence=None, seed=None):
    n_boot = config.N_BOOTSTRAP if n_boot is None else n_boot
    confidence = config.CONFIDENCE if confidence is None else confidence
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)
    mat = np.asarray(pair_deltas, dtype=float)
    n_pairs, n_sec = mat.shape
    point = mat.mean(axis=0)
    boot = np.empty((n_boot, n_sec))
    for k in range(n_boot):
        idx = rng.integers(0, n_pairs, size=n_pairs)   # resample PAIRS (matched)
        boot[k] = mat[idx].mean(axis=0)
    a = 1.0 - confidence
    lo = np.percentile(boot, 100 * a / 2, axis=0)
    hi = np.percentile(boot, 100 * (1 - a / 2), axis=0)
    sig = (lo > 0) | (hi < 0)
    return [{"sector": i + 1, "deltaMean": float(point[i]), "ciLow": float(lo[i]),
             "ciHigh": float(hi[i]), "significant": bool(sig[i])} for i in range(n_sec)]
```
- [ ] **Step 4: run → pass.** - [ ] **Step 5: commit** `git commit -m "feat(engine): paired per-sector bootstrap for comparable race laps"`.

---

### Task 4: Race comparable-lap loader + where-decomposition orchestration

**Files:** Modify `f1-performance-decomposition/src/race_where.py` (FastF1-touching + orchestration); Test: add a `--synthetic`-style guard test if feasible, else rely on the live run in Task 5.

**Interfaces:**
- Produces:
  - `load_race_laps(year, gp, winner, p2) -> tuple[list[Lap], list[Lap]]` — race session telemetry; per driver, the race-clean laps (green/no-lap1/no-pit/valid) as engine `data_loading.Lap` objects with `compound`/`tyre_life`/`lap_number` populated. (Reuse `data_loading._standardise_telemetry`, `data_loading.Lap`, and `enable_cache`; do NOT use `select_clean_laps`.)
  - `decompose_where(winner_laps, p2_laps, corner_distances) -> dict|None` — selects comparable pairs (Task 2); if `< MIN_COMPARABLE_PAIRS` → return `None`; else builds a shared grid (`build_distance_grid(min lap length over all used laps)`), resamples each used lap, computes per-pair per-sector deltas (`segment_times` on a corner-anchored `micro_sector_edges`), runs `paired_sector_bootstrap` (Task 3), forms the representative mean curve `delta(d)` over pairs, picks the largest-magnitude significant sectors, runs `attribution.attribute` on a representative comparable pair, and returns a `matchup_payload`-shaped dict (`meta.nPairs`, `deltaCurve`, `corners`, `sectors`, `attribution`, `callouts`, `track`).

- [ ] **Step 1:** Write a focused test that exercises `decompose_where` on a small **synthetic** set of `Lap` objects (build 6 winner + 6 P2 laps from `src.synthetic`-style fixtures sharing a compound/age so pairs form) and asserts the payload has `sectors` with CI fields and a `deltaCurve` whose last point ≈ mean pair gap. (If building synthetic `Lap`s is impractical, mark this task's verification as the Task-5 live run and note it; do not fake a passing test.)
- [ ] **Step 2–4:** Implement `load_race_laps` (race clean-lap filter + telemetry per lap → `Lap`) and `decompose_where` (orchestration above), reusing engine primitives. Key details: corner distances from `session.get_circuit_info().corners["Distance"]` (mirror `run._corner_distances_from_session`); per-pair delta = `cumulative_delta(resampled_w, resampled_p)`; per-sector via `decompose`/`segment_times`; `faster` per sector from sign of `deltaMean` (negative ⇒ winner). Verify the synthetic test passes (or the live run in Task 5).
- [ ] **Step 5: commit** `git commit -m "feat(engine): race comparable-lap loader + where-on-track decomposition"`.

---

### Task 5: CLI + wire factor 1 into the build (subprocess) + regenerate

**Files:**
- Modify: `f1-performance-decomposition/src/race_where.py` (add `main()` CLI)
- Modify: `scripts/build_race_decomp_data.py` (call the engine via subprocess; embed into `factors.where`)
- Test: `tests/test_race_win.py` (add: `where_factor_from_json` merges a sample engine payload into a `factors.where` block with a verdict)

**Interfaces:**
- Engine CLI: `python -m src.race_where --year 2026 --gp Monaco --a ANT --b HAM` (run from `f1-performance-decomposition/`) → prints the where-payload JSON to stdout (or `{"verdict":"insufficient","reason":...}` if `<MIN_COMPARABLE_PAIRS`). Exit 0 on both; non-zero only on hard error.
- Main build: `build_one_race` calls it via `subprocess.run([sys.executable, "-m", "src.race_where", ...], cwd=DECOMP_ROOT, capture_output=True, text=True)`, parses stdout JSON, and sets `factors.where = {**verdict_from_where(payload), "decomp": payload}` where `verdict_from_where` = `real` if any sector significant else `noise` (or `insufficient` if the payload says so). On subprocess failure → `factors.where` = `{"verdict":"insufficient","reason":<stderr tail>, "decomp":None}` (honest, non-fatal).

- [ ] **Step 1:** Add a pure `verdict_from_where(payload) -> dict` to `src/race_win.py` + a test (`real` when a sector is significant; `insufficient` when payload has `verdict:"insufficient"`). RED→GREEN.
- [ ] **Step 2:** Implement the engine CLI `main()` (argparse year/gp/a/b; calls `load_race_laps`+`decompose_where`; prints JSON; `insufficient` JSON when `None`).
- [ ] **Step 3:** Wire the subprocess call into `build_one_race`; replace the placeholder `factors.where`. Keep it non-fatal.
- [ ] **Step 4: regenerate + verify (real-data calibration gate):**
  `python scripts/build_race_decomp_data.py 2>&1 | tail -12` (SLOW — race telemetry). Then:
  `python3 -c "import json; d=json.load(open('web/public/data/race/monaco.json')); w=d['factors']['where']; print('monaco where verdict:', w['verdict'], '| nPairs:', (w.get('decomp') or {}).get('meta',{}).get('nPairs'), '| sig sectors:', sum(1 for s in (w.get('decomp') or {}).get('sectors',[]) if s['significant']))"`
  Expect Monaco `where` to be `real` with several comparable pairs and ≥1 significant sector. Spot-check 1–2 others. If a race has too few pairs it should read `insufficient` (honest), not crash. Sanity-check the per-driver reconciliation now lets most pairs through.
- [ ] **Step 5: commit** (engine + build script + tests + regenerated data):
```bash
git add f1-performance-decomposition/src/race_where.py scripts/build_race_decomp_data.py src/race_win.py tests/ web/public/data/race
git commit -m "feat: wire where-on-track factor 1 into the race-win build (subprocess)"
```

---

### Task 6: Upgrade `pace_verdict` to a bootstrap CI (optional, do if time)

Replace the bare-threshold pace verdict with a bootstrap CI on the like-compound clean-lap-time differences (resample comparable laps), so factor 3 carries the same signal-vs-noise rigor. Keep `insufficient` when no shared compound. Update `tests/test_race_verdict.py`. Commit `fix(race): bootstrap-CI pace verdict`. If time-constrained, leave the threshold version (it is calibrated and defensible) and note it for the final review.

---

## Self-Review
- **Coverage:** reconciliation fix (T1) ✓; comparable pairs (T2) ✓; paired bootstrap (T3) ✓; race loader + where-decomposition (T4) ✓; CLI + subprocess wiring + regen + calibration (T5) ✓; pace bootstrap upgrade (T6, optional) ✓.
- **Placeholder scan:** Task 4's test has an explicit honest fallback (live-run verification) if synthetic `Lap`s are impractical — not a silent TODO. No other placeholders.
- **Type consistency:** `comparable_pairs` index pairs feed the per-pair delta matrix feeding `paired_sector_bootstrap`; the where-payload mirrors `DecompMatchup` (consumed by Plan 3). `verdict_from_where` reads `sectors[].significant`.
- **Risk:** the subprocess boundary is the key isolation; if it fails, factor 1 degrades to `insufficient` honestly rather than breaking the build. Heavy telemetry → slow build (expected).

## Note for Plan 3
Factor 1's `decomp` payload is `DecompMatchup`-shaped, so the web reuses `DeltaCurve`/`SectorVerdict`/`DecompTrackMap`/`AttributionList` for the "where" factor with no new chart code.
