"""Team / driver-pair resolution and completed-round discovery for the live
site pipeline.

Design: the analysis math is car-controlled via *teammates*, so the unit of the
tool is a team's driver pair. This module answers two questions from FastF1:

  1. Which rounds of a season have already run? (`list_completed_rounds`)
  2. For each team, who are its two drivers, and which is "A" vs "B"?
     (`resolve_pair_for_round`, `season_team_pairs`, `_canonical_from_round_pairs`)

A/B ordering is fixed by car number (lower number = A) so the existing sign
conventions in benchmarks/race (delta = B - A, positive = A faster) stay stable.

The FastF1-touching functions are thin wrappers; the testable logic lives in the
pure `_*` helpers, which operate on plain DataFrames and dicts.
"""
from __future__ import annotations

import re
from datetime import date

import fastf1
import pandas as pd

from src.loaders import setup_cache  # re-exported for the pipeline's convenience


def team_slug(team_name: str) -> str:
    """'Red Bull Racing' -> 'red-bull-racing'. Stable, lowercase, hyphenated."""
    s = re.sub(r"[^a-z0-9]+", "-", team_name.strip().lower())
    return s.strip("-")


def team_display_name(team_name: str) -> str:
    """The FastF1 TeamName is already display-ready; kept as a seam."""
    return team_name


def round_slug(event_name: str) -> str:
    """'Australian Grand Prix' -> 'australian'. Unique per round (event names are)."""
    base = event_name.replace("Grand Prix", "")
    return team_slug(base)


# ---- pure logic (unit-tested with mock DataFrames) -----------------------

def _pairs_from_results(results_df: pd.DataFrame) -> dict[str, dict]:
    """From a session.results-like DataFrame, return {team_name: {"a":..,"b":..}}.

    Each driver dict is {"code", "number", "name"}. Within a team the two drivers
    are ordered by DriverNumber ascending (lower = A). Defensive against a team
    showing >2 drivers in one session (takes the two lowest car numbers)."""
    out: dict[str, dict] = {}
    for team_name, grp in results_df.groupby("TeamName", sort=True):
        drivers = [
            {
                "code": str(r["Abbreviation"]),
                "number": int(r["DriverNumber"]),
                "name": str(r["FullName"]),
            }
            for _, r in grp.iterrows()
        ]
        drivers.sort(key=lambda d: d["number"])
        if len(drivers) < 2:
            continue  # a team with a single classified car this round is unusable
        out[team_name] = {"a": drivers[0], "b": drivers[1]}
    return out


def _completed_from_schedule(schedule_df: pd.DataFrame, today: date) -> list[dict]:
    """Rounds that have already run: RoundNumber present and != 0, EventDate <= today.
    Sorted by round number."""
    rows = []
    for _, r in schedule_df.iterrows():
        rnd = r["RoundNumber"]
        if pd.isna(rnd) or int(rnd) == 0:
            continue
        event_date = pd.Timestamp(r["EventDate"]).date()
        if event_date > today:
            continue
        rows.append(
            {
                "round": int(rnd),
                "slug": round_slug(str(r["EventName"])),
                "eventName": str(r["EventName"]),
                "eventDate": event_date.isoformat(),
                "country": str(r["Country"]),
                "location": str(r["Location"]),
                "format": str(r["EventFormat"]),
            }
        )
    rows.sort(key=lambda d: d["round"])
    return rows


def _next_from_schedule(schedule_df: pd.DataFrame, today: date) -> dict | None:
    """The earliest round whose EventDate is still in the future (the next race)."""
    rows = []
    for _, r in schedule_df.iterrows():
        rnd = r["RoundNumber"]
        if pd.isna(rnd) or int(rnd) == 0:
            continue
        d = pd.Timestamp(r["EventDate"]).date()
        if d > today:
            rows.append((int(rnd), r))
    if not rows:
        return None
    rows.sort(key=lambda x: x[0])
    rnd, r = rows[0]
    return {
        "round": rnd,
        "eventName": str(r["EventName"]),
        "country": str(r["Country"]),
        "location": str(r["Location"]),
        "eventDate": pd.Timestamp(r["EventDate"]).date().isoformat(),
        "format": str(r["EventFormat"]),
    }


def next_race(year: int, today: date | None = None) -> dict | None:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return _next_from_schedule(schedule, today or date.today())


def _canonical_from_round_pairs(round_pairs: list[dict]) -> dict:
    """Given one team's per-round pair dicts (in round order), pick the canonical
    pair (most frequent driver-code set; ties -> earliest occurrence) and flag a
    swap. Returns {"a":.., "b":.., "hasSwap": bool}."""
    counts: dict[frozenset, int] = {}
    first_seen: dict[frozenset, dict] = {}
    order: list[frozenset] = []
    for pr in round_pairs:
        key = frozenset({pr["a"]["code"], pr["b"]["code"]})
        if key not in counts:
            counts[key] = 0
            first_seen[key] = pr
            order.append(key)
        counts[key] += 1
    # Most frequent; tie broken by first appearance (stable order via `order`).
    best = max(order, key=lambda k: counts[k])
    rep = first_seen[best]
    return {"a": rep["a"], "b": rep["b"], "hasSwap": len(order) > 1}


def _match_prior_round(country: str, location: str, prior_rounds: list[dict]) -> int | None:
    """Match a round to its prior-season equivalent for cross-year (same-circuit)
    YoY. Location strings drift across years (e.g. Monaco's 'Monte Carlo' vs
    'Monaco'), so: prefer an exact Location match, else fall back to Country when
    that country is unambiguous in the prior season. Returns the prior round
    number, or None if no confident match (e.g. multiple same-country rounds and
    no location hit)."""
    for pr in prior_rounds:
        if pr["location"] == location:
            return pr["round"]
    same_country = [pr for pr in prior_rounds if pr["country"] == country]
    if len(same_country) == 1:
        return same_country[0]["round"]
    return None


def _yoy_available(canonical_codes: set[str], prior_year_codes: set[str]) -> bool:
    """True iff the same two drivers drove this team in the prior season."""
    return set(canonical_codes) <= set(prior_year_codes)


# ---- FastF1-touching wrappers (used by the pipeline; cache-backed) -------

def _load_results(year: int, round_number: int) -> pd.DataFrame:
    """Light load of a race session's results (no laps/telemetry/weather)."""
    session = fastf1.get_session(year, round_number, "R")
    session.load(laps=False, telemetry=False, weather=False, messages=False)
    return session.results


def list_completed_rounds(year: int, today: date | None = None) -> list[dict]:
    """Completed rounds of `year` from the FastF1 schedule. `today` overridable
    for testing/determinism. Adds hasQualifying/hasRace (True for run rounds)."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    rounds = _completed_from_schedule(schedule, today or date.today())
    for r in rounds:
        r["hasQualifying"] = True
        r["hasRace"] = True
    return rounds


def resolve_pair_for_round(year: int, round_number: int) -> dict[str, dict]:
    """{team_name: {"a":.., "b":..}} for one round, from its race results."""
    return _pairs_from_results(_load_results(year, round_number))


def season_team_pairs(year: int, rounds: list[int]) -> dict[str, list[dict]]:
    """{team_name: [per-round pair dict, ...]} accumulated over the given rounds,
    in round order. Rounds that fail to load are skipped (graceful)."""
    by_team: dict[str, list[dict]] = {}
    for rnd in rounds:
        try:
            pairs = resolve_pair_for_round(year, rnd)
        except Exception as exc:  # noqa: BLE001 - one bad round shouldn't abort
            print(f"  skip pair resolution {year} R{rnd}: {exc!r}")
            continue
        for team_name, pair in pairs.items():
            by_team.setdefault(team_name, []).append(pair)
    return by_team


def team_driver_codes(year: int, rounds: list[int]) -> dict[str, set[str]]:
    """{team_name: {all driver codes that drove for it across `rounds`}}."""
    codes: dict[str, set[str]] = {}
    for team_name, prs in season_team_pairs(year, rounds).items():
        s: set[str] = set()
        for pr in prs:
            s.update({pr["a"]["code"], pr["b"]["code"]})
        codes[team_name] = s
    return codes
