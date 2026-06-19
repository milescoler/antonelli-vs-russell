# Race-Win Decomposition — Data Pipeline (Factors 2–4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce per-race JSON that decomposes a race winning-margin (winner vs P2) into the tyre, pace, and start factors — each with a signal-vs-noise verdict — reusing the already-written race serializers. (Factor 1 "where on track" is added by the next plan; here it is emitted as `insufficient` placeholder.)

**Architecture:** A pure verdict layer (`src/race_verdict.py`) + a per-race assembler and winner/P2 resolver (`src/race_win.py`) reuse `src/race.py` (factor math) and `src/serialize.py` (factor serializers). A build script (`scripts/build_race_decomp_data.py`) discovers rounds via `src/teams.py`, builds each race, and writes `web/public/data/race/{index.json,<slug>.json}` with honest exclusion.

**Tech Stack:** Python 3.12, FastF1 3.8.x, numpy, pandas, pytest. No new deps.

## Global Constraints
- Sign convention: per-driver deltas as `winner − P2`; **negative = winner faster/better** for time, **positive = winner gained** for positions. State the convention in each payload.
- Verdicts are one of `'real' | 'noise' | 'inherited' | 'insufficient'`. `real` requires a quantified edge that clears its noise check; `insufficient` when data is too thin; `inherited` when a rival DNF flipped the outcome.
- Reuse, do not reimplement: `src/race.py` (`load_race_session`, `get_clean_laps`, `start_summary`, `stint_pace`, `tire_deg`, `gap_to_rival`), `src/serialize.py` (`serialize_start`, `serialize_stint_pace`, `serialize_tire_deg`, `serialize_gap_trace`, `_num`, `_int_or_none`), `src/teams.py::list_completed_rounds`.
- Deterministic JSON: sorted keys, fixed rounding, NaN/inf/None → JSON null (`serialize._num`/`_int_or_none`).
- Pure logic (verdicts, resolvers, assembly from DataFrames) lives in `_`-helpers tested with hand-built DataFrames, FastF1-free (mirror `tests/test_serialize.py`). FastF1-touching wrappers are thin.
- Tunable thresholds live as module constants with comments; they are starting values to calibrate on real data, not magic numbers buried in logic.
- Factor 1 is OUT of scope here: emit `{"verdict": "insufficient", "headline": "computed in the where-on-track pass", "magnitudeS": null}` as a placeholder so the schema is stable for the next plan.

Paths are relative to repo root `/Users/mcoler/Documents/project-folder/f1_project`. Tests run from repo root: `python -m pytest tests/ -v`.

---

### Task 1: Winner / P2 / margin resolution

**Files:**
- Create: `src/race_win.py`
- Test: `tests/test_race_win.py`

**Interfaces:**
- Produces: `principals_from_results(results: pd.DataFrame) -> dict` →
  `{"winner": {"code","name","team","color"}, "p2": {...}, "marginS": float|None, "anyDnf": bool, "winnerStatus": str, "p2Status": str}`.
  Input is a `session.results`-shaped frame with columns `Position, Abbreviation, FullName, TeamName, TeamColor, Time, Status`. `marginS` = the P2 row's `Time` (FastF1 stores non-winner `Time` as the gap to the winner, a Timedelta) in seconds; `None` if NaT (lapped/DNF).

- [ ] **Step 1: Write the failing test**

Create `tests/test_race_win.py`:

```python
import pandas as pd
from src import race_win


def _results(rows):
    cols = ["Position", "Abbreviation", "FullName", "TeamName", "TeamColor", "Time", "Status"]
    return pd.DataFrame(rows, columns=cols)


def test_principals_resolves_winner_p2_and_margin():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished"),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.Timedelta(seconds=8.4), "Finished"),
        (3.0, "LEC", "Charles Leclerc", "Ferrari", "E80020", pd.Timedelta(seconds=12.1), "Finished"),
    ])
    p = race_win.principals_from_results(res)
    assert p["winner"]["code"] == "ANT" and p["p2"]["code"] == "NOR"
    assert p["winner"]["color"] == "#27F4D2"
    assert abs(p["marginS"] - 8.4) < 1e-6
    assert p["anyDnf"] is False


def test_principals_margin_none_when_p2_lapped_and_flags_dnf():
    res = _results([
        (1.0, "ANT", "Kimi Antonelli", "Mercedes", "27F4D2", pd.Timedelta(0), "Finished"),
        (2.0, "NOR", "Lando Norris", "McLaren", "FF8000", pd.NaT, "+1 Lap"),
        (3.0, "RUS", "George Russell", "Mercedes", "27F4D2", pd.NaT, "Retired"),
    ])
    p = race_win.principals_from_results(res)
    assert p["marginS"] is None
    assert p["anyDnf"] is True   # a classified runner did not Finish
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race_win.py::test_principals_resolves_winner_p2_and_margin -v`
Expected: FAIL — `ModuleNotFoundError: src.race_win`.

- [ ] **Step 3: Implement**

Create `src/race_win.py`:

```python
"""Resolve a race's principals (winner, P2) and assemble the per-race
decomposition payload, reusing src/race.py (factor math), src/serialize.py
(serializers), and src/race_verdict.py (verdicts). FastF1-touching wrappers are
thin; the pure logic operates on DataFrames so it is unit-tested offline.
"""
from __future__ import annotations

import pandas as pd

from src import race as race_mod
from src import serialize, race_verdict


def _hex(color) -> str | None:
    if isinstance(color, str) and color:
        return color if color.startswith("#") else f"#{color}"
    return None


def _driver(row) -> dict:
    return {
        "code": str(row["Abbreviation"]),
        "name": str(row["FullName"]),
        "team": str(row["TeamName"]),
        "color": _hex(row.get("TeamColor")),
    }


def principals_from_results(results: pd.DataFrame) -> dict:
    res = results.sort_values("Position")
    win_row = res[res["Position"] == 1.0]
    p2_row = res[res["Position"] == 2.0]
    if win_row.empty or p2_row.empty:
        raise ValueError("race has no classified P1/P2")
    win_row, p2_row = win_row.iloc[0], p2_row.iloc[0]

    t = p2_row.get("Time")
    margin_s = None if pd.isna(t) else float(pd.to_timedelta(t).total_seconds())

    classified = res[res["Position"].notna()]
    any_dnf = bool((classified["Status"].astype(str) != "Finished").any())

    return {
        "winner": _driver(win_row),
        "p2": _driver(p2_row),
        "marginS": margin_s,
        "anyDnf": any_dnf,
        "winnerStatus": str(win_row["Status"]),
        "p2Status": str(p2_row["Status"]),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_race_win.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race_win.py tests/test_race_win.py
git commit -m "feat(race): resolve winner/P2/margin from race results"
```

---

### Task 2: Verdict layer — start, pace, tyre

**Files:**
- Create: `src/race_verdict.py`
- Test: `tests/test_race_verdict.py`

**Interfaces:**
- Consumes: serializer outputs — `serialize_start` rows (`[{role,code,grid,lap1Pos,positionsGained,finish,status,dnf}]`), `serialize_stint_pace` rows (`[{code,stint,compound,medianLaptime_s,nClean}]`), `serialize_tire_deg` rows (`[{code,stint,compound,degSlope_s_per_lap,nClean}]`).
- Produces (each `-> dict` = `{"magnitudeS": float|None, "magnitudeUnit": str, "verdict": str, "headline": str, "caveat": str|None}`):
  - `start_verdict(start_rows, winner_code, p2_code) -> dict`
  - `pace_verdict(stint_pace_rows, winner_code, p2_code) -> dict`
  - `tyre_verdict(deg_rows, winner_code, p2_code) -> dict`

- [ ] **Step 1: Write the failing test**

Create `tests/test_race_verdict.py`:

```python
from src import race_verdict as rv


def test_start_verdict_real_when_winner_gains_and_holds():
    rows = [
        {"role": "A", "code": "ANT", "grid": 3, "lap1Pos": 1, "positionsGained": 2,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 1, "lap1Pos": 2, "positionsGained": -1,
         "finish": 2, "status": "Finished", "dnf": False},
    ]
    v = rv.start_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "real" and v["magnitudeS"] == 2  # places gained (unit=places)
    assert v["magnitudeUnit"] == "places"


def test_start_verdict_inherited_when_rival_dnf():
    rows = [
        {"role": "A", "code": "ANT", "grid": 2, "lap1Pos": 2, "positionsGained": 0,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 5, "lap1Pos": 5, "positionsGained": 0,
         "finish": 2, "status": "Finished", "dnf": False},
        {"role": "WINNER_RIVAL_DNF", "code": "RUS", "grid": 1, "lap1Pos": 1,
         "positionsGained": 0, "finish": None, "status": "Retired", "dnf": True},
    ]
    v = rv.start_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "inherited"


def test_start_verdict_noise_when_small_swing():
    rows = [
        {"role": "A", "code": "ANT", "grid": 1, "lap1Pos": 1, "positionsGained": 0,
         "finish": 1, "status": "Finished", "dnf": False},
        {"role": "P2", "code": "NOR", "grid": 2, "lap1Pos": 2, "positionsGained": 0,
         "finish": 2, "status": "Finished", "dnf": False},
    ]
    assert rv.start_verdict(rows, "ANT", "NOR")["verdict"] == "noise"


def test_pace_verdict_real_on_like_compound_advantage():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "MEDIUM", "medianLaptime_s": 80.0, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "MEDIUM", "medianLaptime_s": 80.4, "nClean": 17},
    ]
    v = rv.pace_verdict(rows, "ANT", "NOR")
    assert v["verdict"] == "real" and v["magnitudeS"] < 0  # winner faster per lap


def test_pace_verdict_insufficient_without_shared_compound():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "SOFT", "medianLaptime_s": 80.0, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "HARD", "medianLaptime_s": 80.4, "nClean": 17},
    ]
    assert rv.pace_verdict(rows, "ANT", "NOR")["verdict"] == "insufficient"


def test_tyre_verdict_insufficient_on_small_sample():
    rows = [
        {"code": "ANT", "stint": 1, "compound": "MEDIUM", "degSlope_s_per_lap": 0.03, "nClean": 18},
        {"code": "NOR", "stint": 1, "compound": "MEDIUM", "degSlope_s_per_lap": None, "nClean": 3},
    ]
    assert rv.tyre_verdict(rows, "ANT", "NOR")["verdict"] == "insufficient"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: src.race_verdict`.

- [ ] **Step 3: Implement**

Create `src/race_verdict.py`:

```python
"""Per-factor signal-vs-noise verdicts for the race-win decomposition.

Pure functions over serializer outputs. Each returns
{magnitudeS, magnitudeUnit, verdict, headline, caveat}. Thresholds are starting
values calibrated on real data; the pace/tyre bootstrap-CI upgrade lands with the
where-on-track pass.
"""
from __future__ import annotations

# Tunable starting thresholds (calibrate on real 2026 data).
START_REAL_PLACES = 2          # net lap-1 places gained to call the start decisive
PACE_REAL_S_PER_LAP = 0.15     # like-compound per-lap median advantage to call pace real
TYRE_REAL_S_PER_LAP = 0.03     # like-compound deg-slope advantage to call tyre real


def _row(rows, code):
    for r in rows:
        if r["code"] == code:
            return r
    return None


def start_verdict(start_rows: list[dict], winner_code: str, p2_code: str) -> dict:
    w = _row(start_rows, winner_code)
    gained = (w or {}).get("positionsGained")
    # Inherited: any classified-ahead rival DNF'd (a non-winner/non-P2 row that retired).
    rival_dnf = any(r["dnf"] for r in start_rows
                    if r["code"] not in (winner_code, p2_code))
    if rival_dnf:
        verdict, caveat = "inherited", "a rival ahead retired; track position was inherited"
    elif gained is None:
        verdict, caveat = "insufficient", "no lap-1 data"
    elif gained >= START_REAL_PLACES:
        verdict, caveat = "real", "conflates start skill with grid position and lap-1 luck"
    else:
        verdict, caveat = "noise", "lap-1 swing within normal first-lap scatter"
    return {
        "magnitudeS": (None if gained is None else float(gained)),
        "magnitudeUnit": "places",
        "verdict": verdict,
        "headline": f"{winner_code} {'+' if (gained or 0) >= 0 else ''}{gained} places on lap 1"
                    if gained is not None else "no lap-1 data",
        "caveat": caveat,
    }


def _like_compound_pairs(rows, winner_code, p2_code, value_key):
    """Per shared (compound) the (winner_value, p2_value) on the winner's and P2's
    stints of that compound (mean across stints of the compound)."""
    out = {}
    for code in (winner_code, p2_code):
        for r in rows:
            if r["code"] != code or r.get(value_key) is None:
                continue
            out.setdefault(r["compound"], {}).setdefault(code, []).append(r[value_key])
    pairs = []
    for comp, d in out.items():
        if winner_code in d and p2_code in d:
            wv = sum(d[winner_code]) / len(d[winner_code])
            pv = sum(d[p2_code]) / len(d[p2_code])
            pairs.append((comp, wv, pv))
    return pairs


def pace_verdict(stint_pace_rows: list[dict], winner_code: str, p2_code: str) -> dict:
    pairs = _like_compound_pairs(stint_pace_rows, winner_code, p2_code, "medianLaptime_s")
    if not pairs:
        return {"magnitudeS": None, "magnitudeUnit": "s_per_lap", "verdict": "insufficient",
                "headline": "no shared compound to compare race pace",
                "caveat": "winner and P2 never ran the same compound"}
    # winner − P2 per-lap delta, averaged over shared compounds (negative = winner faster)
    delta = sum(wv - pv for _, wv, pv in pairs) / len(pairs)
    verdict = "real" if delta <= -PACE_REAL_S_PER_LAP else "noise"
    return {"magnitudeS": round(delta, 3), "magnitudeUnit": "s_per_lap", "verdict": verdict,
            "headline": f"{winner_code} {abs(delta):.2f}s/lap "
                        f"{'faster' if delta < 0 else 'slower'} on like compounds",
            "caveat": "not fuel-corrected; tyre-management can mask true pace"}


def tyre_verdict(deg_rows: list[dict], winner_code: str, p2_code: str) -> dict:
    pairs = _like_compound_pairs(deg_rows, winner_code, p2_code, "degSlope_s_per_lap")
    if not pairs:
        return {"magnitudeS": None, "magnitudeUnit": "s_per_lap_of_age", "verdict": "insufficient",
                "headline": "no comparable stint long enough to fit degradation",
                "caveat": "deg slope needs >=5 clean laps on a shared compound"}
    delta = sum(wv - pv for _, wv, pv in pairs) / len(pairs)  # negative = winner degrades less
    verdict = "real" if delta <= -TYRE_REAL_S_PER_LAP else "noise"
    return {"magnitudeS": round(delta, 4), "magnitudeUnit": "s_per_lap_of_age", "verdict": verdict,
            "headline": f"{winner_code} tyres degrade {abs(delta):.3f}s/lap "
                        f"{'less' if delta < 0 else 'more'} on like compounds",
            "caveat": "fuel burn partially offsets degradation; small stint counts"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_race_verdict.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/race_verdict.py tests/test_race_verdict.py
git commit -m "feat(race): start/pace/tyre signal-vs-noise verdicts"
```

---

### Task 3: Per-race assembler (factors 2–4 + placeholders)

**Files:**
- Modify: `src/race_win.py` (add `assemble_race`)
- Test: `tests/test_race_win.py` (add)

**Interfaces:**
- Consumes: Task 1 `principals_from_results`; Task 2 verdicts; the `serialize_*` functions; raw factor DataFrames (start/stint/deg/gap) — passed in so the assembler is pure and FastF1-free.
- Produces: `assemble_race(*, principals, start_df, stint_df, deg_df, gap_df, round_number, slug, event_name, year) -> dict` returning the `RaceDecomp` payload: `meta` (winner/p2/marginS/anyDnf), `factors.{where(placeholder),tyre,pace,start}` (each = serializer block + the verdict dict), `caveats`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_race_win.py`:

```python
def test_assemble_race_has_four_factors_and_placeholder_where():
    principals = {"winner": {"code": "ANT", "name": "Kimi Antonelli", "team": "Mercedes", "color": "#27F4D2"},
                  "p2": {"code": "NOR", "name": "Lando Norris", "team": "McLaren", "color": "#FF8000"},
                  "marginS": 8.4, "anyDnf": False, "winnerStatus": "Finished", "p2Status": "Finished"}
    start_df = pd.DataFrame([
        ("R", "ANT", "ANT", 3, 1, 2, 1.0, "Finished"),
        ("R", "RUS", "NOR", 1, 2, -1, 2.0, "Finished"),
        ("R", "P2", "NOR", 1, 2, -1, 2.0, "Finished"),
    ], columns=["race", "driver", "code", "grid", "lap1_pos", "positions_gained", "finish", "status"])
    stint_df = pd.DataFrame([
        ("R", "ANT", 1, "MEDIUM", 80.0, 18), ("R", "NOR", 1, "MEDIUM", 80.4, 17),
    ], columns=["race", "driver", "stint", "compound", "median_laptime_s", "n_clean"])
    deg_df = pd.DataFrame([
        ("R", "ANT", 1, "MEDIUM", 0.030, 18), ("R", "NOR", 1, "MEDIUM", 0.045, 17),
    ], columns=["race", "driver", "stint", "compound", "deg_slope_s_per_lap", "n_clean"])
    gap_df = pd.DataFrame([("R", 1, -1.2, True), ("R", 2, -2.0, True)],
                          columns=["race", "lap", "gap_s", "leading"])

    out = race_win.assemble_race(principals=principals, start_df=start_df, stint_df=stint_df,
                                 deg_df=deg_df, gap_df=gap_df, round_number=5, slug="canadian",
                                 event_name="Canadian Grand Prix", year=2026)
    assert set(out["factors"]) == {"where", "tyre", "pace", "start"}
    assert out["factors"]["where"]["verdict"] == "insufficient"   # placeholder
    assert out["factors"]["pace"]["verdict"] == "real"
    assert out["meta"]["marginS"] == 8.4
    assert "stintPace" in out["factors"]["tyre"] or "stints" in out["factors"]["tyre"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race_win.py::test_assemble_race_has_four_factors_and_placeholder_where -v`
Expected: FAIL — `assemble_race` not defined.

- [ ] **Step 3: Implement** — add to `src/race_win.py`:

```python
def assemble_race(*, principals, start_df, stint_df, deg_df, gap_df,
                  round_number, slug, event_name, year) -> dict:
    w, p2 = principals["winner"]["code"], principals["p2"]["code"]

    start_rows = serialize.serialize_start(start_df, a_code=w, b_code=p2)
    pace_rows = serialize.serialize_stint_pace(stint_df)
    deg_rows = serialize.serialize_tire_deg(deg_df)
    gap = serialize.serialize_gap_trace(gap_df, w) if gap_df is not None and len(gap_df) else \
        {"driverCode": w, "laps": [], "gap_s": [], "leading": []}

    pace_v = race_verdict.pace_verdict(pace_rows, w, p2)
    tyre_v = race_verdict.tyre_verdict(deg_rows, w, p2)
    start_v = race_verdict.start_verdict(start_rows, w, p2)

    factors = {
        "where": {"verdict": "insufficient", "magnitudeS": None,
                  "headline": "computed in the where-on-track pass", "decomp": None},
        "tyre": {**tyre_v, "stints": [r for r in deg_rows if r["code"] in (w, p2)]},
        "pace": {**pace_v, "gapTrace": gap,
                 "stints": [r for r in pace_rows if r["code"] in (w, p2)]},
        "start": {**start_v, "rows": start_rows},
    }
    return {
        "meta": {"race": slug, "eventName": event_name, "round": int(round_number),
                 "year": int(year), "winner": principals["winner"], "p2": principals["p2"],
                 "marginS": principals["marginS"], "anyDnf": principals["anyDnf"]},
        "signConvention": "winner_minus_p2",
        "factors": factors,
        "caveats": {"anyDnf": principals["anyDnf"], "fuelNotCorrected": True,
                    "noCleanLapsDriver": [c for c in (w, p2)
                                          if c not in {r["code"] for r in pace_rows}]},
    }
```

- [ ] **Step 4: Run tests** — Run: `python -m pytest tests/test_race_win.py -v` → PASS.
- [ ] **Step 5: Commit**
```bash
git add src/race_win.py tests/test_race_win.py
git commit -m "feat(race): assemble per-race decomposition payload (factors 2-4 + where placeholder)"
```

---

### Task 4: Build script

**Files:**
- Create: `scripts/build_race_decomp_data.py`
- Test: `tests/test_race_win.py` (add an offline assembly-integration test via injected DataFrames; no FastF1)

**Interfaces:**
- Consumes: `race_win.assemble_race`/`principals_from_results`; `src/race.py` loaders/metrics; `src/teams.py::list_completed_rounds`.
- Produces (importable for testing): `build_one_race(year, round_info) -> dict|None` (loads session, computes factor DataFrames, calls `assemble_race`; returns payload or raises), `index_entry(payload|exclusion)`, `main()`.

- [ ] **Step 1: Write the failing test** — add to `tests/test_race_win.py`:

```python
def test_index_entry_marks_valid_and_excluded():
    from importlib.util import spec_from_file_location, module_from_spec
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    spec = spec_from_file_location("build_race", root / "scripts" / "build_race_decomp_data.py")
    mod = module_from_spec(spec); spec.loader.exec_module(mod)
    valid = mod.index_entry(slug="canadian", round_number=5, payload={
        "meta": {"winner": {"code": "ANT"}, "p2": {"code": "NOR"}, "marginS": 8.4},
        "factors": {"where": {"verdict": "insufficient"}, "tyre": {"verdict": "noise"},
                    "pace": {"verdict": "real"}, "start": {"verdict": "real"}}})
    assert valid["valid"] is True and valid["realFactorCount"] == 2 and valid["slug"] == "canadian"
    excl = mod.index_entry(slug="japanese", round_number=3, reason="no classified P2")
    assert excl["valid"] is False and excl["reason"] == "no classified P2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_race_win.py -k index_entry -v`
Expected: FAIL — script file does not exist.

- [ ] **Step 3: Implement**

Create `scripts/build_race_decomp_data.py`:

```python
#!/usr/bin/env python3
"""Pre-compute race-win decomposition JSON for the web flagship.

Per completed round: resolve winner vs P2, compute the start/pace/tyre factors
(factor 1 "where on track" is added by a later pass), assign a signal-vs-noise
verdict to each, and write web/public/data/race/<slug>.json + an index with
honest exclusion of races we can't decompose.

    python scripts/build_race_decomp_data.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import race as race_mod, race_win, teams      # noqa: E402
from src.loaders import setup_cache                     # noqa: E402

DATA_DIR = ROOT / "web" / "public" / "data" / "race"
CACHE = ROOT / "fastf1_cache"
HERO_SLUG = "monaco"   # a clean pole-to-flag win; NOT canadian (inherited)


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_json_if_changed(path: Path, obj) -> bool:
    text = _canonical(obj)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build_one_race(year: int, round_info: dict) -> dict:
    rnd, slug, name = round_info["round"], round_info["slug"], round_info["eventName"]
    session = race_mod.load_race_session(year, rnd)
    principals = race_win.principals_from_results(session.results)
    w, p2 = principals["winner"]["code"], principals["p2"]["code"]
    start_df = race_mod.start_summary(year, rnd, drv_a=w, drv_b=p2)
    stint_df = race_mod.stint_pace(year, rnd, [w, p2])
    deg_df = race_mod.tire_deg(year, rnd, [w, p2])
    gap_df = race_mod.gap_to_rival(year, rnd, w)
    return race_win.assemble_race(principals=principals, start_df=start_df, stint_df=stint_df,
                                  deg_df=deg_df, gap_df=gap_df, round_number=rnd, slug=slug,
                                  event_name=name, year=year)


def index_entry(*, slug, round_number, payload=None, reason=None) -> dict:
    if payload is not None:
        f = payload["factors"]
        return {"slug": slug, "round": int(round_number), "valid": True,
                "winner": payload["meta"]["winner"]["code"], "p2": payload["meta"]["p2"]["code"],
                "marginS": payload["meta"]["marginS"],
                "realFactorCount": sum(1 for k in f if f[k].get("verdict") == "real")}
    return {"slug": slug, "round": int(round_number), "valid": False, "reason": reason}


def main() -> None:
    argparse.ArgumentParser().parse_args()
    setup_cache(str(CACHE))
    season = 2026
    rounds = teams.list_completed_rounds(season)
    races = [{"slug": r["slug"], "name": r["eventName"], "round": r["round"]} for r in rounds]
    entries = []
    for ri in rounds:
        try:
            payload = build_one_race(season, ri)
        except Exception as exc:  # noqa: BLE001
            entries.append(index_entry(slug=ri["slug"], round_number=ri["round"], reason=str(exc)))
            print(f"  {ri['slug']}: EXCLUDED - {exc}")
            continue
        write_json_if_changed(DATA_DIR / f"{ri['slug']}.json", payload)
        entries.append(index_entry(slug=ri["slug"], round_number=ri["round"], payload=payload))
        print(f"  {ri['slug']}: ok ({payload['meta']['winner']['code']} by "
              f"{payload['meta']['marginS']}s)")
    index = {"hero": HERO_SLUG, "races": sorted(races, key=lambda r: r["round"]),
             "entries": sorted(entries, key=lambda e: e["round"])}
    write_json_if_changed(DATA_DIR / "index.json", index)
    print(f"\nDone. {sum(e['valid'] for e in entries)}/{len(entries)} races decomposed.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests** — Run: `python -m pytest tests/test_race_win.py -v` → PASS.
- [ ] **Step 5: Commit**
```bash
git add scripts/build_race_decomp_data.py tests/test_race_win.py
git commit -m "feat: build_race_decomp_data writes per-race factor JSON + index"
```

---

### Task 5: Generate real data, sanity-check, wire CI

**Files:** generated `web/public/data/race/*.json`; modify `.github/workflows/deploy.yml`.

- [ ] **Step 1: Run the build on real data**

Run: `python scripts/build_race_decomp_data.py 2>&1 | tail -20`
Expected: per-race `ok`/`EXCLUDED` lines; files in `web/public/data/race/`. (FastF1 2026 race sessions are cached.)

- [ ] **Step 2: Sanity-check the numbers (real-data calibration gate)**

Run:
```bash
python3 -c "import json,glob; [print(p.split('/')[-1], {k:json.load(open(p))['factors'][k]['verdict'] for k in ['where','tyre','pace','start']}) for p in sorted(glob.glob('web/public/data/race/*.json')) if 'index' not in p]"
```
Expected: each race prints its four verdicts. **Sanity rules:** Monaco (hero, pole-to-flag) should NOT be `inherited`; Canada (Russell DNF) start/where should be `inherited`/`insufficient`; verdicts should not be uniformly `real` (that would mean thresholds are too loose) nor uniformly `noise` (too tight). If they look wrong, adjust the `*_REAL_*` constants in `src/race_verdict.py` and rebuild — this is the intended calibration step.

- [ ] **Step 3: Wire CI** — in `.github/workflows/deploy.yml`, after the existing data-build step(s), add:

```yaml
      - name: Build race-win decomposition data
        run: python scripts/build_race_decomp_data.py
```

- [ ] **Step 4: Commit**
```bash
git add web/public/data/race .github/workflows/deploy.yml
git commit -m "build: generate race-win decomposition data + wire CI"
```

---

## Self-Review
- **Coverage:** winner/P2/margin (T1) ✓; start/pace/tyre verdicts (T2) ✓; per-race assembly with where-placeholder (T3) ✓; build script + index + honest exclusion (T4) ✓; real data + calibration + CI (T5) ✓. Factor 1 deferred by design (placeholder schema stable).
- **Placeholder scan:** the only "placeholder" is the intentional `factors.where` block, schema-stable for the next plan. No TBDs.
- **Type consistency:** `principals_from_results` keys (winner/p2/marginS/anyDnf) consumed by `assemble_race`; verdict dicts (`magnitudeS/magnitudeUnit/verdict/headline/caveat`) consistent across T2/T3; `index_entry` reads `factors[k].verdict`. Serializer field names (`positionsGained`, `medianLaptime_s`, `degSlope_s_per_lap`) match `src/serialize.py`.

## Notes for the next plans
- **Plan 2 (factor 1)** replaces the `factors.where` placeholder: comparable-lap pairs (winner vs P2, same compound / ±tyre-age / ±lap / no traffic), the engine on those pairs, paired bootstrap CIs, the per-driver reconciliation fix; wires the real `decomp` payload into `build_one_race`. It also upgrades `pace_verdict` to a bootstrap-CI on comparable laps.
- **Plan 3 (web + cut)** consumes `web/public/data/race/{index.json,<slug>.json}` and deletes the dashboard/chapters.
