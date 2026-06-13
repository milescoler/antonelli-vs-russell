# Separating the Driver from the Car

## How good is Kimi Antonelli, really?

**Antonelli has won 5 of the last 6 races. How much is the driver, and how much is the Mercedes?** Driver and car are tangled in every result, so this project pulls them apart three ways — each controlling for the car from a different angle. The throughline: a fast car flatters a driver *everywhere*, so the signal worth trusting is whatever survives once the car is divided out.

![Year-over-year: Antonelli vs Russell at the same six tracks](../figures/year_over_year.png)

## Chapter 1 — Qualifying (same car, same season)

Antonelli and Russell share a Mercedes, so their fastest-lap delta is mostly driver.

- **Most durable signal:** year-over-year, Antonelli has gained **+0.55 s/track** on Russell at the same six tracks vs his 2025 rookie season (range 0.29–0.77).
- **2026 trajectory is noisy, not monotone:** R1 −0.29 → R2 +0.22 → R3 +0.30 → R4 +0.40 → R5 −0.07 → R6 +0.39 (six-race mean **+0.16 s**). The early climb broke at Canada, then snapped back with a dominant Monaco pole.
- **Where the time comes from:** the segment split is flat, but at fast corners (200 kph+) he brakes ~15 m later and gets to full throttle ~19 m sooner than Russell — the late-brake / early-throttle commitment signature.

## Chapter 2 — Race wins (same car, same race)

Qualifying explains the grid, not the wins. Using Russell plus each race's actual P2 finisher as references: Antonelli generally *converts* the start and *extends* his lead when out front (Monaco: pole to flag-to-flag). The honest edges — Canada's win was partly inherited (Russell retired from the lead), and Australia is a clean P2→P2 loss — are named, not hidden. Pace and degradation are read like-compound only and are not fuel-corrected.

## Chapter 3 — Track history (same track, across years)

The teammate comparison removes the car within a season; this removes it across seasons. For each driver-year I take *(their average finish over the season's other rounds) − (their finish at this track)* — overperformance with car quality divided out — and average it over 2010–2025, per driver and per team.

![Monaco: is it a driver track or a car track?](../figures/driver_vs_car_monaco.png)

- Among drivers/teams with 3+ years at Monaco, the largest *persistent* overperformance belongs to teams about as much as to any single driver — so in this dataset even the archetypal "driver's track" reads partly as a **car track**.
- Each 2026 track is tagged driver- vs car-dependent, against Mercedes' historical standing, to give every Antonelli win a "how much was the car here?" read.

## What I learned doing this

An earlier version of the qualifying chapter reported large per-category deltas that turned out to be a frozen speed sensor at Japan; a freeze-detection filter collapsed them to ~0. Carrying that honesty forward, Chapter 3 excludes DNF/lapped rounds and cross-checks on grid position, flags small samples explicitly, and states plainly that the historical data is this project's own (internally consistent, not real-world F1). The whole pipeline refreshes after each race from a single `RACES` list.

---

**Repo:** github.com/milescoler/antonelli-vs-russell · **Cole Richards** · UCLA Statistics & Data Science · milescoler@gmail.com · [milescoler.github.io](https://milescoler.github.io)

Built in Python with FastF1, pandas, matplotlib, and pytest.
