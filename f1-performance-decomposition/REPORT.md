# Where does a lap-time gap come from — and is it real?

**A spatial + statistical decomposition of one qualifying lap-time gap between two team-mates.**

> Configured for **Russell (RUS) vs Antonelli (ANT)**, 2026 Canada qualifying (see `config.py`).
> The numbers in *Findings* below are written by the pipeline (`python -m src.run`);
> everything else is the fixed analysis design.

---

## 1. Question

When one driver is 0.3 s faster over a lap, that single number hides everything
interesting. This project answers two linked questions:

1. **Where on the track** does the gap come from — which corners, and on entry,
   mid-corner, or exit?
2. **Is the gap real?** Is each local advantage a repeatable edge, or just the
   lap-to-lap scatter of a good lap against a bad one?

The second question is the point. A 0.05 s "edge" with a ±0.15 s interval is
noise, and saying so is more valuable than a confident-sounding decomposition
that can't tell signal from luck.

Team-mates are chosen deliberately: same car, same session, so the machinery is
divided out and what remains is (mostly) the driver.

---

## 2. Method

### 2.1 Why a common *distance* grid (not time, not samples)

Telemetry is sampled irregularly in time (~10 Hz, jittered), and the two cars
cover the lap at different speeds, so their samples never line up — you cannot
compare them index-by-index or at equal times. The only physically meaningful
question is *"what is each driver doing at the same point on track?"* So every
channel of every lap is linearly interpolated onto one shared distance grid
(every `GRID_RESOLUTION_M` = 2 m, from 0 to lap length). Linear interpolation is
chosen over splines on purpose: it is shape-preserving and adds no spurious
oscillation, and at 2 m spacing the curvature between knots is negligible.

### 2.2 The cumulative time-delta curve (the core artefact)

For each driver we form a *time-at-distance* function `t(d)` and take

```
delta(d) = t_RUS(d) − t_ANT(d)
```

the running time gap as a function of distance. Two properties make this the
whole analysis in one curve:

- its **value at the finish line equals the total lap-time gap**;
- its **slope** is the *rate* of time gain/loss — a rising segment is where one
  driver is pulling away, which is what localises the advantage to a corner.

**Choice of time basis.** There are two valid ways to get `t(d)`:

| basis | what it is | why / why not |
|---|---|---|
| **`telemetry_time`** *(used)* | the car's own measured `Time` channel, interpolated onto distance | a direct measurement — no integration error from quantised speed |
| `speed_integral` | integrate `1/v` over distance | independent of the timing beam, so it's the **cross-check** |

We use `telemetry_time` and verify it against the `1/v` integral
(`test_two_time_bases_agree`): the two endpoints must agree to a few hundredths.

**Reconciliation gate.** The curve's finish-line value must equal the *official*
lap-time gap to within `RECONCILE_TOLERANCE_S` = 0.05 s. This is a correctness
test, not a finding — if it fails, the time basis is wrong, and the pipeline
**raises** rather than reporting a bogus decomposition
(`test_delta_endpoint_reconciles_with_official_gap`).

### 2.3 Micro-sectors

The lap is partitioned into ~15–25 micro-sectors. When FastF1 supplies corner
positions, boundaries are placed at the **midpoints between consecutive
corners**, so each sector brackets one corner with its braking zone and exit —
the way a driver actually experiences the lap. Otherwise we fall back to
equal-distance bins. The per-sector delta is the *change in `delta(d)` across the
sector*; by construction these contributions telescope to the curve endpoint
(`test_segment_contributions_telescope`).

### 2.4 Signal vs. noise — the bootstrap

A single lap can't separate a real advantage from a tidy lap. With several clean
laps per driver, each micro-sector has a **distribution** of deltas. We estimate
the per-sector mean delta with a **non-parametric bootstrap**: resample whole
laps with replacement (per driver, independently — the laps are not paired),
recompute the mean delta per sector, repeat `N_BOOTSTRAP` = 5,000 times, and take
the 2.5/97.5 percentiles as a 95% CI.

Bootstrap over a t-test because it is **assumption-light** — it makes no
normality claim about a handful of laps — and because "resample the laps we
happened to get and watch how much the answer wobbles" *is* the uncertainty we
care about and is explainable to a non-statistician. The seed is fixed
(`RANDOM_SEED`) so results are reproducible (`test_bootstrap_is_reproducible`).

**A sector's advantage is flagged real iff its 95% CI excludes zero.** Sectors
whose interval straddles zero are reported as noise — explicitly.

### 2.5 Driver-input attribution

At the largest *real* micro-sectors we overlay both drivers' Speed / Throttle /
Brake / Gear vs distance and read the cause along the corner phases:

- **Entry** — brake point (later braking → time gained into the corner);
- **Mid-corner** — minimum/apex speed (line and commitment);
- **Exit** — throttle-application point (earlier to full throttle → time onto
  the straight).

Each key sector gets one falsifiable sentence: *what* differs in the inputs and
*why* it produces the observed delta.

### 2.6 Confound control (§3.6)

| confound | control |
|---|---|
| **Fuel load** | use **qualifying**, where laps are flat-out and low-fuel; no fuel-burn trend within a run. |
| **Tyre compound / age** | clean-lap filter keeps representative flying laps; compound & tyre life are loaded and reported per lap so mismatches are visible. |
| **Track evolution** | qualifying laps sit close in time; the bootstrap treats remaining session drift as part of lap-to-lap variance. |
| **Traffic / track status** | drop in/out laps and non-accurate laps; keep only laps within `QUICKLAP_THRESHOLD` (107%) of the driver's own best (`pick_quicklaps`). Every dropped lap is logged with a reason. |

---

## 3. Findings

<!-- BEGIN AUTOGEN:findings -->
_This block is generated by `python -m src.run`. Run the pipeline (live FastF1
or `--synthetic`) to populate the official gap, the reconciliation residual, the
ranked micro-sector table with bootstrap CIs and significance flags, the
driver-input attribution for the key sectors, and the explicit "looked like an
edge but it's within noise" call-out._
<!-- END AUTOGEN:findings -->

---

## 4. What the slower driver should do

The decomposition turns into a concrete to-do list: the slower driver's losses
concentrate in the handful of micro-sectors flagged **real** above, and the
attribution names the phase (entry / mid-corner / exit) responsible. The
recommendation is to target those specific corners and that specific phase —
e.g. *carry more apex speed through the named mid-corner sector*, or *brake later
into the named entry sector* — rather than chasing the aggregate lap time. The
sectors flagged **noise** are explicitly *not* worth chasing: there is no
repeatable deficit there to fix.

*(The named corners and phases are filled in from the attribution table once the
pipeline has run.)*

---

## 5. Threats to validity

Named, not waved away:

- **Sample size.** A qualifying session yields only a few clean flying laps per
  driver. The bootstrap quantifies this honestly — small samples produce wide
  intervals, which is *why* several sectors land in "noise". More laps (e.g.
  practice) would tighten the CIs but reintroduce track-evolution drift.
- **Track evolution within the session.** Grip improves over qualifying; if the
  two drivers set their best laps at different times, some of a "real" delta is
  evolution, not driver. We mitigate by using flying laps close in time but do
  not model the grip trend.
- **Setup divergence.** Team-mates can run different wing levels / diff settings.
  That is a real driver-adjacent difference, not pure skill, and we do not
  separate it.
- **Single representative lap for the curve.** The cumulative curve uses each
  driver's fastest lap; the *stats* use all clean laps. Where the representative
  lap disagrees with the lap-mean delta (both reported), the fastest lap was
  somewhat unrepresentative — a flag, not a fix.
- **Telemetry sensor freezes.** FastF1 car telemetry occasionally stalls (speed
  stuck for a stretch). The clean-lap filter catches gross cases; subtle ones can
  bias a sector. Lap- and sector-level *timing-beam* deltas are unaffected, which
  is part of why the reconciliation gate is valuable.
- **Brake channel is coarse.** Brake is effectively on/off in the feed, so
  "brake point" is a position, not a pressure trace; entry attribution is
  directional.

---

*Built by Cole Richards. Data via [FastF1](https://github.com/theOehrly/Fast-F1).
Not affiliated with Formula 1 or Mercedes.*
