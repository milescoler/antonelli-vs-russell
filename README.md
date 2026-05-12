# Antonelli vs Russell: A Segment-Level Look at the 2026 Mercedes Rookie

**Where is Kimi Antonelli closing the gap to George Russell, and where is he still losing time?**

This project compares the two Mercedes drivers' qualifying laps across the 2026 season, broken down by track segment. Same car, same engineers — so the differences are about the drivers.

---

## Headline findings

After the first 4 rounds of 2026:

- **Lap-time gap to Russell:** {TBD} seconds on average across qualifying.
- **Where Antonelli loses time:** {TBD — e.g. "slow-speed corners, particularly braking-zone entries"}.
- **Where he's already competitive:** {TBD — e.g. "high-speed sections; the gap closes to near zero in fast corners"}.
- **Trajectory:** {TBD — e.g. "the gap has narrowed by ~30% from Round 1 to Round 4"}.

![Headline chart: per-segment time delta across four races](figures/headline_segment_delta.png)

---

## Why teammate comparison

Driver-vs-field comparisons in F1 are dominated by car performance. A Mercedes driver beating the midfield median tells you about the W17, not the driver.

Comparing teammates controls for that. Same chassis, same power unit, same engineering team, same tire allocation. What's left is mostly driver — with caveats covered in [Limitations](#limitations).

---

## Method

**Data:** FastF1 telemetry for the 2026 qualifying sessions of {race list}. Each driver's fastest valid lap is used.

**Segmentation:** Track segments are auto-generated from FastF1's `circuit_info.corners`, grouping nearby corners into single segments (default threshold: 250m). This produces 12-20 segments per circuit.

**Time delta:** Both drivers' speed traces are resampled onto a uniform 5m distance grid. Time per step is `Δd / speed`. Segment time is the sum of step times within each segment's distance bounds. Segment delta is `Russell_time − Antonelli_time` (positive = Antonelli faster).

**Sanity check:** The sum of segment deltas across a lap is verified to match the actual lap-time delta within 0.1s. Larger discrepancies indicate a bug.

---

## Project structure

```
antonelli-vs-russell/
├── README.md
├── requirements.txt
├── notebooks/
│   └── 01_antonelli_vs_russell.ipynb     # main analysis
├── src/
│   ├── loaders.py        # FastF1 session, lap, telemetry loading
│   ├── benchmarks.py     # teammate comparison logic
│   ├── segments.py       # circuit segmentation + time-delta math
│   └── plotting.py       # styled chart helpers
├── figures/              # exported PNGs used in this README
└── tests/
    └── test_segments.py  # lap-delta consistency check
```

---

## Reproducing

```bash
git clone https://github.com/{your-handle}/antonelli-vs-russell.git
cd antonelli-vs-russell
pip install -r requirements.txt
jupyter lab notebooks/01_antonelli_vs_russell.ipynb
```

First run downloads ~{X}MB of FastF1 session data into `./fastf1_cache/` (gitignored). Subsequent runs are local and fast.

Tested with FastF1 {version}, Python 3.12.

---

## Limitations

A short list of what this analysis does _not_ control for:

- **Sample size.** {N} qualifying sessions. Findings are directional, not conclusive.
- **Q-session timing.** Q1, Q2, Q3 happen on an evolving track. If one driver's best lap is in Q3 and the other's is in Q2, track conditions differ. The notebook flags these cases.
- **Traffic.** Out-laps, in-laps, and other cars on track affect achievable lap time.
- **Tire age within Q.** Same compound, but tire-age within a Q-session run can differ by a few laps.
- **Setup divergence.** Mercedes drivers don't always run identical setups. Public data can't distinguish driver delta from setup delta.

These caveats matter. The project is a careful look at what the available telemetry shows, not a definitive verdict on relative driver skill.

---

## What's next

- Extend across the rest of the 2026 season as races complete.
- Add race-pace comparison (stint-level, fuel-corrected) once enough race data accumulates.
- Compare Antonelli's rookie progression to other recent Mercedes rookies (Russell 2022, Hamilton 2007) using the same segment-delta framework.

---

## About

Built by Cole Richards. UCLA Statistics & Data Science, June 2026. [Portfolio](https://milescoler.github.io) · [LinkedIn]({TBD})

Data via [FastF1](https://github.com/theOehrly/Fast-F1) by Philipp Schaefer. Not affiliated with Formula 1 or Mercedes.
