"""Car-adjusted driver ratings.

Layer 1 (identified): margin over teammate per duel, with a small-sample Student-t
  interval + exact binomial sign test. Most duels honestly read "inconclusive".
Layer 2 (weakly identified): driver + team-season fixed-effects model on normalized
  qualifying gaps, gauge-fixed per connected component; equal-car what-if.
Layer 3: connectivity graph (union-find) of team-seasons linked by shared drivers —
  the object that makes "what's identified vs assumed" explicit.

Pure functions take plain data (dicts/lists); FastF1 loading lives in the pipeline.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def _r(x, ndigits: int = 3):
    if x is None:
        return None
    fx = float(x)
    if math.isnan(fx) or math.isinf(fx):
        return None
    return round(fx, ndigits)


# ---- shared primitive: normalized gap ------------------------------------

def normalize_session(times: dict[str, float]) -> dict[str, float]:
    """Per-session % off the fastest lap (track-normalized pace; lower = faster)."""
    fastest = min(times.values())
    return {code: 100.0 * (t - fastest) / fastest for code, t in times.items()}


# ---- Layer 1: teammate margin (fully identified) -------------------------

def teammate_margin(deltas, alpha: float = 0.05) -> dict:
    """Per-driver margin over a given teammate from per-round signed gaps
    (positive = this driver faster). Returns mean ± Student-t CI, sign test,
    win rate, median, and an honest three-state verdict."""
    xs = [float(d) for d in deltas]
    n = len(xs)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "se": None, "ciLow": None,
                "ciHigh": None, "winRate": None, "signTestP": None, "verdict": "inconclusive"}
    arr = np.array(xs, dtype=float)
    mean = float(arr.mean())
    median = float(np.median(arr))
    win_rate = round(sum(1 for x in xs if x > 0) / n, 3)
    nz = [x for x in xs if x != 0.0]
    k = sum(1 for x in nz if x > 0)
    sign_p = float(stats.binomtest(k, len(nz), 0.5).pvalue) if nz else 1.0

    if n >= 2:
        se = float(arr.std(ddof=1) / math.sqrt(n))
        tcrit = float(stats.t.ppf(1 - alpha / 2, n - 1))
        ci_low, ci_high = mean - tcrit * se, mean + tcrit * se
    else:
        se = ci_low = ci_high = None

    verdict = "inconclusive"
    if ci_low is not None and ci_low > 0 and sign_p < 0.10:
        verdict = "reliably_faster"
    elif ci_high is not None and ci_high < 0 and sign_p < 0.10:
        verdict = "reliably_slower"

    return {
        "n": n, "mean": _r(mean), "median": _r(median), "se": _r(se),
        "ciLow": _r(ci_low), "ciHigh": _r(ci_high),
        "winRate": win_rate, "signTestP": round(sign_p, 3), "verdict": verdict,
    }


# ---- Layer 3: connectivity / islands -------------------------------------

def connectivity(driver_nodes: dict[str, set]) -> dict:
    """Union-find over team-season nodes; two nodes are linked iff a single driver
    appears in both. Components are the identification 'islands'. `driver_nodes`
    maps driver -> set of (year, team) nodes."""
    nodes = set()
    for ns in driver_nodes.values():
        nodes.update(ns)
    nodes = sorted(nodes)  # deterministic ordering (sets are hash-randomized)
    parent = {nd: nd for nd in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for drv in sorted(driver_nodes):
        ns = sorted(driver_nodes[drv])
        for i in range(1, len(ns)):
            union(ns[0], ns[i])

    groups: dict = {}
    for nd in nodes:
        groups.setdefault(find(nd), []).append(nd)
    components = sorted(groups.values(), key=lambda m: min(m))  # stable component IDs
    node_comp = {nd: idx for idx, members in enumerate(components) for nd in members}
    driver_comp = {drv: node_comp[next(iter(ns))] for drv, ns in driver_nodes.items() if ns}
    return {"components": components, "nodeComponent": node_comp, "driverComponent": driver_comp}


def estimable(a: str, b: str, conn: dict) -> bool:
    """True iff drivers a and b are in the same connectivity component (so a
    cross-driver comparison is data-backed, not assumption-dependent)."""
    dc = conn["driverComponent"]
    return a in dc and b in dc and dc[a] == dc[b]


# ---- Layer 2: absolute model (weakly identified) -------------------------

def absolute_model(rows: list[dict]) -> dict:
    """OLS driver + team-season fixed effects on normalized gaps.
    rows: [{driver, teamSeason, gap_pct}]. Driver effects are identified only up
    to a per-component constant, so they're gauge-fixed to mean 0 within each
    connected component (theta is 'relative to this island's average driver').
    Returns theta/phi, an `estimable(pair)` closure, and the connectivity."""
    drivers = sorted({r["driver"] for r in rows})
    teamseasons = sorted({r["teamSeason"] for r in rows}, key=lambda x: (x[0], str(x[1])))
    di = {d: i for i, d in enumerate(drivers)}
    ti = {t: i for i, t in enumerate(teamseasons)}
    nD, nT = len(drivers), len(teamseasons)

    X = np.zeros((len(rows), nD + nT))
    y = np.zeros(len(rows))
    for k, r in enumerate(rows):
        X[k, di[r["driver"]]] = 1.0
        X[k, nD + ti[r["teamSeason"]]] = 1.0
        y[k] = r["gap_pct"]

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    theta = {d: float(beta[di[d]]) for d in drivers}
    phi = {t: float(beta[nD + ti[t]]) for t in teamseasons}

    driver_nodes: dict[str, set] = {}
    for r in rows:
        driver_nodes.setdefault(r["driver"], set()).add(r["teamSeason"])
    conn = connectivity(driver_nodes)

    # Gauge-fix: center driver effects to 0 within each component.
    by_comp: dict = {}
    for d in drivers:
        by_comp.setdefault(conn["driverComponent"][d], []).append(d)
    for ds in by_comp.values():
        m = float(np.mean([theta[d] for d in ds]))
        for d in ds:
            theta[d] -= m

    def _estimable(pair):
        return estimable(pair[0], pair[1], conn)

    return {
        "theta": theta,
        "phi": phi,
        "estimable": _estimable,
        "connectivity": conn,
        "componentOf": conn["driverComponent"],
    }


def session_bootstrap(rows: list[dict], b: int = 1000, seed: int = 0) -> dict:
    """Cluster bootstrap resampling whole sessions (rows must carry `session`).
    Returns per-driver theta percentile CIs (within-component relative) — the
    honest Layer-2 uncertainty. Seeded for deterministic output."""
    sessions = sorted({r["session"] for r in rows})
    by_session: dict = {}
    for r in rows:
        by_session.setdefault(r["session"], []).append(r)
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {}
    for _ in range(b):
        pick = rng.choice(len(sessions), size=len(sessions), replace=True)
        boot_rows = [row for idx in pick for row in by_session[sessions[idx]]]
        try:
            theta = absolute_model(boot_rows)["theta"]
        except Exception:  # noqa: BLE001 - a degenerate resample is just skipped
            continue
        for d, v in theta.items():
            samples.setdefault(d, []).append(v)
    out = {}
    for d, vals in samples.items():
        arr = np.array(vals)
        out[d] = {"ciLow": _r(np.percentile(arr, 5)), "ciHigh": _r(np.percentile(arr, 95))}
    return out


def equal_car_grid(theta: dict[str, float], component_of: dict[str, int]) -> list[dict]:
    """Equal-car what-if: with every car set equal, predicted pace = driver effect.
    Ranked globally (lower theta = faster). Cross-component ordering is an
    extrapolation — callers must flag it. Within-component rank is data-backed."""
    ordered = sorted(theta, key=lambda d: theta[d])
    # within-component rank (data-backed)
    comp_members: dict = {}
    for d in ordered:
        comp_members.setdefault(component_of.get(d), []).append(d)
    comp_rank = {}
    for ds in comp_members.values():
        for i, d in enumerate(sorted(ds, key=lambda x: theta[x])):
            comp_rank[d] = i + 1
    return [
        {
            "driver": d,
            "theta": _r(theta[d]),
            "globalRank": i + 1,
            "component": component_of.get(d),
            "componentRank": comp_rank[d],
        }
        for i, d in enumerate(ordered)
    ]
