# F1 Lap-Time Performance Decomposition

**Given that one driver is faster over a lap, *where* on the track does the gap
come from — and is it a real, repeatable advantage or just lap-to-lap noise?**

A single lap-time gap ("0.3 s faster") is an aggregate that hides everything
interesting. This project decomposes that gap **spatially** (a cumulative
time-delta curve, sliced into micro-sectors) and quantifies it **statistically**
(bootstrap confidence intervals per micro-sector), then attributes the cause to
specific driver inputs — braking point, apex speed, throttle application.

Configured out of the box for **Russell vs Antonelli, 2026 Canada qualifying** —
two team-mates in the same car (~0.07 s apart on the grid), so the machinery is
divided out and what's left is (mostly) the driver. Swap the matchup in
`config.py`.

> The full narrative write-up — Question → Method → Findings → Recommendation →
> Threats to validity — is in **[`REPORT.md`](REPORT.md)**.

---

## Why I built this

The transferable skill here is **signal extraction from noisy, irregularly
sampled time series, with honest uncertainty** — the same problem shape as a
diagnostic readout or an instrument trace, just dressed as motorsport:

- **Align before you compare.** Two traces sampled on different clocks can't be
  compared sample-by-sample; you resample both onto a common physical axis
  (here, distance) first. This is the same discipline as putting two assays on a
  common reference grid before differencing them.
- **Reconcile against ground truth.** The decomposed curve must sum back to the
  officially measured lap-time gap (to 0.05 s) or the method is wrong — a hard,
  automated correctness gate, not a vibe check.
- **Separate effect from noise, and say which is which.** A point estimate
  without an interval is an opinion. The headline deliverable flags which
  per-sector "advantages" survive a bootstrap and which are within noise —
  including at least one that *looked* like an edge and isn't.

The motorsport framing is a vehicle; the measurement discipline is the point.

---

## What it produces

- **Cumulative time-delta curve** vs distance, with corners/sectors annotated.
- **Per-micro-sector delta bar chart** with 95% bootstrap CIs, coloured by
  whether the interval excludes zero (real vs noise).
- **Input-trace overlays** (speed / throttle / brake / gear) at the key sectors.
- **Track map** coloured by where time is gained/lost.
- **Ranked micro-sector table** (CSV) with deltas, CIs, and significance flags.
- An auto-populated **Findings** section injected into `REPORT.md`.

---

## Setup & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Live: fetches official timing/telemetry via FastF1 (network needed once;
# results are cached to ./fastf1_cache/ so reruns are offline & fast).
python -m src.run

# Offline demo / CI: runs the whole pipeline on a synthetic two-driver fixture
# with a known ground truth (no network).
python -m src.run --synthetic

pytest -q        # invariants incl. the reconciliation gate, all offline
```

Figures land in `outputs/figures/`, tables in `outputs/tables/`, and the
findings are injected into `REPORT.md`. To re-point the analysis, edit
`config.py` (year, Grand Prix, session, the two driver codes, grid resolution,
micro-sector count, bootstrap iterations, seed).

> **Note on environments without F1 network access.** FastF1's data servers must
> be reachable for a live run. Where they aren't (e.g. locked-down CI), use
> `--synthetic` and `pytest` — the full methodology, including the reconciliation
> gate and the signal-vs-noise bootstrap, runs against the fixture.

---

## Repository layout

```
f1-performance-decomposition/
├── config.py              # race, session, drivers, grid, n_sectors, bootstrap — single edit point
├── src/
│   ├── data_loading.py    # FastF1 cache/session + clean-lap selection (only module that hits FastF1)
│   ├── resampling.py      # distance-grid construction + channel interpolation
│   ├── delta.py           # cumulative time-delta curve + micro-sector decomposition + reconciliation
│   ├── stats.py           # bootstrap CIs + significance flags
│   ├── attribution.py     # driver-input comparison at the key micro-sectors
│   ├── plotting.py        # all figures
│   ├── synthetic.py       # offline fixture with a known ground truth (CI / demo)
│   └── run.py             # end-to-end orchestration  (python -m src.run)
├── notebooks/analysis.ipynb   # thin narrative run-through (logic lives in src/)
├── outputs/{figures,tables}/  # generated artefacts
├── tests/test_pipeline.py     # reconciliation gate + resampling/stats invariants
├── REPORT.md              # the narrative analysis
└── requirements.txt
```

Logic lives in `src/`; the notebook only imports and narrates.

---

*Built by Cole Richards — UCLA Statistics & Data Science. Data via
[FastF1](https://github.com/theOehrly/Fast-F1). Not affiliated with Formula 1 or
Mercedes.*
