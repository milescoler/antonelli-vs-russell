# Design spec — Lap-decomposition as the flagship, web-native

**Date:** 2026-06-18
**Status:** Approved (brainstorm)
**Topic:** Make the `f1-performance-decomposition` sub-project the centerpiece of the repo, surfaced as an interactive, executive-showcasable flagship view in the Pitwall web app.

---

## Context

The repo is a data-analysis portfolio piece. Its real subject is **measurement discipline — pulling signal (driver skill) out of noise (car, conditions, lap-to-lap luck)**. The newest and purest expression of that skill is the `f1-performance-decomposition/` sub-project: it takes a single qualifying lap-time gap between two teammates and answers (1) *where on the track* the gap comes from and (2) *is each local edge real or just noise?* — via a cumulative time-delta curve, ~20 corner-anchored micro-sectors, a 5,000-sample non-parametric bootstrap (95% CIs, significance = CI excludes zero), driver-input attribution, and a hard reconciliation gate (curve endpoint must match the official gap within 0.05 s).

Today that sub-project is analyst-facing only (matplotlib PNGs, CSVs, a `REPORT.md` whose findings block is an unrun stub) and is invisible from the deployed web app. **Goal:** promote it to the headline of the project and make it land for an executive judging an internship application — someone who will spend ~60 seconds, on a phone, and will not open code, notebooks, or a markdown report.

## Decisions (from brainstorm)

1. **Primary surface:** a live, link-shareable **web experience** — the flagship view of the existing deployed Pitwall app (reuses its infra + weekly auto-deploy).
2. **Experience shape:** **guided hero story first, interactive explorer below.** Hero is fixed on the protagonist matchup; explorer lets the curious roam.
3. **Framing:** **F1-native, light touch** — let the rigor carry it, with exactly one "why this matters beyond F1" beat (signal-vs-noise extraction ≈ attribution / A-B testing / anomaly detection). No heavy-handed business analogies.
4. **Explorer set:** the **full matrix — any teammate pair × any race** (~65 decompositions), with **honest exclusion**: matchups that fail (DNF, no clean lap, reconciliation residual over tolerance, frozen sensor) are surfaced greyed with a human-readable reason, never silently dropped.
5. **Rendering:** **JSON-driven, web-native** (Recharts + SVG, like the existing telemetry track map). Matplotlib is retained only for the standalone report/notebook artifact.

**Hero matchup:** Russell (RUS) vs Antonelli (ANT), 2026 Canada qualifying — same car, ~0.07 s apart, so the signal-vs-noise question is genuinely live.

---

## Architecture — data pipeline

### Core refactor: a pure, parameterized `decompose()`
Extract a pure function from the sub-project's `run.py` orchestration:

```
decompose(year, gp, session, driver_a, driver_b, *, n_bootstrap, seed, grid_m, n_sectors, ...) -> DecompositionResult
```

- Returns structured data only — **no plotting, no file writes**: delta curve, micro-sector table (delta, ci_low, ci_high, significant, faster), attribution rows, track geometry (x, y, rate), reconciliation residual, official gap, clean-lap counts per driver, and a `status`.
- The existing `run.py` / `config.py` CLI stays and simply calls `decompose()` then does its plotting + `REPORT.md` injection. **All existing invariant tests must stay green** through the extraction (TDD).
- On any hard failure (no clean laps, reconciliation residual > `RECONCILE_TOLERANCE_S`, etc.) it returns a result with `status="excluded"` + `reason`, rather than raising — so the batch build can record and continue. (The CLI path may still treat a failed reconciliation as a raise; the batch path catches/records.)

### New build step: `scripts/build_decomp_data.py`
Sibling to the existing `scripts/build_site_data.py`.
- **Teammate pairs derived dynamically** from each race's qualifying results (group by team; take the two drivers who set timed laps; tolerate reserve/lineup changes).
- Loop race × pair; **load each session once** (FastF1 cache), call `decompose()` per pair.
- Wrap every run in honest failure handling → `valid` or `{valid:false, reason}`.
- Serialize, mirroring the existing lazy-loaded per-session telemetry pattern.

### JSON contract
`web/public/data/decomp/index.json`:
```jsonc
{
  "hero": "canada__RUS_ANT",
  "races": [{ "slug": "canada", "name": "Canadian Grand Prix", "round": 5 }],
  "matchups": [
    { "key": "canada__RUS_ANT", "race": "canada", "team": "Mercedes", "teamColor": "#27F4D2",
      "a": "RUS", "b": "ANT", "valid": true, "officialGapS": 0.07, "significantCount": 3 },
    { "key": "barcelona__RUS_ANT", "race": "barcelona", "team": "Mercedes",
      "a": "RUS", "b": "ANT", "valid": false, "reason": "Antonelli retired — no clean lap" }
  ]
}
```

`web/public/data/decomp/<race>__<A>_<B>.json` (one per valid matchup):
```jsonc
{
  "meta": { "race": "canada", "eventName": "Canadian Grand Prix", "session": "Q", "year": 2026,
            "driverA": { "code": "RUS", "name": "George Russell", "team": "Mercedes", "color": "#27F4D2" },
            "driverB": { "code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "color": "#27F4D2" },
            "officialGapS": 0.07, "reconResidualS": 0.01, "nCleanLapsA": 4, "nCleanLapsB": 3 },
  "deltaCurve": [{ "d": 0, "delta": 0.0 }],                       // cumulative delta vs distance (m, s)
  "corners":    [{ "d": 240, "label": "T1" }],
  "sectors":    [{ "i": 1, "startM": 0, "endM": 230, "midM": 115,
                   "deltaMean": -0.04, "ciLow": -0.09, "ciHigh": 0.01, "significant": false, "faster": null }],
  "attribution":[{ "sector": 7, "phase": "exit", "driverFaster": "B",
                   "brakePointDeltaM": 9, "apexSpeedDeltaKph": 3.1, "throttlePointDeltaM": -14,
                   "narrative": "Antonelli gets to full throttle ~14 m sooner out of T7." }],
  "callouts":   { "topSignificant": [7, 10, 3], "noiseTrap": 12 },  // computed from data
  "track":      [{ "x": 12.3, "y": -44.1, "rate": -0.0008 }]        // xy + d(delta)/d(distance), s/m
}
```
Sign convention is the project's existing one: `delta = t(A) − t(B)`; positive ⇒ B faster. `callouts.noiseTrap` = the largest-|delta| sector whose CI includes zero (the "looked like an edge but isn't" beat).

### CI / deploy
Extend `.github/workflows/deploy.yml` to run `build_decomp_data.py` alongside `build_site_data.py` before the Vite build. Bootstrap × ~65 pairs is seconds of compute; the only real cost is a one-time telemetry download per race (cached thereafter). **Feasibility note:** real JSON generation needs FastF1 network access — reliable in GitHub Actions. Locally we validate via the synthetic fixture + a committed sample JSON; real data is produced by the deploy run.

---

## Architecture — frontend

### Information architecture (the "main part")
- `/` → **flagship decomposition page** (hero story + explorer)
- `/season` → current standings/pace/tire dashboard, demoted to supporting breadth
- `/telemetry` → existing speed track map, kept
- `/about` → updated to lead with the decomposition

"Pitwall" remains the umbrella shell (reuses styling) with a reframed tagline. Nav label for `/` defaults to **"Lap Gap"** (changeable). The hero **absorbs** the "thesis strip" added to the old Dashboard earlier — the homepage *is* the thesis now.

### Hero story (scroll-driven, fixed RUS vs ANT Canada Q)
1. **Hook** — "Where does a 0.07-second lap gap come from — and is it even real?" + stat strip (official gap · N real · N noise).
2. **The curve** — cumulative delta curve, corner-annotated, plain-language read, hover.
3. **Verdict** — per-sector CI bar chart, green = real / grey = noise; headline count.
4. **The trap** — spotlight the `noiseTrap` sector (looked like an edge, CI straddles zero).
5. **Why** — input cause at the real sectors (brake point / apex speed / throttle point), optional overlays.
6. **Track map** — where time is won/lost, spatially.
7. **Beyond F1** — the single light-touch transferable-skill beat.
8. **Method & trust** — short: distance grid, reconciliation gate, bootstrap; links to report / notebook / source.

### Explorer (below the fold)
Race × Team pickers → curve + verdict + track map re-render from the selected matchup's **precomputed JSON** (lazy-loaded on selection — no client-side computation); excluded pairs greyed with reason.

### New components (`web/src/components/decomp/`), all JSON-driven
- `DeltaCurve.tsx` — Recharts line + corner reference lines + hover.
- `SectorVerdict.tsx` — bars + CI error bars, colored by significance.
- `DecompTrackMap.tsx` — **adapts existing `SpeedTrackMap`**, coloring by `rate` instead of speed.
- `AttributionCard.tsx` — one-sentence cause + optional speed/throttle/brake overlays.
- `MatchupPicker.tsx` — reuses the `DriverSessionPicker` pattern.
- Hooks `useDecompIndex()` / `useDecompMatchup(key)` in `lib/data.ts`; types in `types.ts`. Recharts and `Panel`/`ui` primitives already exist.

---

## Repo reorientation
- **Root `README.md`** leads with the decomposition as the headline; the Antonelli-vs-Russell 3-chapter work is reframed as a "season-wide companion analysis" section; the existing method block is re-pointed to the decomposition.
- **`f1-performance-decomposition/src/`** becomes importable from `scripts/` via a thin path/packaging shim (no logic move). Its `REPORT.md`, tests, synthetic fixture, and CLI are unchanged in spirit.
- The sub-project's empty `REPORT.md` findings block is populated by an actual CLI run, so that artifact is no longer a stub.

## Testing
- **Backend:** existing invariant tests (reconciliation, telescoping, bootstrap reproducibility, signal/noise flagging on the synthetic fixture) must stay green through the `decompose()` extraction. New tests for: the parameterized API surface, teammate-pair derivation, and the build script's JSON serialization + honest-exclusion behavior — all driven off the synthetic fixture, offline.
- **Frontend:** `tsc --noEmit` + `vite build` (existing bar). A lightweight render smoke check of the flagship against a committed sample matchup JSON, so the page is provably wired even without live data.

## Verification (end-to-end)
1. `pytest` (sub-project + new build-script tests) — green offline.
2. Run `build_decomp_data.py` (live FastF1 if reachable, else synthetic/sample path) → `index.json` + per-matchup JSON validate against the schema; excluded matchups carry reasons.
3. `npm run build` + `tsc` clean; dev server boots; eyeball hero + explorer + a greyed excluded matchup.
4. "60-second test": open `/` cold — is the headline result (where the gap is, real vs noise, the trap) legible without scrolling far?

## Scope guards
- No new statistical *methods* — we surface the existing decomposition, not invent analysis.
- Matplotlib stays only for the standalone report/notebook.
- The season dashboard is demoted, not deleted.
- Honest exclusion is a feature, not a defect — excluded matchups are shown with reasons.

## Open nano-decisions (defaults chosen, easily changed)
- Nav label for `/`: **"Lap Gap"** (vs "Decomposition").
- Whether the hero includes the input-overlay charts inline or behind a toggle: **default toggle/expand** to keep the 60-second path light.
