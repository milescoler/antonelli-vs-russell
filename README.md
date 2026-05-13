# Antonelli vs Russell: A Segment-Level Look at the 2026 Mercedes Rookie

**Antonelli has overtaken Russell on qualifying pace. How is he winning?**

I built this to dig into Kimi Antonelli's 2026 season racing for Mercedes by comparing his qualifying laps to George Russell's, broken down by track segment. They're driving the same car, with the same team of engineers — so the differences are mostly about the drivers (with caveats covered in [Limitations](#limitations)).

---

## Headline findings

After the first 4 rounds of 2026:

- **Antonelli has overtaken Russell.** He was 0.29 s slower at Australia (R1) but has been faster every round since, with the margin growing each race: R2 +0.22 s → R3 +0.30 s → R4 +0.40 s. The four-race mean is +0.16 s in his favour, but across the 4 races there is a clear monotone trend.
- **Where Antonelli loses time:** medium-speed corners (130–200 kph), at −0.14 s/lap on average — a small but consistent deficit. *(An earlier version of this finding put the medium-corner gap at −0.46 s/lap, but it turned out two Japan segments had a frozen telemetry sensor that misclassified them; see [Limitations](#limitations).)*
- **Where he's gaining the most:** straights, **+0.17 s/lap** — the largest and most consistent positive across all four rounds. Fast corners (>200 kph) and slow corners (<130 kph) are essentially level with Russell (−0.003 s and +0.009 s respectively).
- **Trajectory:** the gap has shifted in Antonelli's favour every single round — from −0.29 s (Russell faster) at Australia to +0.40 s (Antonelli faster) at Miami, a monotone swing of 0.69 s across four rounds.

![Headline chart: per-segment time delta across four races](figures/headline_segment_delta.png)

For a finer-grained view, the figure below maps the local time-delta slope onto each circuit. **Blue** = Antonelli is gaining on Russell at that part of the track; **red** = Russell is gaining on Antonelli. Corner numbers are overlaid for orientation.

![Track-map: where each driver gains time across the lap](figures/track_delta_map.png)

---

## Why teammate comparison

Driver-vs-field comparisons in F1 are dominated by car performance. A Mercedes driver beating the midfield median tells you about the W17, not the driver.

Comparing teammates controls for that. Same chassis, same power unit, same engineering team, same tire allocation. What's left is mostly driver — with caveats covered in [Limitations](#limitations).

---

## Method

**Data:** FastF1 telemetry for the 2026 qualifying sessions of the Australian, Chinese, Japanese and Miami Grands Prix. Each driver's fastest valid lap is used.

**Segmentation:** Track segments are auto-generated from FastF1's `circuit_info.corners`, grouping nearby corners into single segments (default threshold: 250m). This produces 12-20 segments per circuit.

**Time delta:** Both drivers' telemetry — including FastF1's per-sample `Time` channel — is resampled onto a uniform 5m distance grid. Segment time is read directly from that resampled `Time` channel as `Time[last_step] − Time[first_step]` within the segment's distance bounds. Segment delta is `Russell_time − Antonelli_time` (positive = Antonelli faster).

_An earlier version of the analysis integrated `Δd / speed` per step instead. On 2 of the 4 races the accumulated residual exceeded the 0.1s sanity-check threshold below, so the method switched to reading FastF1's sample times directly. Residuals are now ≤ 0.1s on all four races — see the notebook's sanity-check section._

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

First run downloads ~411 MB of FastF1 session data into `./fastf1_cache/` (gitignored). Subsequent runs are local and fast.

After install, verify the math wires correctly:

```bash
pytest tests/
```

Tested with FastF1 3.8.1, Python 3.12.

---

## Limitations

A short list of what this analysis does _not_ control for:

- **Sample size.** 4 qualifying sessions. Findings are directional, not conclusive.
- **Q-session timing.** Q1, Q2, Q3 happen on an evolving track. If one driver's best lap is in Q3 and the other's is in Q2, track conditions differ. The notebook flags these cases.
- **Traffic.** Out-laps, in-laps, and other cars on track affect achievable lap time.
- **Tire age within Q.** Same compound, but tire-age within a Q-session run can differ by a few laps.
- **Setup divergence.** Mercedes drivers don't always run identical setups. Public data can't distinguish driver delta from setup delta.
- **Telemetry sensor freezes.** FastF1's car telemetry occasionally stops reporting changes for long stretches — Antonelli's Japan lap is the clearest case in this dataset, with the speed sensor stuck at 189 kph from ≈ 4000 m to the end of the lap. When that happens, integrated `Distance`, `Speed`, and the X/Y trajectory all become unreliable in the affected segments. Lap-level and sector-level deltas are unaffected (those come from timing-line beams, independent of the car telemetry), and I checked Japan's sector splits to confirm Antonelli's +0.30 s lap advantage is real. The notebook detects sensor freezes by checking unique-`Speed`-value counts per segment, lists which segments were flagged, and excludes them from the category headline.

These caveats matter. I treated this as a careful look at what the available telemetry shows, not a definitive verdict on relative driver skill.

---

## What I'd build next

- Extend across the rest of the 2026 season as races complete.
- Add race-pace comparison (stint-level, fuel-corrected) once enough race data accumulates.
- Compare Antonelli's rookie progression to other recent Mercedes rookies (Russell 2022, Hamilton 2007) using the same segment-delta framework.

---

## About

I'm Cole Richards — UCLA Statistics & Data Science, June 2026. [Portfolio](https://milescoler.github.io)

Data via [FastF1](https://github.com/theOehrly/Fast-F1) by Philipp Schaefer. Not affiliated with Formula 1 or Mercedes.
