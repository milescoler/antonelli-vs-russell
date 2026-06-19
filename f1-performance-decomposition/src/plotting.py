"""All figures. Pure rendering - it consumes artefacts, never recomputes them.

Style is deliberately plain: this is an analysis for a technical reader, so the
charts privilege legibility of the numbers over decoration.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # headless / reproducible
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

SIG_COLOR = "#1b7837"          # advantage distinguishable from zero
NOISE_COLOR = "#b3b3b3"        # within noise
A_COLOR = "#d1495b"
B_COLOR = "#2e7da6"


def _save(fig, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_cumulative_delta(grid, delta, edges, corner_distances=None,
                          driver_a=None, driver_b=None,
                          out_path=None) -> Path:
    """The core artefact: running gap vs distance, sectors/corners annotated."""
    driver_a = driver_a or config.DRIVER_A
    driver_b = driver_b or config.DRIVER_B
    out_path = out_path or (config.FIGURES_DIR / "cumulative_delta.png")

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.axhline(0, color="k", lw=0.8)
    ax.plot(grid, delta, color="#333333", lw=1.8)
    ax.fill_between(grid, 0, delta, where=(delta >= 0), color=A_COLOR, alpha=0.18)
    ax.fill_between(grid, 0, delta, where=(delta < 0), color=B_COLOR, alpha=0.18)

    for x in edges:
        ax.axvline(x, color="0.85", lw=0.6, zorder=0)
    if corner_distances is not None:
        for i, cd in enumerate(np.asarray(corner_distances), start=1):
            if 0 < cd < grid[-1]:
                ax.axvline(cd, color="0.6", lw=0.5, ls=":", zorder=0)
                ax.text(cd, ax.get_ylim()[1], f"T{i}", fontsize=7,
                        ha="center", va="bottom", color="0.4")

    endpoint = float(delta[-1])
    ax.annotate(f"finish: {endpoint:+.3f} s",
                xy=(grid[-1], endpoint), xytext=(-10, 10),
                textcoords="offset points", ha="right", fontsize=9)
    ax.set_xlabel("Distance around lap (m)")
    ax.set_ylabel(f"Cumulative delta (s)\n+ = {driver_a} slower / {driver_b} faster")
    ax.set_title(f"Cumulative time delta: {driver_a} - {driver_b}")
    return _save(fig, out_path)


def plot_sector_bars(sector_table: pd.DataFrame,
                     driver_a=None, driver_b=None, out_path=None) -> Path:
    """Per-micro-sector delta with bootstrap CIs, coloured by significance."""
    driver_a = driver_a or config.DRIVER_A
    driver_b = driver_b or config.DRIVER_B
    out_path = out_path or (config.FIGURES_DIR / "sector_deltas.png")

    t = sector_table.sort_values("sector")
    x = t["sector"].to_numpy()
    y = t["delta_s_mean"].to_numpy()
    lo = y - t["ci_low"].to_numpy()
    hi = t["ci_high"].to_numpy() - y
    colors = [SIG_COLOR if s else NOISE_COLOR for s in t["significant"]]

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.axhline(0, color="k", lw=0.8)
    ax.bar(x, y, color=colors, edgecolor="0.3", linewidth=0.4)
    ax.errorbar(x, y, yerr=[lo, hi], fmt="none", ecolor="0.25",
                elinewidth=1.0, capsize=2)
    ax.set_xticks(x)
    ax.set_xlabel("Micro-sector")
    ax.set_ylabel(f"Delta (s)  + = {driver_a} slower")
    ax.set_title(f"Per-micro-sector delta with {int(config.CONFIDENCE*100)}% bootstrap CI")
    handles = [plt.Rectangle((0, 0), 1, 1, color=SIG_COLOR),
               plt.Rectangle((0, 0), 1, 1, color=NOISE_COLOR)]
    ax.legend(handles, ["CI excludes 0 (real)", "within noise"], fontsize=8)
    return _save(fig, out_path)


def plot_input_overlays(top_sectors: pd.DataFrame,
                        repr_a: pd.DataFrame, repr_b: pd.DataFrame,
                        driver_a=None, driver_b=None, out_path=None) -> Path:
    """Speed / throttle / brake / gear overlays at the key micro-sectors."""
    driver_a = driver_a or config.DRIVER_A
    driver_b = driver_b or config.DRIVER_B
    out_path = out_path or (config.FIGURES_DIR / "input_overlays.png")

    sectors = list(top_sectors.itertuples(index=False))
    n = max(len(sectors), 1)
    fig, axes = plt.subplots(4, n, figsize=(4.2 * n, 9), sharex="col", squeeze=False)
    channels = [("Speed", "Speed (km/h)"), ("Throttle", "Throttle (%)"),
                ("Brake", "Brake"), ("nGear", "Gear")]

    for j, sec in enumerate(sectors):
        s, e = float(sec.start_m), float(sec.end_m)
        for i, (ch, label) in enumerate(channels):
            ax = axes[i][j]
            for rep, name, col in ((repr_a, driver_a, A_COLOR), (repr_b, driver_b, B_COLOR)):
                d = rep["Distance"].to_numpy()
                m = (d >= s) & (d <= e)
                ax.plot(d[m], rep[ch].to_numpy()[m], color=col, lw=1.4, label=name)
            if i == 0:
                ax.set_title(f"Sector {int(sec.sector)}  ({sec.delta_s_mean:+.3f}s)",
                             fontsize=9)
                ax.legend(fontsize=7)
            if j == 0:
                ax.set_ylabel(label)
            if i == 3:
                ax.set_xlabel("Distance (m)")
    fig.suptitle("Driver-input traces at the key micro-sectors", y=1.0)
    return _save(fig, out_path)


def plot_track_map(repr_lap: pd.DataFrame, grid, delta, out_path=None) -> Path:
    """Track map (X/Y) coloured by local rate of time gain/loss (d delta / dx)."""
    out_path = out_path or (config.FIGURES_DIR / "track_map.png")
    d = repr_lap["Distance"].to_numpy()
    x = repr_lap["X"].to_numpy()
    y = repr_lap["Y"].to_numpy()
    rate = np.gradient(np.interp(d, grid, delta), d)   # s per m, signed

    fig, ax = plt.subplots(figsize=(7, 7))
    sc = ax.scatter(x, y, c=rate, cmap="coolwarm", s=8,
                    vmin=-np.nanpercentile(np.abs(rate), 98),
                    vmax=np.nanpercentile(np.abs(rate), 98))
    cb = fig.colorbar(sc, ax=ax, shrink=0.8)
    cb.set_label("local time rate (s/m)  red = A losing")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Where time is gained / lost around the lap")
    return _save(fig, out_path)
