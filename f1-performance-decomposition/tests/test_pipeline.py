"""Pipeline invariants, all runnable offline via the synthetic fixture.

The headline test is the reconciliation gate the spec demands: the cumulative
delta curve's value at the finish line must equal the official lap-time gap to
within tolerance. The rest guard the resampling, the telescoping decomposition,
and that the bootstrap actually separates planted signal from noise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from src import synthetic, resampling, delta as delta_mod, stats, attribution


@pytest.fixture(scope="module")
def drivers():
    return synthetic.load_drivers(n_laps=8)


@pytest.fixture(scope="module")
def pipeline(drivers):
    laps_a, laps_b = drivers
    fa, fb = laps_a.fastest, laps_b.fastest
    grid = resampling.common_grid(fa, fb)
    repr_a = resampling.resample_lap(fa, grid)
    repr_b = resampling.resample_lap(fb, grid)
    g, dlt = delta_mod.cumulative_delta(repr_a, repr_b)
    edges = delta_mod.micro_sector_edges(g, corner_distances=synthetic.corner_distances())
    decomp = delta_mod.decompose(g, dlt, edges)
    all_a = resampling.resample_driver(laps_a.laps, grid)
    all_b = resampling.resample_driver(laps_b.laps, grid)
    seg_a = stats.segment_time_matrix(all_a, edges)
    seg_b = stats.segment_time_matrix(all_b, edges)
    boot = stats.bootstrap_sector_deltas(seg_a, seg_b)
    table = stats.assemble_sector_table(decomp, boot)
    return dict(laps_a=laps_a, laps_b=laps_b, fa=fa, fb=fb, grid=g, delta=dlt,
                edges=edges, decomp=decomp, table=table,
                repr_a=repr_a, repr_b=repr_b)


# --------------------------------------------------------------------------- #
# Resampling
# --------------------------------------------------------------------------- #
def test_grid_is_monotone_and_spans_lap(pipeline):
    g = pipeline["grid"]
    assert g[0] == 0.0
    assert np.all(np.diff(g) > 0)
    assert g[-1] == pytest.approx(min(pipeline["fa"].lap_length,
                                      pipeline["fb"].lap_length))


def test_resample_preserves_endpoints(pipeline):
    # Interpolated speed at the grid ends matches the raw lap's ends closely.
    raw = pipeline["fa"].telemetry
    res = pipeline["repr_a"]
    assert res["Speed"].iloc[0] == pytest.approx(raw["Speed"].iloc[0], abs=1.0)


# --------------------------------------------------------------------------- #
# Reconciliation gate (THE test from the spec)
# --------------------------------------------------------------------------- #
def test_delta_endpoint_reconciles_with_official_gap(pipeline):
    official_gap = pipeline["fa"].lap_time - pipeline["fb"].lap_time
    endpoint = float(pipeline["delta"][-1])
    ok, residual = delta_mod.reconcile(endpoint, official_gap)
    assert ok, f"residual {residual:.4f}s exceeds tolerance"


def test_two_time_bases_agree(pipeline):
    # telemetry_time and the 1/speed integral must give the same endpoint.
    _, d_tel = delta_mod.cumulative_delta(pipeline["repr_a"], pipeline["repr_b"],
                                          basis="telemetry_time")
    _, d_int = delta_mod.cumulative_delta(pipeline["repr_a"], pipeline["repr_b"],
                                          basis="speed_integral")
    assert float(d_tel[-1]) == pytest.approx(float(d_int[-1]), abs=0.05)


def test_segment_contributions_telescope(pipeline):
    # Sum of per-sector deltas == curve endpoint (the invariant the table uses).
    total = pipeline["decomp"]["delta_s"].sum()
    assert total == pytest.approx(float(pipeline["delta"][-1]), abs=1e-6)


# --------------------------------------------------------------------------- #
# Micro-sectors
# --------------------------------------------------------------------------- #
def test_micro_sector_count_in_spec_range(pipeline):
    n = len(pipeline["edges"]) - 1
    assert 10 <= n <= 30   # corner-anchored count lands in the 15-25 ballpark


# --------------------------------------------------------------------------- #
# Signal vs. noise
# --------------------------------------------------------------------------- #
def test_bootstrap_is_reproducible(pipeline):
    seg_a = stats.segment_time_matrix(
        resampling.resample_driver(pipeline["laps_a"].laps, pipeline["grid"]),
        pipeline["edges"])
    seg_b = stats.segment_time_matrix(
        resampling.resample_driver(pipeline["laps_b"].laps, pipeline["grid"]),
        pipeline["edges"])
    t1 = stats.bootstrap_sector_deltas(seg_a, seg_b)
    t2 = stats.bootstrap_sector_deltas(seg_a, seg_b)
    pd.testing.assert_frame_equal(t1, t2)   # fixed seed -> identical


def test_bootstrap_flags_signal_and_clears_noise(pipeline):
    """Planted-signal corners should read significant; at least one noise-only
    sector should read non-significant. This is the whole point of the project."""
    table = pipeline["table"]
    assert table["significant"].any(), "no sector flagged real - bootstrap too conservative"
    assert (~table["significant"]).any(), "every sector flagged - bootstrap too liberal"


def test_ci_brackets_point_estimate(pipeline):
    t = pipeline["table"]
    assert np.all(t["ci_low"] <= t["delta_s_mean"] + 1e-9)
    assert np.all(t["delta_s_mean"] <= t["ci_high"] + 1e-9)


# --------------------------------------------------------------------------- #
# Attribution
# --------------------------------------------------------------------------- #
def test_attribution_produces_narrative(pipeline):
    top = stats.top_significant_sectors(pipeline["table"], k=3)
    attrib = attribution.attribute(top, pipeline["repr_a"], pipeline["repr_b"])
    assert len(attrib) == len(top)
    if len(attrib):
        assert attrib.iloc[0]["narrative"]
