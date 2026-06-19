# What Won the Race?

**For a given F1 race, decompose the winning margin (winner vs P2) into four causes and issue a verdict on each.** This is an outcome-attribution problem under uncertainty — F1 is the worked example; the method is the point.

> **Live tool:** [milescoler.github.io/antonelli-vs-russell](https://milescoler.github.io/antonelli-vs-russell/)
> **Method write-up:** [`f1-performance-decomposition/REPORT.md`](f1-performance-decomposition/REPORT.md)

---

## The Four Factors

| Factor | Question | Verdict options |
|--------|----------|-----------------|
| **Where on track / which laps** | Which corners or stint windows actually built the gap? | Real / Noise / Insufficient data |
| **Tyre strategy & degradation** | Did one driver gain from undercut, overcut, or slower tyre wear? | Real / Noise / Inherited / Insufficient data |
| **Race pace** | On comparable laps (same compound, similar tyre age), who was faster? | Real / Noise / Insufficient data |
| **Start & track position** | Did the result turn on grid slot, a lap-1 move, or traffic that never cleared? | Real / Noise / Inherited |

---

## The Method

**Comparable laps** — race pace is read only across matching compounds at similar tyre age. No apples-to-oranges stint comparisons.

**Bootstrap CIs** — the where-on-track factor uses 5,000 resamples to put confidence intervals on each track sector. A sector earns a "real" verdict only when the CI excludes zero. Stints under five clean laps report no verdict rather than a noisy number.

**Per-driver reconciliation** — each factor is cross-checked so verdicts are consistent (e.g., a pace verdict of "noise" can't coexist with a pace-derived gap being called "real").

**Honest exclusion** — safety-car and VSC laps are excluded. Fuel load is named but not modelled. Claims are "in this dataset," not real-world F1 history.

---

## Findings — Proof the Method is Honest

**Monaco** — clean pole-to-flag win; multiple factors ruled **real** (pace, tyre management, track position all pointed the same direction). The clearest "everything aligned" case.

**Canada** — Antonelli's win was **inherited**. Polesitter Russell led until his DNF on lap 2; the tool says so explicitly rather than crediting a pass that didn't happen.

**Japan** — Antonelli won from pole despite dropping **five places on lap 1**, then recovering. Real data; the tool traces exactly which laps recovered which positions and verdicts them **real**.

**Australia** — the winner was actually **slower on race pace**. Track position, not outright speed, decided it. The tool calls this out rather than attributing the win to pace it can't find.

---

## Measurement Discipline

The clearest proof the method is honest: an early telemetry pass at Japan found large per-sector deltas that turned out to be a **frozen speed sensor** — a freeze-detection filter collapsed them to ~0. Catching that, and knowing when you *haven't* found real signal, is the whole skill.

The sensor-freeze detection is documented in [`f1-performance-decomposition/REPORT.md`](f1-performance-decomposition/REPORT.md).

---

## Project Structure

```
f1_project/
├── README.md
├── requirements.txt
├── f1-performance-decomposition/   # engine: decomposition method + REPORT.md
├── scripts/
│   └── build_race_decomp_data.py  # fetch + build all race JSON
├── src/                            # shared loaders, filters, bootstrap logic
├── web/                            # React/Vite interactive tool (Tailwind + Recharts)
│   ├── src/pages/RaceDecomp.tsx   # main decomposition view
│   └── src/pages/About.tsx        # method + findings summary
└── tests/                         # invariant tests
```

---

## Reproducing

```bash
git clone https://github.com/milescoler/antonelli-vs-russell.git
cd f1_project
pip install -r requirements.txt
python scripts/build_race_decomp_data.py   # fetch sessions, build race JSON
pytest tests/                              # invariant checks
# Web (dev):
cd web && npm install && npm run dev
```

Tested with FastF1 3.8.x, Python 3.12. The first run downloads session data into `./fastf1_cache/` (gitignored); subsequent runs are local.

---

## Limitations

- **Sample size.** Findings are directional, not conclusive — each race is a single data point.
- **Fuel load.** Not corrected. Stint-pace comparisons reflect on-track conditions, not a corrected baseline.
- **Synthetic historical data.** The data source is internally consistent but not real-world F1. Every claim is "in this dataset."
- **Small-stint exclusion.** Stints under five clean laps return no pace verdict rather than a noisy one.
- **Telemetry sensor freezes.** A sliding-window freeze-detection filter excludes corrupted sectors (Japan qualifying is the documented case).

---

## About

I'm Cole Richards — UCLA Statistics & Data Science, June 2026. [Portfolio](https://milescoler.github.io)

Data via [FastF1](https://github.com/theOehrly/Fast-F1). Not affiliated with Formula 1 or Mercedes.
