# Separating the Driver from the Car — How Good Is Antonelli, Really?: Design Spec

**Date:** 2026-06-07
**Author:** Cole Richards (with Claude)
**Status:** Approved by user (pending spec review)

---

## 1. Purpose & context

Round 6, the **Monaco Grand Prix** (2026-06-07), has just been run. Antonelli took
**pole** (Russell only P6 — his largest qualifying margin over his teammate this year)
and **won the race** from pole (HAM P2, HAD P3). Through Monaco he has now won **5 of the
last 6** rounds (China, Japan, Miami, Canada, Monaco), losing only the Australia opener.

The repo is currently in a split state:

- **`main` ships the v1 project:** a portfolio-quality *qualifying* teammate comparison
  (Antonelli vs Russell) across the first **4** rounds. See the v1 spec:
  [2026-05-12-antonelli-vs-russell-design.md](2026-05-12-antonelli-vs-russell-design.md).
- **A reframe was designed but never built.** The 2026-05-29 commits added a spec
  ([2026-05-29-how-antonelli-wins-races-design.md](2026-05-29-how-antonelli-wins-races-design.md))
  and a full implementation plan to reframe the project around race wins (adding
  start/pace/tire analysis and folding in Canada R5). `src/race.py`, `notebooks/02`,
  and the new figures **do not exist** — only the docs were committed.

This spec **supersedes and absorbs** the 2026-05-29 reframe, extends it through Monaco,
and adds a third analytical layer the user requested: a **cross-year, per-track
historical analysis** that controls for the car *across seasons* (the teammate
comparison controls for it *within* a season). The user's framing of that request —
*"which teams do best… that might help control for car differences year by year"* — is
itself a car-control mechanism, so it slots under the same spine rather than forming a
second project.

**The unifying central direction (decided with the user):**

> **Separating the driver from the car: how good is Antonelli, really?**

Every chapter is one independent way to strip car performance out of the picture.

**Audience:** technical recruiters and engineers visiting the portfolio. Non-F1 readers
must be able to follow the README and notebooks. The README is itself a deliverable.

**Standing constraint (user):** the whole pipeline must be **refreshable after every
race** — one `RACES` list drives everything, and one command brings the project current
(fetch new session → re-execute notebooks → regenerate figures + PDFs). See §8.

## 2. The three chapters (the spine)

| Ch | Question | How it removes the car | Status |
|----|----------|------------------------|--------|
| 1 | Is he faster than his teammate? | Same car, same season (Russell) | exists — **extend** to Monaco |
| 2 | How does he convert pace to wins? | Same car, same race (Russell + per-race P2 ref) | designed, **unbuilt** — **build + extend** to Monaco |
| 3 | Are his wins at "driver tracks" or "car tracks"? | Same track, across years (overperformance vs each season's own baseline) | **new** |

The README ties the three together under the single thesis. Each chapter is its own
notebook (`01`, `02`, `03`); `src/` modules stay small and single-purpose.

## 3. Scope

### Races (2026 season-to-date)
All **6** rounds: Australia (R1, the loss), China (R2), Japan (R3), Miami (R4),
Canada (R5), **Monaco (R6, new)**. Master list:
`RACES = ['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco']` — drives all
three notebooks. Monaco and Canada 2026 sessions: Monaco must be fetched on first run
(confirmed available: Q and R both load); Canada is already cached. The 2025 sessions
for the same tracks are pulled implicitly by the year-over-year comparison.

### Historical window (Chapter 3)
**2010–2025** (~16 seasons), exposed as a tunable parameter (`years`). Results-only
loads — confirmed available and fast back to at least 2010 in this data source.

### Comparison frames
- **Teammate as control (primary):** Antonelli vs Russell — same car. Chapters 1–2.
- **Per-race P2 finisher (field context):** Chapter 2 race-pace reference (varies by
  race; resolved per race).
- **Season-baseline overperformance (cross-year car control):** Chapter 3. See §6.

### Data-world honesty (applies to Chapter 3 especially)
This is the project's own "2026 season" data source. Its history is internally
consistent but **not** real-world (e.g. it lists a 2020 Monaco winner; Monaco wasn't
held in 2020 in reality). The analysis is therefore **data-driven** — it lets the
numbers define who is strong at a track rather than asserting real-world reputations.
No prose makes claims about real F1 history; all claims are "in this dataset". This is
stated once in the Chapter 3 method note.

### Rigor level (carried from the existing project)
Defensible descriptive metrics, light modeling only where stable, uncontrolled factors
**named as caveats, not modeled away** (consistent with the Japan sensor-freeze
section). **No** fuel/track-evolution models, **no** strategy simulation, **no** fitted
"true pace" model.

### Non-goals (explicitly out of scope)
- Fuel-corrected / track-evolution-corrected pace models; undercut/overcut math.
- Full-field telemetry analysis beyond the per-race P2 reference.
- Real-world-history claims in Chapter 3 (the data is synthetic; see above).
- A regression/ML model of track affinity — the overperformance metric is descriptive
  arithmetic, deliberately, to match project rigor and avoid overfitting.

## 4. Architecture

Follows the existing clean module pattern. The qualifying pipeline
(`loaders.py`, `segments.py`, qualifying paths in `benchmarks.py`) is **untouched**
except the notebook's `RACES` list. Two new isolated modules; plotting extended; two
new test files; one orchestration script.

| File | Responsibility | Status |
|------|----------------|--------|
| [src/loaders.py](../../../src/loaders.py) | FastF1 qualifying session/lap/telemetry loading | done — unchanged |
| [src/segments.py](../../../src/segments.py) | Segment math | done — unchanged |
| [src/benchmarks.py](../../../src/benchmarks.py) | `compare_teammates`, corner signatures (qualifying) | done — unchanged |
| `src/season.py` | **New.** Single source of truth: the `RACES` list + default `years` window, imported by all three notebooks and the refresh script | to build |
| `src/race.py` | **New (Ch2).** All race-session logic (per the 2026-05-29 plan) | to build |
| `src/track_history.py` | **New (Ch3).** Cross-year per-track overperformance | to build |
| [src/plotting.py](../../../src/plotting.py) | Existing plots + 4 race plots + 3 track-history plots | extend |
| `scripts/refresh.py` | **New.** One-command season refresh | to build |
| `tests/test_race.py` | **New.** Race invariants + Monaco/Canada anchors | to build |
| `tests/test_track_history.py` | **New.** Overperformance invariants + small-n guard | to build |
| `notebooks/01_antonelli_vs_russell.ipynb` | Ch1 — add Canada **and** Monaco | modify |
| `notebooks/02_how_antonelli_wins_races.ipynb` | **New.** Ch2 race chapters | to build |
| `notebooks/03_driver_vs_car_track_history.ipynb` | **New.** Ch3 track history | to build |
| `README.md` | Reframed around the single thesis; 3 chapters; refresh section | modify |
| `case_study.pdf` | Regenerated to the new framing | regen |

## 5. Chapter 1 — Qualifying (update only)

Extend the existing notebook's `RACES` through **Monaco**. This subsumes the
2026-05-29 plan's "add Canada" step — Canada **and** Monaco are added in one pass.

- Recompute all 6-race aggregates **from live data** (do not trust any number written in
  a plan); update the trajectory prose (the early monotone climb already broke at
  Canada; Monaco adds a large +ve for Antonelli — state the real shape from the
  recomputed values).
- The year-over-year chart now spans **6 tracks** (2025 sessions for Canada and Monaco
  pulled implicitly). Confirm each track's `q_mismatch` flag so the hollow-marker set is
  intentional.
- Segment-category, corner-cycle, and sensor-flag sections updated to 6-race values
  (Japan remains the only sensor-flagged race unless Monaco data says otherwise).
- Regenerate the five qualifying figures and the notebook PDFs.

**All carried numbers are recomputed live during implementation; none are hard-coded
from this spec or the prior plan.**

## 6. Chapter 2 — Race-winning mechanisms (build the pending plan, extended)

Build exactly the modules, plots, tests, and notebook specified in the **approved
2026-05-29 plan** ([2026-05-29-how-antonelli-wins-races.md](../plans/2026-05-29-how-antonelli-wins-races.md)),
with two deltas:

1. **`RACES` runs through Monaco (R6)**, not stopping at Canada (R5).
2. **Monaco regression anchor added** to `tests/test_race.py`: ANT lap-1 position and
   final position at Monaco 2026 are both 1 (pole → win), alongside the existing Canada
   anchor (P2 → P1).

`src/race.py` functions (unchanged from the prior plan): `load_race_session`,
`get_clean_laps`, `start_summary`, `stint_pace`, `tire_deg`, `gap_to_rival`, plus the
`_pn_finisher` helper. Four plots: `plot_start_conversion`, `plot_stint_pace`,
`plot_gap_trace`, `plot_tire_deg`. Sign convention: **positive = Antonelli better**.
Clean lap = `TrackStatus == '1'`, not lap 1, not in/out/pit, valid `LapTime`.
Cross-cutting rules (one sign convention, SC/red-flag excluded everywhere,
like-compound only, ≥5-clean-lap tire-deg guard, per-race P2 reference) carry over
verbatim from the 2026-05-29 spec §4.

## 7. Chapter 3 — Cross-year track history (new)

New module `src/track_history.py` (results-only loads), new notebook `03`, and the
chapter folded into the README. Reusable for any track; **Monaco is the centerpiece**
deep-dive, with a compact summary across all 6 tracks Antonelli has raced in 2026.

### 7.1 Core definitions

For a given `track` and a set of `years`:

- **A driver-year is "classified"** at a round if the driver was running at the flag
  (FastF1 `Status` starting with `"Finished"` or `"+N Lap(s)"`). DNF/DNS rounds are
  **excluded** from both the baseline and the track value (per the user-approved
  DNF handling) so a retirement's ~back-of-grid classified position cannot masquerade
  as "bad at this track".
- **Season baseline (finish):** `baseline_finish(d, y)` = mean classified finishing
  position of driver `d` across **all** classified rounds in season `y`.
  **Edge case:** if `d` has no *other* classified round that season (a one-off entry, or
  the track round is their only finish), the baseline is undefined and that driver-year
  contributes **no** delta — it is dropped, not treated as zero overperformance.
- **Track overperformance (finish):** for each year `y` the driver was classified at the
  track, `track_delta_finish(d, track, y) = baseline_finish(d, y) − finish(d, track, y)`.
  **Positive = finished better here than their season norm** (lower position number is
  better, hence baseline − track).
- **Driver track affinity:** mean of `track_delta_finish(d, track, y)` over the years in
  the window the driver was classified at the track, with `n_years` recorded.
- **Team version:** identical arithmetic on **team** entries — `baseline_finish(team, y)`
  is the mean classified finish of the team's cars across the season; the track value is
  the team's mean classified finish at the track that year; the delta and affinity follow.
  Team affinity reveals track-specific **car** strength.

### 7.2 Grid (qualifying) cross-check

The same overperformance arithmetic computed on **grid position** instead of finishing
position (`baseline_grid`, `track_delta_grid`, etc.). Grid has **no DNF noise** (everyone
starts) and is a pure one-lap-pace proxy, keeping method-consistency with Chapter 1. The
notebook reports affinity on **both** finish and grid; agreement between them strengthens
a claim, disagreement is flagged. Grid is unavailable for some very old/edge rounds; such
rows are dropped from the grid view only.

### 7.3 "Driver track vs car track" characterization (the Antonelli payoff)

To classify a track as more *driver-* or *car-*dependent (so we can say what an Antonelli
win there is worth):

- **Preferred test — does it follow the driver or the seat?** For drivers in the window
  who drove for **≥2 different teams**, check whether their track overperformance tracks
  *driver identity* (same driver overperforms here across different cars → driver track)
  or *team identity* (overperformance stays with the team as drivers cycle through →
  car track). Reported where enough team-switchers have track data; honest small-n note
  otherwise.
- **Supporting descriptive view:** compare the spread/magnitude of the top **driver**
  affinities vs the top **team** affinities at the track. A track where a few teams own a
  large, persistent positive delta (and drivers don't carry it between teams) reads as a
  **car track**; a track where specific drivers carry a positive delta across different
  cars reads as a **driver track**.

This stays descriptive arithmetic + a clearly-caveated qualitative call — **no fitted
model** — consistent with project rigor. Monaco's result (driver vs car) is the
centerpiece narrative beat.

### 7.4 Antonelli tie-in

Compute the **same** overperformance metric for Antonelli himself (2025 rookie year +
2026) at each 2026 track and place him on the track's board. The synthesis: at the tracks
he is winning, is he overperforming the Mercedes/season baseline (driver signal), and are
those tracks the historically driver-dependent ones? His sample is tiny (1–2 years) —
stated plainly as a directional, not conclusive, signal.

### 7.5 `src/track_history.py` function signatures

```python
def load_results(year: int, track: str) -> pd.DataFrame:
    """Results-only load of one race (R) session: classified position, grid,
    driver code, team, status. No telemetry/laps. Cached."""

def season_table(year: int) -> pd.DataFrame:
    """All rounds of a season as tidy rows (round, track, driver, team, grid,
    finish, classified) — the basis for season baselines. Results-only."""

def driver_track_affinity(track: str, years: list[int],
                          metric: str = "finish") -> pd.DataFrame:
    """Per driver: mean overperformance vs own-season baseline at `track`
    across `years`, plus n_years. metric in {'finish','grid'}. DNF rounds
    excluded for metric='finish'. Sorted best-to-worst."""

def team_track_affinity(track: str, years: list[int],
                        metric: str = "finish") -> pd.DataFrame:
    """As above, aggregated by team — track-specific car strength."""

def track_leaderboard(track: str, years: list[int]) -> pd.DataFrame:
    """Raw 'who owns this track' board: wins, podiums, mean finish, mean grid,
    n_starts per driver over the window (accessible hook, NOT car-controlled)."""

MIN_TRACK_YEARS = 3  # drivers/teams with fewer years at the track are flagged small-n
```

`season_table` is computed once per year and reused across `track`/metric calls within a
notebook run (cache the per-year frames in the notebook to avoid reloading every season
for every track).

### 7.6 Plots (in `src/plotting.py`, matching existing contract)

- `plot_track_affinity(affinity_df, save_path=None)` — horizontal bar leaderboard of
  driver (or team) overperformance at a track; positive (better-than-baseline) to the
  right; small-n entries visually de-emphasized; Antonelli highlighted when present.
- `plot_driver_vs_car_spread(driver_df, team_df, save_path=None)` — side-by-side view
  contrasting top driver affinities vs top team affinities at the track (the
  driver-track / car-track read).
- `plot_track_summary(summary_df, save_path=None)` — the compact 6-track season summary:
  per 2026 track, its driver-vs-car character and Mercedes' historical standing, with
  Antonelli's own overperformance marked.

All follow the repo contract: take a tidy df, optional `save_path`, return `fig`, no
FastF1 imports, 150 dpi, `bbox_inches='tight'`, hidden top/right spines.

## 8. Refresh workflow (the standing constraint)

`scripts/refresh.py` — one command brings the project current after any race:

1. Read the single `RACES` list (and the historical `years` window).
2. For each 2026 race, ensure the Q and R sessions are cached; fetch if missing.
3. Execute `notebooks/01`, `02`, `03` in order via nbconvert (`--execute --inplace`,
   600s timeout each).
4. Regenerate the no-input and with-code PDFs for each notebook (match the existing
   PDF route; fall back as the prior plan notes if LaTeX is unavailable).
5. Print a summary of what was fetched/regenerated.

The README gains an **"Updating after a new race"** section: add the new track string to
`RACES` in `src/season.py` (the **single** edit point), run `python scripts/refresh.py`,
commit. The figures and PDFs are the regenerated artifacts. Both notebooks and the refresh
script import `RACES` (and the default `years` window) from `src/season.py`, so there is
exactly **one** place to edit per new race.

## 9. Data flow

```
                ┌─ Ch1: loaders → segments/benchmarks → qualifying figs
RACES (1 list) ─┼─ Ch2: race.load_race_session → get_clean_laps → start/pace/tire/gap → race figs
                └─ Ch3: track_history.season_table(year)*  ─┐
                                                            ├─ driver/team_track_affinity → affinity figs
years window ──────────────────────────────────────────────┘   track_leaderboard → raw board
scripts/refresh.py orchestrates: fetch missing → execute 01/02/03 → regenerate figs + PDFs
```

## 10. Testing

Light footprint, invariants on real cached data (the repo's "a handful of meaningful
tests" philosophy), no brittle magic-number asserts except deliberate regression anchors.

**`tests/test_race.py`** (per 2026-05-29 plan §6) plus:
- **Monaco anchor:** ANT lap-1 position == 1 and final position == 1 (pole → win).
- (existing) **Canada anchor:** ANT lap-1 == 2, final == 1.

**`tests/test_track_history.py`:**
- **Overperformance invariant:** for a sampled classified driver-year,
  `track_delta_finish == baseline_finish − finish` (the definition holds).
- **DNF exclusion:** a driver-year with a DNF round has that round absent from its
  baseline (baseline computed only over classified rounds).
- **Small-n guard:** drivers/teams with `n_years < MIN_TRACK_YEARS` are flagged (not
  silently ranked as if robust).
- **Sign convention:** a driver who finishes better than baseline yields a positive
  affinity.
- **Reusability:** `driver_track_affinity('Monaco', years)` and a second track both
  return the documented columns.

Tests skip cleanly if the historical cache is not populated (mirroring the existing
cache-gated test).

## 11. Deliverables & what changes

### New files
- `src/race.py`, `tests/test_race.py` (Ch2, per 2026-05-29 plan, Monaco-extended).
- `src/track_history.py`, `tests/test_track_history.py` (Ch3).
- `notebooks/02_how_antonelli_wins_races.ipynb` (+ with-code & no-code PDFs).
- `notebooks/03_driver_vs_car_track_history.ipynb` (+ with-code & no-code PDFs).
- `src/season.py` (single source of truth: `RACES` + default `years`) and `scripts/refresh.py`.
- New figures: `start_conversion.png`, `stint_pace.png`, `gap_trace.png`, `tire_deg.png`,
  `track_affinity_monaco.png`, `driver_vs_car_monaco.png`, `track_summary.png`.

### Modified files
- `README.md` — reframed around the single thesis; race record (5 of 6); three chapters
  with figures inlined; qualifying demoted to Ch1; "Updating after a new race" section;
  honest-accounting section updated (Canada DNF context, Monaco, synthetic-data note for
  Ch3, all small-n caveats). Every hard-coded "four rounds"/"4 rounds" → six; monotone
  trajectory bullet replaced with the recomputed honest shape.
- `notebooks/01_antonelli_vs_russell.ipynb` — `RACES` through Monaco; corrected
  trajectory/category/corner/YoY prose (live numbers); regenerated figures + PDFs.
- `src/plotting.py` — 4 race plots + 3 track-history plots.
- Existing qualifying figures regenerated with R5+R6 data.
- `case_study.pdf` — regenerated to the new framing.

## 12. Limitations to state in the deliverables

- **6-race 2026 sample.** All 2026 findings directional. README keeps saying so.
- **Synthetic historical data** (Ch3): claims are "in this dataset", not real F1 history.
- **DNF handling** (Ch3): excluding DNF rounds removes reliability/luck from the affinity
  signal but also discards information; stated as a deliberate choice, with the grid
  cross-check as a DNF-free corroboration.
- **Small samples** (Ch3): drivers/teams below `MIN_TRACK_YEARS`, team-switcher counts,
  and Antonelli's 1–2 years are all flagged; the driver-vs-car call is qualitative.
- **Roster/era drift** across a 16-season window: the field changes; the metric is
  within-season-relative (baseline per year) which mitigates but does not eliminate this.
- Carry-over qualifying caveats (Q-session timing, traffic, tire age, setup divergence,
  telemetry sensor freezes) and race caveats (no fuel/strategy correction, SC/VSC
  excluded) from the prior specs.

## 13. Open questions / risks

- **Monaco fetch on first run.** The refresh script must fetch Monaco's Q and R the first
  time; confirmed available. The deep historical window also triggers many results-only
  downloads on first Ch3 run (fast, but not free) — `scripts/refresh.py` should report
  progress and the README should note the first run is slower.
- **Team identity over 16 years** (Ch3): team names change (rebrands/ownership). Decide
  during implementation whether to map historical team names to a canonical lineage or
  treat each `TeamName` string as-is; the honest default is as-is, with a caveat, unless
  a rebrand obviously splits one team's history.
- **Title wording** for the README H1 is finalized during the rewrite; working title:
  "Separating the Driver from the Car: How Good Is Kimi Antonelli, Really?"
