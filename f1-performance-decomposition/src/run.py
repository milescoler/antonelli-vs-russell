"""End-to-end pipeline: data -> resample -> delta -> stats -> attribution -> outputs.

Run it with::

    python -m src.run                 # live FastF1 data (needs network once)
    python -m src.run --synthetic     # offline fixture, for CI / a quick demo

Everything is driven by ``config.py``. The run reconciles the delta curve
against the official lap gap (a hard correctness gate), writes the ranked
micro-sector table and figures to ``outputs/``, and injects the data-derived
findings into ``REPORT.md`` between the AUTOGEN markers.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

import config
from src import data_loading, resampling, delta as delta_mod, stats, attribution, plotting

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run")


def _corner_distances_from_session(session) -> np.ndarray | None:
    try:
        ci = session.get_circuit_info()
        if ci is not None and len(ci.corners):
            return ci.corners["Distance"].to_numpy(dtype=float)
    except Exception as exc:  # noqa: BLE001
        logger.warning("no circuit info (%s); falling back to equal-distance bins", exc)
    return None


def gather_inputs(use_synthetic: bool):
    """Return (laps_a, laps_b, corner_distances, label)."""
    if use_synthetic:
        from src import synthetic
        a, b = synthetic.load_drivers(driver_a=config.DRIVER_A, driver_b=config.DRIVER_B)
        return a, b, synthetic.corner_distances(), "SYNTHETIC FIXTURE"
    session = data_loading.load_session()
    a = data_loading.select_clean_laps(session, config.DRIVER_A)
    b = data_loading.select_clean_laps(session, config.DRIVER_B)
    cd = _corner_distances_from_session(session)
    label = f"{config.YEAR} {config.GRAND_PRIX} {config.SESSION}"
    return a, b, cd, label


def run_pipeline(use_synthetic: bool = False) -> dict:
    laps_a, laps_b, corner_distances, label = gather_inputs(use_synthetic)
    if not laps_a.laps or not laps_b.laps:
        raise RuntimeError("No clean laps for one of the drivers - cannot decompose.")

    fa, fb = laps_a.fastest, laps_b.fastest
    grid = resampling.common_grid(fa, fb)

    # Representative (fastest) laps drive the curve; all clean laps drive stats.
    repr_a = resampling.resample_lap(fa, grid)
    repr_b = resampling.resample_lap(fb, grid)
    all_a = resampling.resample_driver(laps_a.laps, grid)
    all_b = resampling.resample_driver(laps_b.laps, grid)

    # Core curve + segmentation.
    g, dlt = delta_mod.cumulative_delta(repr_a, repr_b)
    edges = delta_mod.micro_sector_edges(g, corner_distances=corner_distances)
    decomp = delta_mod.decompose(g, dlt, edges)

    # Reconciliation gate.
    official_gap = fa.lap_time - fb.lap_time
    ok, residual = delta_mod.reconcile(float(dlt[-1]), official_gap)
    logger.info("reconciliation: curve endpoint=%.3f s, official gap=%.3f s, residual=%.4f s (%s)",
                float(dlt[-1]), official_gap, residual, "OK" if ok else "FAIL")
    if not ok:
        raise AssertionError(
            f"delta curve endpoint {dlt[-1]:.3f}s != official gap {official_gap:.3f}s "
            f"(residual {residual:.4f}s > tol {config.RECONCILE_TOLERANCE_S}s)")

    # Signal vs. noise.
    seg_a = stats.segment_time_matrix(all_a, edges)
    seg_b = stats.segment_time_matrix(all_b, edges)
    boot = stats.bootstrap_sector_deltas(seg_a, seg_b)
    table = stats.assemble_sector_table(decomp, boot)
    top = stats.top_significant_sectors(table)

    # Attribution at the key micro-sectors.
    attrib = attribution.attribute(top, repr_a, repr_b) if len(top) else pd.DataFrame()

    return dict(
        label=label, use_synthetic=use_synthetic,
        grid=g, delta=dlt, edges=edges, corner_distances=corner_distances,
        decomp=decomp, table=table, top=top, attrib=attrib,
        repr_a=repr_a, repr_b=repr_b,
        official_gap=official_gap, endpoint=float(dlt[-1]), residual=residual,
        n_laps_a=len(laps_a.laps), n_laps_b=len(laps_b.laps),
        fastest_a=fa.lap_time, fastest_b=fb.lap_time,
    )


def write_outputs(res: dict) -> None:
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    res["table"].to_csv(config.TABLES_DIR / "micro_sector_deltas.csv", index=False)
    if len(res["attrib"]):
        res["attrib"].to_csv(config.TABLES_DIR / "attribution.csv", index=False)

    plotting.plot_cumulative_delta(res["grid"], res["delta"], res["edges"],
                                   res["corner_distances"])
    plotting.plot_sector_bars(res["table"])
    if len(res["top"]):
        plotting.plot_input_overlays(res["top"], res["repr_a"], res["repr_b"])
    plotting.plot_track_map(res["repr_a"], res["grid"], res["delta"])
    logger.info("wrote tables to %s and figures to %s", config.TABLES_DIR, config.FIGURES_DIR)


def _findings_markdown(res: dict) -> str:
    a, b = config.DRIVER_A, config.DRIVER_B
    lines = [
        f"*Source: {res['label']}"
        + ("  ⚠️ synthetic fixture, not real F1 data.*" if res["use_synthetic"] else ".*"),
        "",
        f"- Clean laps used: **{a}** {res['n_laps_a']}, **{b}** {res['n_laps_b']}.",
        f"- Fastest lap: {a} {res['fastest_a']:.3f}s, {b} {res['fastest_b']:.3f}s "
        f"-> official gap **{res['official_gap']:+.3f}s** ({'+' if res['official_gap']>0 else ''}= {a} slower).",
        f"- Cumulative-delta curve endpoint **{res['endpoint']:+.3f}s**, reconciles to "
        f"within **{abs(res['residual']):.4f}s** (tolerance {config.RECONCILE_TOLERANCE_S}s).",
        "",
        "**Ranked micro-sectors (top by magnitude):**",
        "",
        "| rank | sector | mid (m) | delta mean (s) | 95% CI | real? |",
        "|---:|---:|---:|---:|:--:|:--:|",
    ]
    for _, r in res["table"].head(8).iterrows():
        flag = "yes" if r["significant"] else "noise"
        lines.append(
            f"| {int(r['rank'])} | {int(r['sector'])} | {r['mid_m']:.0f} | "
            f"{r['delta_s_mean']:+.3f} | [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {flag} |")
    lines += ["", "**Attribution at the key (real) micro-sectors:**", ""]
    if len(res["attrib"]):
        for _, r in res["attrib"].iterrows():
            lines.append(f"- {r['narrative']}")
    else:
        lines.append("- No micro-sector advantage was statistically distinguishable from zero "
                     "at this sample size - the lap-time gap is within lap-to-lap noise.")

    # The honesty line the spec asks for: a near-zero "edge" swamped by its CI.
    noise = res["table"][~res["table"]["significant"]]
    if len(noise):
        r = noise.iloc[0]
        lines += ["", f"> **Noise check.** Sector {int(r['sector'])} shows a "
                  f"{r['delta_s_mean']:+.3f}s 'edge', but its 95% CI "
                  f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] straddles zero - this is not a "
                  "real advantage, just a good/bad lap."]
    return "\n".join(lines)


def inject_report(res: dict) -> None:
    """Replace the AUTOGEN block in REPORT.md with freshly computed findings."""
    begin, end = "<!-- BEGIN AUTOGEN:findings -->", "<!-- END AUTOGEN:findings -->"
    if not config.REPORT_PATH.exists():
        return
    text = config.REPORT_PATH.read_text()
    if begin in text and end in text:
        pre = text.split(begin)[0]
        post = text.split(end)[1]
        text = f"{pre}{begin}\n{_findings_markdown(res)}\n{end}{post}"
        config.REPORT_PATH.write_text(text)
        logger.info("injected findings into %s", config.REPORT_PATH)


def main() -> None:
    p = argparse.ArgumentParser(description="F1 lap-time decomposition pipeline")
    p.add_argument("--synthetic", action="store_true",
                   help="use the offline synthetic fixture instead of FastF1")
    p.add_argument("--no-report", action="store_true", help="skip REPORT.md injection")
    args = p.parse_args()

    res = run_pipeline(use_synthetic=args.synthetic)
    write_outputs(res)
    if not args.no_report:
        inject_report(res)
    logger.info("done.")


if __name__ == "__main__":
    main()
