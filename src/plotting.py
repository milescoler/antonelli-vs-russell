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
    ax.set_title('Where does Antonelli gain or lose time vs Russell?\n2026 Qualifying, first 4 rounds')
    ax.grid(axis='y', linestyle='--', alpha=0.35, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
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
        'Antonelli vs Russell — same 4 tracks, rookie year vs sophomore year'
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
