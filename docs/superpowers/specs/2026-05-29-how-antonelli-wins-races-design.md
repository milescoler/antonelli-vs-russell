# How Antonelli Keeps Winning — Race-Result Analysis: Design Spec

**Date:** 2026-05-29
**Author:** Cole Richards (with Claude)
**Status:** Approved (pending spec review)

---

## 1. Purpose & context

A new race (Round 5, the **Canadian Grand Prix**, 2026-05-24) has been run, and it
changes the story the existing project tells. The repo to date is a portfolio-quality
*qualifying* comparison of the two Mercedes drivers (Antonelli vs Russell) across the
first 4 rounds of 2026. See the approved v1 spec:
[2026-05-12-antonelli-vs-russell-design.md](2026-05-12-antonelli-vs-russell-design.md).

Two things motivate this work:

1. **Canada breaks the qualifying headline.** Antonelli qualified **0.068 s slower**
   than Russell at Canada (P2 vs Russell's pole) — the existing README's central claim
   ("faster every round since R1, monotone gain, margin growing each round") is no
   longer true.
2. **The user wants to reframe the project around race wins.** Antonelli has won **4 of
   the last 4 races** (China, Japan, Miami, Canada); he lost only the Australia opener
   (P2). Qualifying — what the project measures today — explains grid position, but not
   how those grids convert to wins. Canada is the proof: he won the race from P2 *after*
   Russell (on pole) retired.

This spec defines the reframe: the project's headline becomes **"Antonelli has won 4 of
the last 4 races. How?"**, with the existing qualifying analysis demoted to Chapter 1
(get-to-the-front evidence) and three new race-mechanism chapters added.

**Audience:** technical recruiters and engineers visiting the portfolio. Non-F1 readers
must be able to follow the README and notebooks. The README is itself a deliverable.

## 2. Scope

### Comparison frame
- **Teammate as control (primary):** Antonelli vs Russell, same car → isolates driver.
  Runs through every chapter.
- **Field as context (secondary):** the *actual P2 finisher* of each race (varies by
  race; Russell is not always P2) is the "what winning required" reference, used in the
  race-pace chapter.

### Races
All **5** rounds of 2026: Australia (R1, the loss), China (R2), Japan (R3), Miami (R4),
Canada (R5). The 4 wins are the subject; Australia is the honest counter-case.

### Race-winning mechanisms in scope
1. **Start & lap 1** — grid → position at end of lap 1, positions gained. Canada
   (P2 → led by lap 2) is the centerpiece.
2. **Race pace & control** — green-flag clean-lap pace per stint (ANT vs RUS vs P2
   finisher) and a per-lap gap-to-leader trace (pull away vs manage/inherit).
3. **Tire management / degradation** — linear slope of clean-lap time vs tire age
   (s/lap) per stint, ANT vs RUS.

### Qualifying chapter update
The existing qualifying analysis is retained as Chapter 1, **with Canada (R5) added**:
all hard-coded "first 4 rounds", monotone-trend, and aggregate numbers updated to the
5-race values (see §7).

### Rigor level (chosen: "robust middle", Approach C)
Defensible descriptive metrics with light modeling only where stable. **No** fuel-load
correction model, **no** track-evolution model, **no** undercut/overcut math — with 5
races and ~40 green laps per stint, fuel/deg/evolution are badly collinear and a fitted
pace model would overfit. Uncontrolled factors (fuel burn, traffic, safety cars) are
**named as caveats, not modeled away** — consistent with the project's existing honesty
(e.g. the Japan sensor-freeze section).

### Non-goals (explicitly out of scope)
- Fuel-corrected or track-evolution-corrected "true pace" models.
- Undercut / overcut / strategy-simulation math.
- Full-field analysis beyond the per-race P2 reference.
- A built-out "capitalizing on rivals' misfortune" section. Russell's Canada DNF is
  named plainly in the honest-accounting narrative, but is not its own analytical
  component.

## 3. Architecture

Follows the existing clean module pattern (`loaders` / `segments` / `benchmarks` /
`plotting`). Race logic is isolated in **one new module**, with additions to plotting
and a new test file. The qualifying pipeline (`segments.py`, qualifying paths in
`benchmarks.py`) is **untouched** except that the notebook adds `'Canada'` to `RACES`.

### Module boundaries

| File | Responsibility | Status |
|------|---------------|--------|
| [src/loaders.py](../../../src/loaders.py) | FastF1 session/lap/telemetry loading (qualifying) | done — unchanged |
| [src/segments.py](../../../src/segments.py) | Segment math | done — unchanged |
| [src/benchmarks.py](../../../src/benchmarks.py) | `compare_teammates`, `compute_corner_signatures` (qualifying) | done — unchanged |
| [src/race.py](../../../src/race.py) | **New.** All race-session logic | to build |
| [src/plotting.py](../../../src/plotting.py) | Existing qualifying plots + **4 new race plots** | extend |
| [tests/test_race.py](../../../tests/test_race.py) | **New.** Race invariant + Canada-anchor tests | to build |
| [notebooks/01_antonelli_vs_russell.ipynb](../../../notebooks/01_antonelli_vs_russell.ipynb) | Qualifying chapter; add Canada (R5) | modify |
| [notebooks/02_how_antonelli_wins_races.ipynb](../../../notebooks/02_how_antonelli_wins_races.ipynb) | **New.** The race chapters | to build |

A separate `02` notebook (rather than folding race chapters into `01`) keeps each
notebook focused; the README ties them together.

### `src/race.py` function signatures

```python
def load_race_session(year: int, race: str) -> fastf1.core.Session:
    """Load the Race (R) session for a given year/race, with laps loaded.
    Parallels load_qualifying_session."""

def get_clean_laps(session, driver: str) -> pd.DataFrame:
    """Green-flag racing laps only: TrackStatus == '1', excludes in-laps,
    out-laps, pit laps, and lap 1. The shared filter all race metrics build on."""

def start_summary(year: int, race: str) -> pd.DataFrame:
    """One row per reference driver (ANT, RUS, P2-finisher): grid position,
    position at end of lap 1, positions_gained (grid - lap1_pos), final position."""

def stint_pace(year: int, race: str, drivers: list[str]) -> pd.DataFrame:
    """Per driver per stint: median clean-lap time, compound, n clean laps."""

def tire_deg(year: int, race: str, drivers: list[str]) -> pd.DataFrame:
    """Per driver per clean stint: linear slope of clean-lap time vs TyreLife
    (s/lap), compound, n clean laps. Stints with < 5 clean laps yield slope=NaN."""

def gap_to_leader(year: int, race: str, driver: str) -> pd.DataFrame:
    """Per-lap cumulative gap (s) of `driver` to the race leader, for the
    gap-to-leader trace."""
```

The per-race P2 finisher is resolved inside `race.py` (e.g. a private
`_pn_finisher(session, n)` helper), so `loaders.py` stays qualifying-agnostic.

### `src/plotting.py` additions

Four new functions, matching the existing signature style (take a tidy df, optional
`save_path`, return `fig`):
- `plot_start_conversion(start_df, save_path=None)` — grid → lap-1 → finish per race.
- `plot_stint_pace(pace_df, save_path=None)` — median clean-lap per stint, ANT vs RUS
  vs P2, labeled by compound.
- `plot_gap_trace(gap_df, save_path=None)` — per-lap gap-to-leader, per race.
- `plot_tire_deg(deg_df, save_path=None)` — degradation slope (s/lap) per comparable
  stint, ANT vs RUS.

## 4. Data flow

```
FastF1 R session ──load_race_session──▶ laps
   laps ──get_clean_laps──▶ green-flag laps (shared filter)
       ├─▶ start_summary  ─▶ start df    ─▶ plot_start_conversion
       ├─▶ stint_pace     ─▶ pace df     ─▶ plot_stint_pace
       ├─▶ gap_to_leader  ─▶ gap trace   ─▶ plot_gap_trace
       └─▶ tire_deg       ─▶ slope df    ─▶ plot_tire_deg
```

Notebook `02` orchestrates: loops the 5 races, builds the dfs, renders charts to
`figures/`, and carries the narrative markdown. The same `RACES` list drives both the
qualifying chapter (notebook `01`) and the race chapters (notebook `02`).

### Cross-cutting rules (consistency with the qualifying chapter's rigor)
- **One sign convention, stated once** and held across all race charts (define whether
  "positive = Antonelli better").
- **Safety-car / red-flag laps excluded everywhere** via the shared `get_clean_laps`
  filter (`TrackStatus == '1'`).
- **Like-compound comparisons only** in stint pace; compound mismatches are flagged,
  not silently averaged.
- **Small-n guard:** tire-deg slopes require ≥ 5 clean laps in a stint; otherwise report
  "n too small" (NaN), never a noisy fitted number.
- **P2 finisher is the field reference** per race, resolved per race (varies).

## 5. The three race components (detail)

### Component A — Start & lap 1
- `start_summary` → `plot_start_conversion`.
- Metric: grid, lap-1 position, positions gained, final position — ANT / RUS / P2.
- Chart: slope / small-multiples, grid → lap-1 → finish per race. Canada (P2 → led by
  L2) and Australia (P2 → P2, the loss) both visible.
- Narrative note: Canada's lead came on lap 2; Russell's later DNF is what sealed the win.

### Component B — Race pace & control
- `stint_pace` + `gap_to_leader` → `plot_stint_pace`, `plot_gap_trace`.
- Metric 1: median green-flag lap per stint (no in/out/pit/L1, TrackStatus==1), ANT vs
  RUS vs P2 finisher, labeled by compound; like-compound only.
- Metric 2: per-lap gap-to-leader trace per race — "pulled away" (China/Japan/Miami) vs
  "managed/inherited" (Canada).
- Caveat stated inline: raw medians don't fuel-correct; stint timing and traffic differ.

### Component C — Tire degradation
- `tire_deg` → `plot_tire_deg`.
- Metric: linear slope of clean-lap time vs `TyreLife` per stint (s/lap), ANT vs RUS, by
  compound; ≥ 5 clean laps required to fit.
- Chart: slope bars (or laptime-vs-tyrelife scatter with fit lines) per comparable stint.
- Caveat: fuel burn lowers lap times through a stint, partially offsetting real deg —
  named, not modeled out.

## 6. Testing

`tests/test_race.py`, extending the repo's existing "one consistency test" philosophy —
invariants on real telemetry, not brittle exact-value asserts:

- `get_clean_laps` returns no in/out/pit laps, no lap 1, and every returned lap has
  `TrackStatus == '1'`.
- `start_summary`: `positions_gained == grid − lap1_pos` for each reference driver.
- `tire_deg`: stints with < 5 clean laps yield `NaN` slope, not a number (guards the
  small-n rule).
- **End-to-end regression anchor:** for Canada 2026, ANT's lap-1 position is 2 and final
  position is 1 — the case the whole piece hinges on.

Keep to a handful of meaningful tests, matching the repo's light test footprint.

## 7. Deliverables & what changes

### New files
- `src/race.py` — 6 functions (§3).
- `tests/test_race.py` — invariant + Canada-anchor tests (§6).
- `notebooks/02_how_antonelli_wins_races.ipynb` (+ exported PDFs: with-code and
  no-code, matching the `01` pattern).
- New figures: `start_conversion.png`, `stint_pace.png`, `gap_trace.png`,
  `tire_deg.png`.

### Modified files
- `README.md` — reframed around "how he keeps winning": new title, new headline (4 of 5
  wins), qualifying demoted to Chapter 1, three new race chapters, honest-accounting
  section updated (Canada DNF, 5-race sample). All hard-coded "first 4 rounds" /
  monotone-trend / aggregate numbers updated to 5-race values.
- `notebooks/01_antonelli_vs_russell.ipynb` — add `'Canada'` to `RACES`; update the
  qualifying markdown asserting the monotone trend; regenerate its figures + PDFs.
- `src/plotting.py` — 4 new race plot functions.
- Existing qualifying figures regenerated with R5 data: `headline_segment_delta.png`,
  `lap_delta_by_round.png`, `track_delta_map.png`, `year_over_year.png`,
  `corner_buckets.png`.
- `case_study.pdf` — regenerated to reflect the new framing.

### Updated qualifying numbers carried into prose (computed during design)
| Quantity | Old (4 races) | New (5 races) |
|---|---|---|
| 2026 qualifying mean lap Δ (RUS−ANT) | +0.16 s | **+0.11 s** |
| 2026 trajectory | monotone, faster every round | **not monotone** — Canada **−0.07 s** (R1 −0.29, R2 +0.22, R3 +0.30, R4 +0.40, R5 −0.07) |
| YoY mean gain vs 2025 | +0.53 s/track (4) | **+0.51 s/track (5)**; range 0.29–0.69; Canada +0.42 |
| Segment categories | flat (±0.014) | **still flat** (straight +0.005, slow −0.001, fast −0.003, medium −0.014) |
| Corner-cycle fast signature | brake ~21 m later, throttle ~23 m sooner (12 pts) | **unchanged** — Canada (Montreal) added no fast-corner points |
| Sensor flags | Japan only (5 segs) | **unchanged** — Canada clean |

### Race-result facts (2026, R session)
| Round | Race | Grid | Finish | Note |
|---|---|---|---|---|
| 1 | Australia | P2 | P2 | Lost to Russell (pole → win) |
| 2 | China | P1 | **P1 WIN** | From pole |
| 3 | Japan | P1 | **P1 WIN** | From pole |
| 4 | Miami | P1 | **P1 WIN** | From pole |
| 5 | Canada | P2 | **P1 WIN** | Led by L2; Russell (pole) retired |

## 8. Open questions / risks

- **5-race sample.** All findings are directional; the README must keep saying so. The
  three race mechanisms have even thinner data than the qualifying chapter — state this.
- **Compound availability for like-for-like stint comparison.** If ANT and RUS never
  share a compound in a given race, the stint-pace comparison for that race is reported
  as "no comparable stint" rather than forced.
- **Gap-to-leader when ANT *is* the leader.** Trace is gap to the leader; when ANT leads,
  show his gap *ahead* of P2 instead (the "pulling away" signal). To confirm in
  implementation.
- **Title wording** ("How Kimi Antonelli Keeps Winning: A Look at the 2026 Mercedes
  Driver") is a placeholder; finalize during README rewrite.
