# Race-Win Decomposition — Web Flagship + Repo Cut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Surface the race-win decomposition as the Pitwall flagship (`/`) — a guided hero race (4 factors, each with a real/noise verdict) + an explorer over the season's wins — then cut the now-superseded season dashboard + 3-chapter study from the repo.

**Architecture:** New `RaceDecomp` page consumes `web/public/data/race/{index.json,<slug>.json}`. Factor 1 ("where on track") reuses the existing `DeltaCurve`/`SectorVerdict`/`DecompTrackMap`/`AttributionList` (the payload matches their types). Three small new components render tyre/pace/start. Then a safe-ordered deletion of the dashboard + chapters + old pipelines, and a README/About/CI reframe.

**Tech Stack:** React 19, Vite 6, TypeScript 5.8, Tailwind 4, Recharts 2.15, HashRouter. No new deps. No FE test runner — gate is `npm run typecheck` + `npm run build`.

## Global Constraints
- The race JSON is already generated. Per-race shape: `meta{race,eventName,round,year,winner{code,name,team,color},p2{...},marginS,anyDnf,winnerInherited,winnerStartedPole,poleSitter}`, `signConvention`, `factors{where,tyre,pace,start}`, `caveats`. Each factor has `verdict ∈ {real,noise,inherited,insufficient}`, `magnitudeS`, `magnitudeUnit`, `headline`, `caveat`. `where` additionally has `decomp` (a `DecompMatchup`-shaped object: `deltaCurve,corners,sectors[],attribution[],callouts,track[]`, `meta.driverA/B.code`, `meta.nPairs/nUniqueLapsA/nUniqueLapsB`) or `decomp:null`. `tyre/pace` have `stints[]`; `pace` has `gapTrace{laps,gap_s,leading,driverCode}`; `start` has `rows[]` ({role,code,grid,lap1Pos,positionsGained,finish,status,dnf}).
- `index.json`: `{hero:"monaco", races:[{slug,name,round}], entries:[{slug,round,valid,winner,p2,marginS?,realFactorCount?,reason?}]}`.
- Reuse existing primitives: `Panel`/`Badge`/`StudyLinks` (`components/ui.tsx`), `charts/common.tsx`, `getJSON` (`lib/data.ts`), and the four `components/decomp/*` for factor 1.
- Business-forward framing for a hiring manager; F1 the worked example. Honest: surface `nUniqueLaps` for factor 1 and the `insufficient`/`inherited` verdicts plainly.
- Verdict → Badge tone: real=`sky`/green, noise=`zinc`, inherited=`amber`, insufficient=`zinc`/muted.

Paths relative to repo root. Frontend commands from `web/`.

---

### Task 1: Race types + hooks
**Files:** Modify `web/src/types.ts` (append), `web/src/lib/data.ts` (append).
**Produces:** types `RaceDecomp`, `RaceDecompIndex`, `Verdict`, `FactorBase`, `WhereFactor`(`{...FactorBase, decomp: DecompMatchup|null}` — reuse existing `DecompMatchup`/`Sector`/etc.; widen `DecompDriver` usage so a `{code,...}`-only meta type-checks, e.g. a `WhereDecomp` alias whose `meta.driverA/B` is `{code:string; name?:string; team?:string; color?:string|null}`), `TyreFactor`/`PaceFactor`/`StartFactor` (with `stints`/`gapTrace`/`rows`); hooks `useRaceIndex()` (`getJSON<RaceDecompIndex>('race/index.json')`) and `useRaceDecomp(slug)` (`getJSON<RaceDecomp>(\`race/${slug}.json\`)`), mirroring `useDecompIndex`/`useDecompMatchup`.
- [ ] Append the types + hooks; `cd web && npm run typecheck && npm run build` clean; commit `feat(web): race-decomp types + hooks`.

### Task 2: Three factor components (tyre / pace / start)
**Files:** Create `web/src/components/race/{TyreFactor,PaceFactor,StartFactor}.tsx`.
- **TyreFactor**: winner vs P2 `stints[]` — compound chips (salvage `CompoundChip`/`COMPOUND_COLORS` from `components/TireStrategy.tsx` before it's deleted) + per-stint deg-slope; show the verdict headline.
- **PaceFactor**: a Recharts `LineChart` of `gapTrace` (lap on X, gap_s on Y; `leading` shown) — "leading and extending" vs "inherited/flat"; reuse `charts/common.tsx`.
- **StartFactor**: a compact grid→lap1→finish ladder from `rows[]` (winner + P2), highlighting `positionsGained`; surface `inherited` honestly.
- Each takes its factor object; renders the headline + a `Badge` for the verdict + the viz + the caveat.
- [ ] Create the three; `npm run typecheck && npm run build` clean; commit `feat(web): tyre/pace/start factor components`.

### Task 3: RaceDecomp flagship page + RacePicker
**Files:** Create `web/src/pages/RaceDecomp.tsx`, `web/src/components/race/RacePicker.tsx`.
- Hero: business-forward H1 ("What actually won this race — and what was noise?"), sub naming the worked example ("{winner} beat {p2} by {marginS}s at {eventName}"). Stat strip: margin · real N/4 · noise N/4.
- Four factor `Panel`s in order where/tyre/pace/start, each with verdict Badge + component (factor 1 → `DeltaCurve`+`SectorVerdict`+`AttributionList`+`DecompTrackMap` on `where.decomp` when non-null, else the `insufficient` message; pass `where.decomp` whose `meta.driverA/B.code` the charts read; show the `nUniqueLaps` caveat).
- "Why this matters beyond F1" Panel (business framing: outcome attribution under uncertainty = root-cause / A-B / anomaly detection).
- Explorer: `RacePicker` (one dropdown of `index.races`; excluded/insufficient races still selectable, shown honestly) → re-render the four factors for the picked race. Default to `index.hero`.
- "Method & trust" Panel: clean-lap filter, like-compound, fuel not corrected, comparable-lap selection + bootstrap CIs, per-driver reconciliation; `StudyLinks`.
- [ ] Create both; `npm run typecheck && npm run build` clean; commit `feat(web): race-win decomposition flagship page + explorer`.

### Task 4: Routing reorientation
**Files:** Modify `web/src/App.tsx`.
- `/` → `RaceDecomp`; remove `/season` (`Dashboard`) and `/telemetry` (`Telemetry`) routes + imports + nav links. Keep `/about`. Update nav brand/label toward "What Won the Race?" / "Race Win". Footer stays (StudyLinks).
- [ ] Edit; remove now-unused imports; `npm run typecheck && npm run build` clean; commit `feat(web): make race-win decomposition the landing route`.

**CHECKPOINT:** after Task 4 the new flagship is live and the old dashboard is merely unrouted (not deleted). Verify `npm run dev` renders `/` with the hero + 4 factors + explorer before the destructive cut.

### Task 5: Repo cut (safe order)
**Files:** delete. Do in this order; run `npm run build` + `python -m pytest tests/` after, and `git grep` to confirm no dangling imports.
1. Web: delete `web/src/pages/{Dashboard,Telemetry}.tsx`, `components/{StandingsBoard,PaceTable,SpeedTrackMap,DriverSessionPicker,TireStrategy}.tsx` (after salvaging `CompoundChip` into TyreFactor), `components/decomp/MatchupPicker.tsx` (qualifying-only), `lib/data.ts` `useSeason`/`useTelemetry` + the qualifying decomp hooks if unused, and the dashboard/qualifying types in `types.ts` if unused. Delete `web/public/data/{season.json,telemetry/,decomp/}`.
2. Pipelines: delete `scripts/{build_site_data,build_decomp_data,refresh}.py`. Fold round-discovery into `build_race_decomp_data.py` (it already uses `teams.list_completed_rounds`, so just confirm it no longer depends on season.json).
3. Python `src/`: delete `{benchmarks,segments,track_history,standings,season_stats,plotting}.py` + their tests (`tests/test_{segments,track_history,standings,season_stats,teams?}.py`); keep `race.py,serialize.py,loaders.py,teams.py,season.py,race_win.py,race_verdict.py`. Trim dead qualifying serializers in `serialize.py` only if low-risk.
4. Notebooks/docs/figures: delete `notebooks/`, `docs/case_study.*`, `case_study.pdf`, `figures/`.
5. Engine `f1-performance-decomposition/`: KEEP (it's the decomposition + factor-1 engine).
- [ ] Delete in order; after each group run `python -m pytest tests/ -q` + `cd web && npm run build`; `git grep -n "build_site_data\|track_history\|StandingsBoard\|useSeason"` returns nothing live; commit `chore: cut the season dashboard + 3-chapter study (superseded by race-win decomposition)`.

### Task 6: README / About / links / CI reframe
**Files:** `README.md`, `web/src/pages/About.tsx`, `web/src/lib/links.ts`, `web/index.html`, `.github/workflows/deploy.yml`, `package.json` (name).
- README: lead with "What Won the Race?" — the one centerpiece; drop the 3-chapter table + figures; keep the measurement-discipline thesis + FastF1/reproduce. Point at `f1-performance-decomposition/REPORT.md`.
- About: rewrite around the new thesis; KEEP the Japan frozen-sensor anecdote (great measurement-discipline story); add the new "what won the race / signal vs noise" framing.
- `links.ts`: repoint `caseStudy` → `f1-performance-decomposition/REPORT.md`; drop notebooks link.
- `index.html` title/description; footer text; `package.json` name → e.g. `what-won-the-race`.
- `deploy.yml`: remove the `build_site_data.py` + `build_decomp_data.py` steps (deleted); keep `build_race_decomp_data.py`; update `paths:`.
- [ ] Edit; `npm run build` clean; commit `docs: reframe the repo around the race-win decomposition flagship`.

### Task 7: End-to-end verification
- [ ] `cd web && npm run typecheck && npm run build` clean; `python -m pytest tests/ -q` + engine suite green.
- [ ] `npm run dev` → `/` shows the hero race with four verdicted factors (Monaco: where/tyre/pace real, start noise), the explorer switches races (Canada shows start `inherited`, Japan where `insufficient`), deleted routes 404 cleanly.
- [ ] The 60-second test: margin + four factors + which are real vs noise legible without deep scrolling, business framing up top.
- [ ] `git grep` clean of deleted-module references; commit any final polish.

## Self-Review
- Coverage: types/hooks (T1) ✓; factor components (T2) ✓; flagship page + explorer (T3) ✓; routing (T4) ✓; cut (T5) ✓; reframe (T6) ✓; verify (T7) ✓.
- Reuse: factor-1 payload matches `Sector`/`AttributionItem`/`TrackPoint`/`CurvePoint` → existing decomp components reused.
- Honesty: `insufficient`/`inherited` verdicts + factor-1 `nUniqueLaps` caveat are surfaced, not hidden.
