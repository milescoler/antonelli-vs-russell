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
