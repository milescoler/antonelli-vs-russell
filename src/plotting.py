"""
Styled chart helpers for the Antonelli-vs-Russell analysis. Plotting functions
take pre-shaped DataFrames — no FastF1 imports, no filesystem awareness.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CATEGORY_ORDER = ['slow_corner', 'medium_corner', 'fast_corner', 'straight']
CATEGORY_LABELS = {
    'slow_corner': 'Slow corners\n(<130 kph min)',
    'medium_corner': 'Medium corners\n(130–200 kph)',
    'fast_corner': 'Fast corners\n(>200 kph min)',
    'straight': 'Straights',
}


def plot_category_deltas(
    all_races_df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Headline chart: per-category mean delta across races, with each race
    overlaid as a small dot.

    Args:
        all_races_df: concatenated per-segment frames across all races.
            Required columns: category, delta_s, event_name.
        save_path: if given, save PNG to this path at 150 dpi.

    Returns:
        The matplotlib Figure.

    Sign convention: positive delta_s = driver A faster.
    """
    cats_present = [c for c in CATEGORY_ORDER if c in all_races_df['category'].unique()]
    means = (
        all_races_df.groupby('category')['delta_s']
        .mean()
        .reindex(cats_present)
    )
    fig, ax = plt.subplots(figsize=(9, 5.5))

    x = np.arange(len(cats_present))
    ax.bar(x, means.values, width=0.55, color='#1f77b4', alpha=0.85, zorder=2)
    ax.axhline(0, color='black', linewidth=0.8, zorder=1)

    # Per-race dots
    events = sorted(all_races_df['event_name'].unique())
    for i, cat in enumerate(cats_present):
        per_race = all_races_df[all_races_df['category'] == cat].groupby('event_name')['delta_s'].mean()
        ax.scatter(
            [i + 0.18] * len(per_race),
            per_race.values,
            color='black', s=22, zorder=3, alpha=0.7,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_LABELS[c] for c in cats_present])
    ax.set_ylabel('Time delta per category (s)\npositive → Antonelli faster')
    ax.set_title('Where does Antonelli gain or lose time vs Russell?\n2026 Qualifying, first 6 rounds')
    ax.grid(axis='y', linestyle='--', alpha=0.35, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def plot_corner_bucket_summary(
    corner_df: pd.DataFrame,
    save_path: Optional[Path] = None,
    real_braking_threshold_m: float = 20.0,
) -> plt.Figure:
    """
    Compact headline chart for the corner-cycle finding: a single grouped bar
    plot of brake-on Δ and throttle-full Δ vs Russell, grouped by corner-speed
    bucket. Each Δ is in meters; the sign convention matches the rest of the
    project — NEGATIVE means Antonelli's advantage (he brakes later or gets
    to full throttle sooner).

    Args:
        corner_df: output of compute_corner_signatures (one or more races
            concatenated). Required columns: mean_apex_kph, brake_on_a,
            brake_on_b, brake_on_delta, throttle_full_delta, sensor_ok.
        real_braking_threshold_m: drop corners where either driver braked
            less than this many meters before apex (flat-out kinks).
    """
    real = corner_df[
        corner_df['sensor_ok']
        & (corner_df['brake_on_a'] > real_braking_threshold_m)
        & (corner_df['brake_on_b'] > real_braking_threshold_m)
    ].copy()

    def bucket(v):
        if v < 100: return 'Very slow\n(<100 kph)'
        if v < 150: return 'Slow\n(100–150)'
        if v < 200: return 'Medium\n(150–200)'
        return 'Fast\n(≥200)'

    real['bucket'] = real['mean_apex_kph'].apply(bucket)
    order = ['Very slow\n(<100 kph)', 'Slow\n(100–150)',
             'Medium\n(150–200)', 'Fast\n(≥200)']
    means = real.groupby('bucket')[['brake_on_delta', 'throttle_full_delta']].mean().reindex(order)
    counts = real.groupby('bucket').size().reindex(order)

    x = np.arange(len(order))
    w = 0.36
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    bars_brake = ax.bar(
        x - w / 2, means['brake_on_delta'], w,
        color='#1f77b4', alpha=0.9, label='Brake-on Δ (m before apex)',
    )
    bars_thr = ax.bar(
        x + w / 2, means['throttle_full_delta'], w,
        color='#ff7f0e', alpha=0.9, label='Throttle-full Δ (m after apex)',
    )

    for bars in (bars_brake, bars_thr):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f'{h:+.0f} m',
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4 if h >= 0 else -14),
                textcoords='offset points',
                ha='center', va='bottom' if h >= 0 else 'top',
                fontsize=10, fontweight='medium',
            )

    ax.axhline(0, color='black', linewidth=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{lbl}\nn={counts[lbl]}' for lbl in order])
    ax.set_ylabel('Distance Δ vs Russell (m)')
    ax.set_title(
        'How is Antonelli winning?\n'
        'Brake-on and throttle-full timing Δ by corner-speed bucket  '
        '(negative = Antonelli\'s advantage)',
        fontsize=12,
    )

    ymin, ymax = ax.get_ylim()
    bound = max(abs(ymin), abs(ymax)) * 1.15
    ax.set_ylim(-bound, bound)
    ax.text(
        -0.45, bound * 0.9, '↑ Russell advantage',
        fontsize=9, color='#555', ha='left', va='top',
    )
    ax.text(
        -0.45, -bound * 0.9, '↓ Antonelli advantage',
        fontsize=9, color='#555', ha='left', va='bottom',
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.legend(loc='upper right', frameon=False, fontsize=10)

    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_corner_signatures(
    corner_df: pd.DataFrame,
    save_path: Optional[Path] = None,
    real_braking_threshold_m: float = 20.0,
    clip_y: float = 100.0,
) -> plt.Figure:
    """
    Two-panel scatter showing, per corner, where the brake-on and throttle-on
    timing differences between the two drivers live as a function of how fast
    the corner is. Each point = one corner (across all races).

    Args:
        corner_df: output of compute_corner_signatures, optionally concatenated
            across multiple races. Must contain mean_apex_kph, brake_on_delta,
            throttle_full_delta, sensor_ok, brake_on_a, brake_on_b, race.
        save_path: PNG output path (optional).
        real_braking_threshold_m: drop corners where either driver braked less
            than this many meters before apex (i.e., flat-out kinks).
        clip_y: cap the y-axis at ± this value to keep outliers visible but
            not stretching the scale.
    """
    real = corner_df[
        corner_df['sensor_ok']
        & (corner_df['brake_on_a'] > real_braking_threshold_m)
        & (corner_df['brake_on_b'] > real_braking_threshold_m)
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    races = sorted(real['race'].unique())
    cmap = plt.get_cmap('tab10')
    race_colors = {r: cmap(i) for i, r in enumerate(races)}

    for ax, col, ylabel, title in [
        (axes[0], 'brake_on_delta',
         'Brake-on Δ (m)\nnegative → Antonelli brakes LATER',
         'When does each driver start braking?'),
        (axes[1], 'throttle_full_delta',
         'Throttle-full Δ (m)\nnegative → Antonelli to full throttle SOONER',
         'When does each driver get back to full throttle?'),
    ]:
        for race in races:
            sub = real[real['race'] == race]
            ax.scatter(
                sub['mean_apex_kph'], sub[col].clip(-clip_y, clip_y),
                color=race_colors[race], s=55, alpha=0.8, label=race,
                edgecolors='black', linewidths=0.4,
            )
        ax.axhline(0, color='black', linewidth=0.8)
        ax.axvline(200, color='gray', linewidth=0.8, linestyle='--', alpha=0.7)
        ax.set_xlabel('Mean apex speed (kph)')
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.set_ylim(-clip_y, clip_y)
        ax.grid(linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[1].legend(loc='lower left', frameon=False, fontsize=9)
    fig.suptitle(
        'How is Antonelli winning? Brake / throttle timing by corner speed',
        fontsize=13,
    )
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_yoy_lap_deltas(
    tracks: list,
    deltas_2025: list,
    deltas_2026: list,
    *,
    save_path: Optional[Path] = None,
    flagged_2025: Optional[list] = None,
    flagged_2026: Optional[list] = None,
) -> plt.Figure:
    """
    Year-over-year lap-delta comparison: two lines, same 4 tracks, one point
    per (year, track). Positive = Antonelli faster than Russell.

    Args:
        tracks: list of track labels in calendar order, e.g. ['Australia', ...].
        deltas_2025, deltas_2026: lap_delta_s for each track, same order.
        flagged_2025, flagged_2026: optional list of bool (one per track);
            True marks a track where the comparison has a known caveat
            (e.g. Q-session mismatch, telemetry-quality issue). Flagged points
            are drawn with a hollow marker and asterisked label.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(tracks))

    def _plot_year(deltas, flagged, color, label, marker_style, linestyle):
        ax.plot(x, deltas, color=color, linewidth=2, linestyle=linestyle, zorder=2)
        if flagged is None:
            flagged = [False] * len(tracks)
        for xi, yi, fl in zip(x, deltas, flagged):
            ax.scatter(
                xi, yi, s=90, color=color, edgecolors=color,
                facecolors='white' if fl else color, linewidth=2, zorder=3,
                marker=marker_style,
            )
        # Single legend entry per year
        ax.plot([], [], color=color, marker=marker_style, linewidth=2,
                linestyle=linestyle, markersize=10, label=label)

    _plot_year(deltas_2025, flagged_2025, '#888888', '2025 (rookie year)',
               's', '--')
    _plot_year(deltas_2026, flagged_2026, '#1f77b4', '2026 (sophomore)',
               'o', '-')

    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(tracks)
    ax.set_ylabel('Lap-time delta (s)\npositive → Antonelli faster')
    ax.set_title(
        'Antonelli vs Russell — same 6 tracks, rookie year vs sophomore year'
    )
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=False)

    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_track_delta_map(
    x: np.ndarray,
    y: np.ndarray,
    slope: np.ndarray,
    corners: Optional[pd.DataFrame] = None,
    *,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    vmax: Optional[float] = None,
) -> tuple:
    """
    Track-shape (X/Y) view colored by the local slope of the cumulative time
    delta. Positive slope = driver A is gaining time at that part of the track;
    negative slope = driver B is gaining.

    Args:
        x, y: 1D arrays of equal length — the track coordinates from one
            driver's distance-grid-resampled telemetry.
        slope: 1D array, same length as x/y. Local d(delta_s)/d(distance)
            at each grid step. Sign convention matches delta_s: positive =
            driver A faster at that point.
        corners: optional DataFrame from FastF1 circuit_info.corners with
            columns Number, X, Y (and optionally Letter). Used to overlay
            corner-number labels at corner positions.
        ax: matplotlib Axes to draw into (created if None).
        title: subplot title.
        vmax: symmetric color limit. If None, uses the 95th percentile of
            abs(slope) to avoid one outlier saturating the scale.

    Returns:
        (ax, mappable) where mappable is the scatter PathCollection — pass
        it to fig.colorbar to add a shared colorbar across subplots.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 7))

    if vmax is None:
        vmax = float(np.percentile(np.abs(slope), 95)) or 1e-6

    mappable = ax.scatter(
        x, y, c=slope, cmap='RdBu', s=10,
        vmin=-vmax, vmax=vmax, edgecolors='none',
    )

    if corners is not None and len(corners) > 0:
        has_letter = 'Letter' in corners.columns
        for c in corners.itertuples():
            label = str(c.Number)
            if has_letter:
                ltr = getattr(c, 'Letter', None)
                if isinstance(ltr, str) and ltr.strip():
                    label = f"{c.Number}{ltr}"
            ax.annotate(
                label,
                xy=(c.X, c.Y),
                fontsize=7,
                ha='center', va='center',
                bbox=dict(boxstyle='circle,pad=0.18', fc='white',
                          ec='gray', lw=0.5, alpha=0.85),
                zorder=5,
            )

    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if title:
        ax.set_title(title, fontsize=11)

    return ax, mappable


def plot_lap_delta_by_round(
    meta_df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> plt.Figure:
    """
    Trajectory chart: total lap-time delta by race round.

    Args:
        meta_df: one row per race. Required columns: round, event_name, lap_delta_s.
        save_path: if given, save PNG at 150 dpi.
    """
    df = meta_df.sort_values('round').reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df['round'], df['lap_delta_s'], marker='o', color='#1f77b4', linewidth=2, markersize=8)
    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(df['round'])
    ax.set_xticklabels([f"R{r}\n{n}" for r, n in zip(df['round'], df['event_name'])])
    ax.set_ylabel('Lap-time delta (s)\npositive → Antonelli faster')
    ax.set_title('Antonelli vs Russell — total qualifying lap delta by round')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


# ---------------------------------------------------------------------------
# Chapter 2 — race-winning mechanism charts (start / pace / gap / tire)
# ---------------------------------------------------------------------------

def plot_start_conversion(start_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Per race, a 3-point slope line (grid -> end of lap 1 -> finish) for
    ANT, RUS, and the per-race P2 finisher. Y-axis is track position, inverted
    so P1 sits at the top. Highlights Canada (ANT P2->led->win) and Monaco
    (ANT pole->win), with Australia the honest counter-case (P2->P2).

    Required columns: race, driver, code, grid, lap1_pos, finish.
    """
    races = list(dict.fromkeys(start_df["race"]))  # preserve order
    role_color = {"ANT": "#1f77b4", "RUS": "#7f7f7f", "P2": "#d62728"}
    fig, axes = plt.subplots(1, len(races), figsize=(3.2 * len(races), 4.2), sharey=True)
    if len(races) == 1:
        axes = [axes]
    stages = ["grid", "lap1_pos", "finish"]
    stage_labels = ["Grid", "End L1", "Finish"]
    for ax, rc in zip(axes, races):
        sub = start_df[start_df["race"] == rc]
        for _, row in sub.iterrows():
            ys = [row[s] for s in stages]
            label = row["driver"] if row["driver"] != "P2" else f"P2 ({row['code']})"
            ax.plot(range(3), ys, marker="o", color=role_color[row["driver"]], label=label)
        ax.set_title(rc.replace(" Grand Prix", ""), fontsize=10)
        ax.set_xticks(range(3))
        ax.set_xticklabels(stage_labels, fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Track position (P1 = top)")
    axes[-1].legend(fontsize=8, loc="lower right")
    fig.suptitle("Grid → lap 1 → finish: how Antonelli's races unfold", fontsize=12)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_stint_pace(pace_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Median clean-lap time per stint, ANT vs RUS vs field (P2 finisher code),
    grouped by race. Each bar annotated with its tire compound. Lower = faster.
    Compare bars WITHIN a race and only across matching compounds.

    Required columns: race, driver, stint, compound, median_laptime_s.
    'driver' here is the actual code (ANT/RUS/<P2 code>)."""
    races = list(dict.fromkeys(pace_df["race"]))
    fig, axes = plt.subplots(1, len(races), figsize=(3.4 * len(races), 4.2))
    if len(races) == 1:
        axes = [axes]
    drivers = list(dict.fromkeys(pace_df["driver"]))
    colors = plt.cm.tab10.colors
    dcolor = {d: colors[i % 10] for i, d in enumerate(drivers)}
    for ax, rc in zip(axes, races):
        sub = pace_df[pace_df["race"] == rc]
        stints = sorted(sub["stint"].unique())
        width = 0.8 / max(len(drivers), 1)
        for j, d in enumerate(drivers):
            ds = sub[sub["driver"] == d].set_index("stint")
            xs, ys, comps = [], [], []
            for k, st in enumerate(stints):
                if st in ds.index:
                    xs.append(k + j * width)
                    ys.append(ds.loc[st, "median_laptime_s"])
                    comps.append(str(ds.loc[st, "compound"])[:1])
            ax.bar(xs, ys, width=width, color=dcolor[d], label=d)
            for x, y, c in zip(xs, ys, comps):
                ax.text(x, y, c, ha="center", va="bottom", fontsize=7)
        ax.set_title(rc.replace(" Grand Prix", ""), fontsize=10)
        ax.set_xticks([k + width for k in range(len(stints))])
        ax.set_xticklabels([f"Stint {s}" for s in stints], fontsize=8)
        ax.set_ylabel("Median clean lap (s)")
        if len(sub):
            lo, hi = sub["median_laptime_s"].min(), sub["median_laptime_s"].max()
            ax.set_ylim(lo - 0.5, hi + 1.0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[-1].legend(fontsize=8)
    fig.suptitle("Race pace by stint (lower = faster); letter = compound", fontsize=12)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_gap_trace(gap_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Per-lap race-control trace. y = gap_s (negative when ANT leads/ahead of
    P2, positive when chasing the leader). One line per race. The y=0 line is
    the lead/chase boundary.

    Required columns: race, lap, gap_s, leading."""
    races = list(dict.fromkeys(gap_df["race"]))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = plt.cm.tab10.colors
    for i, rc in enumerate(races):
        sub = gap_df[gap_df["race"] == rc]
        ax.plot(sub["lap"], sub["gap_s"], color=colors[i % 10],
                label=rc.replace(" Grand Prix", ""))
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Lap")
    ax.set_ylabel("Gap (s): negative = Antonelli leading / ahead of P2")
    ax.set_title("How Antonelli controls the race: gap trace per round")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_tire_deg(deg_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Tire-degradation slope (s lost per lap of tire age) for comparable
    stints, ANT vs RUS. Lower = better tire management. Stints with NaN slope
    (fewer than MIN_DEG_LAPS clean laps) are omitted from bars and listed as a
    caption note rather than shown as zero.

    Required columns: race, driver, stint, compound, deg_slope_s_per_lap, n_clean."""
    fittable = deg_df.dropna(subset=["deg_slope_s_per_lap"]).copy()
    fittable["label"] = (fittable["race"].str.replace(" Grand Prix", "", regex=False)
                         + "\nS" + fittable["stint"].astype(str)
                         + " " + fittable["compound"].str[:1])
    drivers = list(dict.fromkeys(fittable["driver"]))
    labels = list(dict.fromkeys(fittable["label"]))
    colors = {"ANT": "#1f77b4", "RUS": "#7f7f7f"}
    fig, ax = plt.subplots(figsize=(max(8, 1.1 * len(labels)), 5))
    width = 0.8 / max(len(drivers), 1)
    for j, d in enumerate(drivers):
        ds = fittable[fittable["driver"] == d].set_index("label")
        xs = [k + j * width for k, lab in enumerate(labels) if lab in ds.index]
        ys = [ds.loc[lab, "deg_slope_s_per_lap"] for lab in labels if lab in ds.index]
        ax.bar(xs, ys, width=width, color=colors.get(d, "#999"), label=d)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks([k + width / 2 for k in range(len(labels))])
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Degradation (s lost per lap of tire age)\nlower = better")
    ax.set_title("Tire management by stint: Antonelli vs Russell")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=8)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ---------------------------------------------------------------------------
# Chapter 3 — cross-year track-history charts (overperformance vs baseline)
# ---------------------------------------------------------------------------

def plot_track_affinity(affinity_df: pd.DataFrame, group_col: str = "driver",
                        title: str = "", highlight: Optional[str] = None,
                        top_n: int = 12, save_path: Optional[Path] = None) -> plt.Figure:
    """Horizontal bars of overperformance vs season baseline at one track.
    Positive = finishes/qualifies better here than their season norm (car divided
    out). Small-n rows (small_n==True) are drawn lighter. `highlight` (a value in
    group_col) is accented. Shows the top_n by affinity.

    Required columns: <group_col>, affinity, n_years, small_n."""
    df = affinity_df.head(top_n).iloc[::-1]  # best at top
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(df))))
    for _, row in df.iterrows():
        base = "#1f77b4" if not row["small_n"] else "#b8cfe5"
        color = "#d62728" if (highlight is not None and row[group_col] == highlight) else base
        ax.barh(str(row[group_col]), row["affinity"], color=color)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Overperformance vs season baseline (positions; + = better here)")
    ax.set_title(title or f"Who overperforms at this track ({group_col})")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_driver_vs_car_spread(driver_df: pd.DataFrame, team_df: pd.DataFrame,
                              track: str = "", top_n: int = 8,
                              save_path: Optional[Path] = None) -> plt.Figure:
    """Two panels for one track: top driver overperformance vs top team
    overperformance. Lets the reader judge whether the track is driver-dependent
    (drivers carry the signal) or car-dependent (teams do).
    Required columns: driver/team, affinity, small_n."""
    fig, (ax_d, ax_t) = plt.subplots(1, 2, figsize=(12, max(3, 0.5 * top_n)))
    for ax, df, gcol, label in [(ax_d, driver_df, "driver", "Drivers"),
                                (ax_t, team_df, "team", "Teams")]:
        d = df.head(top_n).iloc[::-1]
        colors = ["#1f77b4" if not s else "#b8cfe5" for s in d["small_n"]]
        ax.barh(d[gcol].astype(str), d["affinity"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(label)
        ax.set_xlabel("Overperformance (+ = better than baseline)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(f"{track}: is it a driver track or a car track?", fontsize=12)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_track_summary(summary_df: pd.DataFrame, save_path: Optional[Path] = None) -> plt.Figure:
    """Compact per-2026-track context. For each track: a bar = Mercedes historical
    team overperformance (car strength here), and a marker = Antonelli's own
    overperformance. Reading: Mercedes-strong tracks vs tracks where ANT himself
    carries the result.

    Required columns: track, merc_affinity, ant_overperf (NaN allowed),
    driver_track (bool: is this a driver-dependent track?)."""
    df = summary_df.copy()
    fig, ax = plt.subplots(figsize=(9, max(3, 0.6 * len(df))))
    ypos = range(len(df))
    bar_colors = ["#9b59b6" if dt else "#7f7f7f" for dt in df["driver_track"]]
    ax.barh(list(ypos), df["merc_affinity"], color=bar_colors, alpha=0.7,
            label="Mercedes hist. overperf (car)")
    ax.scatter(df["ant_overperf"], list(ypos), color="#d62728", zorder=3,
               label="Antonelli overperf (driver)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(df["track"])
    ax.set_xlabel("Overperformance vs season baseline (+ = better)")
    ax.set_title("Each 2026 track: car strength vs Antonelli's own edge\n"
                 "(purple bar = driver-dependent track)")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
