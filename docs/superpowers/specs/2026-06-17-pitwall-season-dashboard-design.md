# Pitwall — 2026 F1 Season Performance Dashboard: Design Spec

**Date:** 2026-06-17
**Author:** Cole Richards (with Claude)
**Status:** Approved by user (pending spec review)

---

## 1. Purpose & context

The tool has been, through several iterations, built on a **teammate comparison** (same car → the delta is the driver). The user has decided to **drop all teammate comparison** and pivot to a **descriptive season performance dashboard**, renamed **Pitwall**.

This removes the causal "driver vs car" framing entirely. Pitwall makes **no separation claims** — it's a sharp, F1TV-styled view of *who is performing and how* across the 2026 season, from real FastF1 data.

**Reused:** the Python pre-compute pipeline, FastF1 loaders, the F1 theme (F1-red / carbon / Titillium), Recharts, GitHub Pages deploy, and the championship-standings logic.
**Removed:** `src/ratings.py` (+ tests), the driver power ranking / equal-car / islands UI, and the teammate machinery in the team data (segment deltas, corner-signatures-vs-teammate, lap-delta, YoY, track-delta coloring). The notebooks/case-study PDFs are left untouched.

## 2. Goals / non-goals

**Goals:** four descriptive views — standings (drivers + constructors), qualifying pace, race pace & tire strategy, single-driver telemetry — all from real 2026 data, auto-updating, fast (static JSON).
**Non-goals:** no driver-vs-car separation, no teammate comparison, no predictions/odds, no modeling. Purely descriptive.

## 3. The four views

1. **Standings.** Drivers' **and** Constructors' championships from real points. Per entry: points, wins, podiums, avg finish, and a round-by-round form sparkline. Team-color accents.
2. **Qualifying pace.** Each driver's **gap to pole** (% off the session's fastest lap, track-normalized), as a season-average ranking + a round-by-round trend. Honest small-sample note (n = rounds).
3. **Race pace & tire strategy.** Race-pace ranking (median clean green-flag lap, normalized to each race's fastest median); per-driver stint/compound usage; tire-degradation slopes (NaN-guarded for short stints); gap-to-leader.
4. **Telemetry / track view.** Pick a driver + session → their fastest qualifying lap drawn on the circuit, **colored by speed** (heatmap), with braking/throttle markers and corner detail. Single-driver (no comparison) — a recolor of the existing track-map renderer.

## 4. Architecture & data

Pipeline (`scripts/build_site_data.py`) emits new season-level JSON; the frontend reads it (no Python at runtime). New pure-aggregation module `src/season_stats.py` (relocates the small reusable helpers — `normalize_session`, per-session pace — out of the deleted `ratings.py`).

**Data outputs (`web/public/data/`):**
- `season.json` — manifest + the three tabular views:
  - `meta`: season, rounds covered, sessions list, drivers list, `lastUpdated`.
  - `standings.drivers[]`, `standings.constructors[]` (points, wins, podiums, avgFinish, form[]).
  - `qualifying[]` — per driver: meanGapToPole_pct, byRound[], rank.
  - `racePace[]` — per driver: meanPaceGap_pct, byRound[]; `tire[]` — per driver stint/compound + deg slope.
- `telemetry/<sessionSlug>.json` — per session, every driver's fastest-lap path (columnar `{x,y,speed,throttle,brake}`, downsampled) + corner markers. Lazy-loaded on selection.

Reuse: `loaders.get_fastest_valid_lap`, `segments.resample_to_distance_grid`, `race.get_clean_laps`/`stint_pace`/`tire_deg`, `standings.build_standings`. Light Q/R results loads for standings + qualifying pace; race laps for race pace; telemetry only for the track view. All deterministic (sorted keys/lists, fixed rounding, write-if-changed) and auto-updating via the existing GitHub Action.

**Pure functions to add (`src/season_stats.py`), unit-tested:** `constructors_table(driver_rows)`, `qualifying_pace_table(pace_rows)`, `race_pace_table(lap_rows)`, `tire_summary(stint_rows)`, plus relocated `normalize_session`.

## 5. Frontend (`web/`)

Rename app to **Pitwall**; nav brand + title updated; F1 theme kept. Structure:
- **Dashboard (`/`)**: Standings (drivers + constructors, side by side) → Qualifying pace → Race pace & tire strategy, as stacked F1-styled panels.
- **Telemetry (`/telemetry`)**: driver + session selectors → speed-colored track map (recolored `TrackMap`) + corner detail.
- **About/Method (`/about`)**: short, honest "what this shows / data via FastF1 / descriptive only" note.

New components: `StandingsTable` (reuse, extend for constructors), `QualifyingPace`, `RacePaceTable`, `TireStrategy`, `SpeedTrackMap` (recolor of `TrackMap`), `DriverSessionPicker`. **Delete:** `DriverRanking`, `EqualCarGrid`, the teammate-detail `TeamDashboard`/`OverviewGrid` ranking pieces, `PredictionCard` (already gone).

## 6. Build milestones (for the implementation plan)
1. `src/season_stats.py` + tests (constructors, qualifying pace, race pace, tire) — relocate `normalize_session`; delete `ratings.py` + tests.
2. Pipeline: emit `season.json` + `telemetry/<session>.json`; remove ratings/teammate outputs.
3. Frontend data layer + types + hooks for the new JSON; rename to Pitwall.
4. Build the four views; recolor `TrackMap` → `SpeedTrackMap`; remove comparison components.
5. About page; verify, deterministic rerun, commit.

## 7. Verification
- **Python:** `pytest` (existing race/standings/segments tests + new `season_stats` tests) green; `ratings` tests removed. Run the pipeline → `season.json` has drivers+constructors standings (ANT leads, 143 pts), a qualifying-pace ranking, race-pace + tire tables, and one `telemetry/<session>.json` per session. Determinism: rerun → clean `git diff`.
- **Frontend:** `npm run typecheck && npm run build` clean; `npm run dev` → Pitwall branding; all four views render from real data; telemetry picker loads a session's lap and colors by speed.
- **Honesty:** no teammate/driver-vs-car language anywhere; small-sample notes on pace.

## 8. Non-blocking / later
- The repo (`antonelli-vs-russell`) and Python dir (`f1_project`) names are now stale vs "Pitwall" — optional rename later (affects only the Vite `base` path and the git remote). Championship standings remain the data backbone.
