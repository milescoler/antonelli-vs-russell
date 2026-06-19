"""Signal vs. noise: bootstrap confidence intervals on per-sector deltas.

A single lap cannot tell a real advantage from a tidy lap. With several clean
laps per driver, each micro-sector has a *distribution* of time deltas, and the
question becomes statistical: is the mean delta distinguishable from zero?

We use a non-parametric bootstrap (resample whole laps with replacement) rather
than a t-test because it is assumption-light - it makes no normality claim
about a handful of laps - and because "resample the laps we happened to get and
see how much the answer wobbles" is exactly the uncertainty we care about and is
trivial to explain to a non-statistician. Laps are resampled *per driver and
independently*: the laps are not paired, so pairing them would invent structure
that is not there.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from src import delta as delta_mod


def segment_time_matrix(resampled_laps: list[pd.DataFrame],
                        edges: np.ndarray,
                        basis: str | None = None) -> np.ndarray:
    """(n_laps, n_sectors) matrix of per-sector times for one driver."""
    return np.vstack([delta_mod.segment_times(lap, edges, basis)
                      for lap in resampled_laps])


def bootstrap_sector_deltas(seg_a: np.ndarray,
                            seg_b: np.ndarray,
                            n_boot: int | None = None,
                            confidence: float | None = None,
                            seed: int | None = None) -> pd.DataFrame:
    """Bootstrap the per-micro-sector mean delta (A - B) with CIs.

    Parameters
    ----------
    seg_a, seg_b : (n_laps, n_sectors) per-sector time matrices.

    Returns one row per micro-sector with the point estimate, the percentile
    CI, the bootstrap SE, and a ``significant`` flag (CI excludes zero).
    """
    n_boot = n_boot or config.N_BOOTSTRAP
    confidence = confidence or config.CONFIDENCE
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)

    n_a, n_sec = seg_a.shape
    n_b = seg_b.shape[0]

    point = seg_a.mean(axis=0) - seg_b.mean(axis=0)

    boot = np.empty((n_boot, n_sec))
    for k in range(n_boot):
        ia = rng.integers(0, n_a, size=n_a)     # resample laps, with replacement
        ib = rng.integers(0, n_b, size=n_b)
        boot[k] = seg_a[ia].mean(axis=0) - seg_b[ib].mean(axis=0)

    alpha = 1.0 - confidence
    lo = np.percentile(boot, 100 * alpha / 2, axis=0)
    hi = np.percentile(boot, 100 * (1 - alpha / 2), axis=0)
    se = boot.std(axis=0, ddof=1)
    significant = (lo > 0) | (hi < 0)           # interval excludes zero

    return pd.DataFrame({
        "sector": np.arange(1, n_sec + 1),
        "delta_s": point,
        "ci_low": lo,
        "ci_high": hi,
        "boot_se": se,
        "significant": significant,
        "n_laps_a": n_a,
        "n_laps_b": n_b,
    })


def assemble_sector_table(decomposition: pd.DataFrame,
                          stats: pd.DataFrame) -> pd.DataFrame:
    """Merge the geometric decomposition with the bootstrap stats and rank.

    The point delta in ``stats`` (mean over laps) and the single-lap
    ``decomposition`` delta are reported side by side: where they disagree, the
    representative lap was unrepresentative - itself a useful diagnostic.
    """
    out = decomposition.merge(
        stats.drop(columns=["delta_s"]), on="sector", how="left",
        suffixes=("", "_boot"),
    )
    out = out.rename(columns={"delta_s": "delta_s_repr_lap"})
    out["delta_s_mean"] = stats.set_index("sector").loc[out["sector"], "delta_s"].to_numpy()
    out["abs_delta"] = out["delta_s_mean"].abs()
    out = out.sort_values("abs_delta", ascending=False).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    cols = ["rank", "sector", "start_m", "end_m", "mid_m",
            "delta_s_mean", "delta_s_repr_lap", "ci_low", "ci_high",
            "boot_se", "significant", "n_laps_a", "n_laps_b"]
    return out[cols]


def top_significant_sectors(table: pd.DataFrame, k: int | None = None) -> pd.DataFrame:
    """The k largest-magnitude micro-sectors whose CI excludes zero."""
    k = k or config.N_KEY_SECTORS
    sig = table[table["significant"]].copy()
    return sig.head(k)
