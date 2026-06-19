# Lap-Decomposition Web Flagship — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the lap-decomposition the flagship of the Pitwall web app — a guided hero story (RUS vs ANT, Canada Q) plus a full-matrix explorer — rendered natively from the JSON the Data plan emits.

**Architecture:** New route `/` is a `Decomposition` page composed of small JSON-driven components (`DeltaCurve`, `SectorVerdict`, `DecompTrackMap`, `AttributionList`, `MatchupPicker`). The existing season dashboard moves to `/season`. Data is fetched via two new hooks mirroring `useSeason`/`useTelemetry`. The track map adapts the existing `SpeedTrackMap` (diverging color by rate instead of speed). Charts use Recharts (already a dependency).

**Tech Stack:** React 19, Vite 6, TypeScript 5.8, Tailwind 4, Recharts 2.15, React Router 7 (HashRouter). No new dependencies.

## Global Constraints

- This project has **no frontend unit-test runner**. The verification gate for every web task is: `npm run typecheck` (tsc --noEmit) clean AND `npm run build` succeeds. A committed sample `web/public/data/decomp/` (from the Data plan's synthetic demo) makes the page renderable during development. Do not add a test framework.
- Reuse existing primitives: `Panel`/`StudyLinks` (`web/src/components/ui.tsx`), chart helpers (`web/src/components/charts/common.tsx` — `tooltipStyle`, `axisTick`, `grid`, `zero`, `shortEvent`, `Empty`), Tailwind tokens (`carbon`, `carbon-soft`, `carbon-card`, `carbon-line`, `f1-red`). Match the existing F1 visual language (uppercase italic headers, `f1-bar` kicker, mono numerals).
- Data fetch path: `getJSON` in `web/src/lib/data.ts` resolves `${import.meta.env.BASE_URL}data/<path>` — all new hooks go through it so the GitHub Pages subpath works.
- Sign convention from the data: `deltaMean > 0` ⇒ A slower ⇒ **B faster** in that sector; the curve endpoint = official gap (`t_A − t_B`).
- All paths relative to repo root `/Users/mcoler/Documents/project-folder/f1_project`. Frontend commands run from `web/`.

**Prerequisite:** the Data plan (`2026-06-18-lap-decomposition-data.md`) is complete, and `web/public/data/decomp/index.json` + at least the hero matchup file exist (real or the synthetic demo). Confirm before starting:
Run: `ls web/public/data/decomp/` → expect `index.json` and one or more `<slug>__<A>_<B>.json`.

---

### Task 1: Decomp types + data hooks

**Files:**
- Modify: `web/src/types.ts` (append)
- Modify: `web/src/lib/data.ts` (append)

**Interfaces:**
- Produces (types): `DecompIndex`, `IndexMatchup`, `DecompMatchup`, `Sector`, `CurvePoint`, `CornerMark`, `AttributionItem`, `TrackPoint`.
- Produces (hooks): `useDecompIndex(): { data: DecompIndex|null; error: string|null }`, `useDecompMatchup(key: string|undefined): { data: DecompMatchup|null; error: string|null }`.

- [ ] **Step 1: Add the types**

Append to `web/src/types.ts`:

```typescript
// --- Lap decomposition (decomp/*.json) ---

export interface CurvePoint { d: number; delta: number | null }
export interface CornerMark { d: number | null; label: string }

export interface Sector {
  i: number
  startM: number | null
  endM: number | null
  midM: number | null
  deltaMean: number | null
  ciLow: number | null
  ciHigh: number | null
  significant: boolean
  faster: string | null
}

export interface AttributionItem {
  sector: number
  driverFaster: string
  deltaS: number | null
  significant: boolean
  narrative: string
}

export interface TrackPoint { x: number | null; y: number | null; rate: number | null }

export interface DecompDriver { code: string; name: string; team: string; color: string | null }

export interface DecompMatchup {
  meta: {
    race: string
    eventName: string
    round: number
    year: number
    session: string
    driverA: DecompDriver
    driverB: DecompDriver
    officialGapS: number | null
    reconResidualS: number | null
    nCleanLapsA: number
    nCleanLapsB: number
  }
  deltaCurve: CurvePoint[]
  corners: CornerMark[]
  sectors: Sector[]
  attribution: AttributionItem[]
  callouts: { topSignificant: number[]; noiseTrap: number | null }
  track: TrackPoint[]
}

export interface IndexMatchup {
  key: string
  race: string
  team: string
  teamColor: string | null
  a: string
  b: string
  valid: boolean
  officialGapS?: number | null
  significantCount?: number
  reason?: string
}

export interface DecompIndex {
  hero: string
  races: { slug: string; name: string; round: number }[]
  matchups: IndexMatchup[]
}
```

- [ ] **Step 2: Add the hooks**

Append to `web/src/lib/data.ts` (and extend the existing type import on line 2 to include the two new types):

```typescript
import type { DecompIndex, DecompMatchup } from '../types'

export function useDecompIndex() {
  const [data, setData] = useState<DecompIndex | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    getJSON<DecompIndex>('decomp/index.json')
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [])
  return { data, error }
}

export function useDecompMatchup(key: string | undefined) {
  const [data, setData] = useState<DecompMatchup | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!key) return
    let live = true
    setData(null)
    setError(null)
    getJSON<DecompMatchup>(`decomp/${key}.json`)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [key])
  return { data, error }
}
```

(Use the existing `import type { SeasonData, SessionTelemetry } from '../types'` line — either merge the new names into it or add the separate `import type` line shown above; both type-check.)

- [ ] **Step 3: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: both clean (no errors). New code is unused so far — that's fine.

- [ ] **Step 4: Commit**

```bash
git add web/src/types.ts web/src/lib/data.ts
git commit -m "feat(web): decomp JSON types + data hooks"
```

---

### Task 2: DeltaCurve component

The cumulative time-delta curve — the core artefact. Recharts line, zero reference, corner reference lines.

**Files:**
- Create: `web/src/components/decomp/DeltaCurve.tsx`

**Interfaces:**
- Produces: `DeltaCurve({ matchup }: { matchup: DecompMatchup })`.

- [ ] **Step 1: Implement**

Create `web/src/components/decomp/DeltaCurve.tsx`:

```tsx
import {
  Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DecompMatchup } from '../../types'
import { axisTick, tooltipStyle, zero } from '../charts/common'

export function DeltaCurve({ matchup }: { matchup: DecompMatchup }) {
  const { deltaCurve, corners, meta } = matchup
  const a = meta.driverA.code
  const b = meta.driverB.code

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={deltaCurve} margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
          <XAxis
            dataKey="d" type="number" domain={['dataMin', 'dataMax']}
            tick={axisTick} tickFormatter={(v) => `${Math.round(v)}m`}
            stroke={zero}
          />
          <YAxis
            tick={axisTick} width={48}
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}s`}
            stroke={zero}
          />
          <ReferenceLine y={0} stroke={zero} />
          {corners.map((c) =>
            c.d == null ? null : (
              <ReferenceLine key={c.label} x={c.d} stroke="#3f3f46" strokeDasharray="2 3"
                label={{ value: c.label, position: 'top', fill: '#71717a', fontSize: 9 }} />
            ),
          )}
          <Tooltip
            {...tooltipStyle}
            formatter={(v: number) => [`${v > 0 ? '+' : ''}${v.toFixed(3)}s`, `${a} − ${b}`]}
            labelFormatter={(d: number) => `${Math.round(d)} m`}
          />
          <Line type="monotone" dataKey="delta" stroke="#e10600" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-center text-[11px] text-zinc-500">
        Cumulative time gap (<span className="text-zinc-300">{a} − {b}</span>) along the lap.
        Rising = {b} pulling ahead; the finish-line value is the official gap.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/decomp/DeltaCurve.tsx
git commit -m "feat(web): cumulative delta curve chart"
```

---

### Task 3: SectorVerdict component

Per-micro-sector mean delta as bars with 95% CI error bars, green = real / grey = noise.

**Files:**
- Create: `web/src/components/decomp/SectorVerdict.tsx`

**Interfaces:**
- Produces: `SectorVerdict({ matchup }: { matchup: DecompMatchup })`.

- [ ] **Step 1: Implement**

Create `web/src/components/decomp/SectorVerdict.tsx`:

```tsx
import {
  Bar, BarChart, Cell, ErrorBar, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DecompMatchup } from '../../types'
import { axisTick, tooltipStyle, zero } from '../charts/common'

const REAL = '#22c55e'   // CI excludes zero
const NOISE = '#52525b'  // CI straddles zero

export function SectorVerdict({ matchup }: { matchup: DecompMatchup }) {
  // Recharts ErrorBar wants asymmetric offsets [down, up] from the bar value.
  const data = matchup.sectors.map((s) => {
    const mean = s.deltaMean ?? 0
    const lo = s.ciLow ?? mean
    const hi = s.ciHigh ?? mean
    return { ...s, mean, err: [mean - lo, hi - mean] as [number, number] }
  })
  const nReal = matchup.sectors.filter((s) => s.significant).length

  return (
    <div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
            <XAxis dataKey="i" tick={axisTick} stroke={zero}
              label={{ value: 'micro-sector', position: 'insideBottom', offset: -8, fill: '#71717a', fontSize: 10 }} />
            <YAxis tick={axisTick} width={48}
              tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}s`} stroke={zero} />
            <ReferenceLine y={0} stroke={zero} />
            <Tooltip
              {...tooltipStyle}
              formatter={(v: number, _n, p) => {
                const s = p.payload
                const tag = s.significant ? 'real' : 'noise'
                return [`${v > 0 ? '+' : ''}${v.toFixed(3)}s  [${(s.ciLow ?? 0).toFixed(3)}, ${(s.ciHigh ?? 0).toFixed(3)}]  ${tag}`, `sector ${s.i}`]
              }}
              labelFormatter={() => ''}
            />
            <Bar dataKey="mean" isAnimationActive={false}>
              {data.map((s) => <Cell key={s.i} fill={s.significant ? REAL : NOISE} />)}
              <ErrorBar dataKey="err" width={3} strokeWidth={1} stroke="#a1a1aa" direction="y" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-center text-[11px] text-zinc-500">
        <span style={{ color: REAL }}>■</span> {nReal} real (CI excludes 0) ·{' '}
        <span style={{ color: NOISE }}>■</span> {matchup.sectors.length - nReal} within noise.
        Bars are mean Δ per sector; whiskers are the 95% bootstrap CI.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/decomp/SectorVerdict.tsx
git commit -m "feat(web): per-sector verdict bars with bootstrap CIs"
```

---

### Task 4: DecompTrackMap component

Adapt `SpeedTrackMap` to color the lap by rate of time gain/loss (diverging around zero).

**Files:**
- Create: `web/src/components/decomp/DecompTrackMap.tsx`

**Interfaces:**
- Produces: `DecompTrackMap({ matchup }: { matchup: DecompMatchup })`.

- [ ] **Step 1: Implement**

Create `web/src/components/decomp/DecompTrackMap.tsx`:

```tsx
import type { DecompMatchup } from '../../types'

// Diverging color: t in [-1,1]. Negative (A faster here) -> blue; positive
// (B faster here) -> red; near zero -> grey.
function rateColor(t: number): string {
  const mag = Math.min(1, Math.abs(t))
  const light = 30 + mag * 30
  if (t < 0) return `hsl(210,90%,${light}%)`
  if (t > 0) return `hsl(0,90%,${light}%)`
  return 'hsl(0,0%,45%)'
}

export function DecompTrackMap({ matchup }: { matchup: DecompMatchup }) {
  const pts = matchup.track.filter((p) => p.x != null && p.y != null) as
    { x: number; y: number; rate: number | null }[]
  const n = pts.length
  if (n < 2) return <p className="py-8 text-center text-sm text-zinc-500">No track geometry.</p>

  const a = matchup.meta.driverA.code
  const b = matchup.meta.driverB.code
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const PAD = 24
  const VIEW = 600
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const scale = (VIEW - PAD * 2) / Math.max(maxX - minX || 1, maxY - minY || 1)
  const sx = (v: number) => PAD + (v - minX) * scale
  const sy = (v: number) => VIEW - PAD - (v - minY) * scale

  const maxRate = Math.max(1e-6, ...pts.map((p) => Math.abs(p.rate ?? 0)))

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${VIEW} ${VIEW + 36}`} className="mx-auto block w-full max-w-[600px]"
        aria-label={`Where time is won and lost, ${a} vs ${b}`}>
        {Array.from({ length: n - 1 }, (_, i) => (
          <line key={i} x1={sx(pts[i].x)} y1={sy(pts[i].y)} x2={sx(pts[i + 1].x)} y2={sy(pts[i + 1].y)}
            stroke={rateColor((pts[i].rate ?? 0) / maxRate)} strokeWidth={5}
            strokeLinecap="round" strokeLinejoin="round" />
        ))}
        <circle cx={sx(pts[0].x)} cy={sy(pts[0].y)} r={6} fill="white" stroke="#e10600" strokeWidth={2} />
        <text x={PAD} y={VIEW + 22} fontSize={11} fill="#60a5fa" fontFamily="inherit">{a} faster</text>
        <text x={VIEW - PAD} y={VIEW + 22} fontSize={11} fill="#f87171" fontFamily="inherit" textAnchor="end">{b} faster</text>
      </svg>
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/decomp/DecompTrackMap.tsx
git commit -m "feat(web): track map colored by where time is won/lost"
```

---

### Task 5: AttributionList + the noise-trap callout

Render the one-sentence causes at the real sectors, and spotlight the sector that looked like an edge but isn't.

**Files:**
- Create: `web/src/components/decomp/AttributionList.tsx`

**Interfaces:**
- Produces: `AttributionList({ matchup }: { matchup: DecompMatchup })`.

- [ ] **Step 1: Implement**

Create `web/src/components/decomp/AttributionList.tsx`:

```tsx
import type { DecompMatchup } from '../../types'

export function AttributionList({ matchup }: { matchup: DecompMatchup }) {
  const { attribution, callouts, sectors } = matchup
  const trap = callouts.noiseTrap == null
    ? null
    : sectors.find((s) => s.i === callouts.noiseTrap) ?? null

  return (
    <div className="space-y-3">
      {attribution.length === 0 ? (
        <p className="text-sm text-zinc-400">
          No micro-sector advantage was statistically distinguishable from zero at this sample
          size — the lap-time gap is within lap-to-lap noise.
        </p>
      ) : (
        attribution.map((row) => (
          <div key={row.sector} className="rounded-md border border-carbon-line bg-carbon-soft p-3">
            <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">
              Sector {row.sector} · faster: {row.driverFaster}
            </div>
            <p className="mt-1 text-sm text-zinc-300">{row.narrative}</p>
          </div>
        ))
      )}

      {trap && (
        <div className="rounded-md border border-f1-red/40 bg-f1-red/10 p-3">
          <div className="text-[11px] font-bold uppercase tracking-widest text-f1-red">
            The trap
          </div>
          <p className="mt-1 text-sm text-zinc-300">
            Sector {trap.i} shows a {(trap.deltaMean ?? 0) > 0 ? '+' : ''}
            {(trap.deltaMean ?? 0).toFixed(3)}s “edge”, but its 95% CI [
            {(trap.ciLow ?? 0).toFixed(3)}, {(trap.ciHigh ?? 0).toFixed(3)}] straddles zero — not a
            real advantage, just a good/bad lap. Calling that out is the discipline.
          </p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/decomp/AttributionList.tsx
git commit -m "feat(web): attribution narratives + noise-trap callout"
```

---

### Task 6: MatchupPicker

Race × Team selects driving the explorer; excluded matchups are shown disabled with their reason.

**Files:**
- Create: `web/src/components/decomp/MatchupPicker.tsx`

**Interfaces:**
- Consumes: `DecompIndex` (Task 1).
- Produces: `MatchupPicker({ index, value, onPick }: { index: DecompIndex; value: string; onPick: (key: string) => void })`.

- [ ] **Step 1: Implement**

Create `web/src/components/decomp/MatchupPicker.tsx`:

```tsx
import { useMemo } from 'react'
import type { DecompIndex } from '../../types'

const SELECT_CLS =
  'rounded-sm border border-carbon-line bg-carbon-card px-3 py-1.5 text-xs font-semibold ' +
  'uppercase tracking-wide text-zinc-200 focus:outline-none focus:border-zinc-500 ' +
  'cursor-pointer hover:border-zinc-500 transition'

export function MatchupPicker({
  index, value, onPick,
}: { index: DecompIndex; value: string; onPick: (key: string) => void }) {
  const current = index.matchups.find((m) => m.key === value)
  const race = current?.race ?? index.races[0]?.slug

  const teamsForRace = useMemo(
    () => index.matchups.filter((m) => m.race === race),
    [index.matchups, race],
  )

  const pickRace = (slug: string) => {
    const first = index.matchups.find((m) => m.race === slug && m.valid)
      ?? index.matchups.find((m) => m.race === slug)
    if (first) onPick(first.key)
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Race</label>
        <select className={SELECT_CLS} value={race} onChange={(e) => pickRace(e.target.value)}>
          {index.races.map((r) => (
            <option key={r.slug} value={r.slug}>{r.name}</option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Teammates</label>
        <select className={SELECT_CLS} value={value} onChange={(e) => onPick(e.target.value)}>
          {teamsForRace.map((m) => (
            <option key={m.key} value={m.key} disabled={!m.valid}>
              {m.team}: {m.a} v {m.b}{m.valid ? '' : ` — ${m.reason ?? 'excluded'}`}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/decomp/MatchupPicker.tsx
git commit -m "feat(web): race x team matchup picker with excluded reasons"
```

---

### Task 7: The Decomposition flagship page

Compose the hero story (fixed hero matchup) + the explorer + the "beyond F1" beat + method/links.

**Files:**
- Create: `web/src/pages/Decomposition.tsx`

**Interfaces:**
- Consumes: `useDecompIndex`, `useDecompMatchup` (Task 1); all decomp components (Tasks 2–6); `Panel`, `StudyLinks` (`ui.tsx`).
- Produces: `Decomposition()` (default-style export used by the router in Task 8).

- [ ] **Step 1: Implement**

Create `web/src/pages/Decomposition.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Panel, StudyLinks } from '../components/ui'
import { DeltaCurve } from '../components/decomp/DeltaCurve'
import { SectorVerdict } from '../components/decomp/SectorVerdict'
import { DecompTrackMap } from '../components/decomp/DecompTrackMap'
import { AttributionList } from '../components/decomp/AttributionList'
import { MatchupPicker } from '../components/decomp/MatchupPicker'
import { useDecompIndex, useDecompMatchup } from '../lib/data'
import type { DecompMatchup } from '../types'

function gapLine(m: DecompMatchup): string {
  const g = m.meta.officialGapS ?? 0
  const ahead = g <= 0 ? m.meta.driverA.code : m.meta.driverB.code
  return `${Math.abs(g).toFixed(3)}s — ${ahead} ahead`
}

export function Decomposition() {
  const { data: index, error: indexError } = useDecompIndex()
  const { data: hero } = useDecompMatchup(index?.hero)

  const [pick, setPick] = useState<string>('')
  useEffect(() => { if (index && !pick) setPick(index.hero) }, [index, pick])
  const { data: picked } = useDecompMatchup(pick || undefined)

  const nReal = hero ? hero.sectors.filter((s) => s.significant).length : 0
  const nNoise = hero ? hero.sectors.length - nReal : 0

  return (
    <div className="space-y-9">
      {/* Hook */}
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] uppercase tracking-widest text-f1-red">
          Lap-time decomposition
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          Where does a lap gap come from — and is it real?
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          {hero
            ? `${hero.meta.driverA.name} vs ${hero.meta.driverB.name}, ${hero.meta.eventName} qualifying — same car, ${gapLine(hero)}. We split that gap by corner and ask which differences are real and which are noise.`
            : 'Splitting one qualifying lap-time gap by corner, and separating real driver edges from lap-to-lap noise.'}
        </p>
      </section>

      {indexError && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load decomposition data: {indexError}
        </p>
      )}

      {hero && (
        <>
          {/* Stat strip */}
          <section className="grid grid-cols-3 gap-3">
            {[
              ['Official gap', gapLine(hero)],
              ['Real corners', `${nReal}`],
              ['Within noise', `${nNoise}`],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg border border-carbon-line bg-carbon-soft p-3 text-center">
                <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{k}</div>
                <div className="mt-1 font-mono text-sm text-white">{v}</div>
              </div>
            ))}
          </section>

          <Panel title="The curve" subtitle="Cumulative time gap along the lap">
            <DeltaCurve matchup={hero} />
          </Panel>

          <Panel title="Verdict — signal vs noise" subtitle="Per micro-sector, with 95% bootstrap CIs">
            <SectorVerdict matchup={hero} />
          </Panel>

          <Panel title="Why — and the trap" subtitle="The cause at the real sectors; the edge that isn't">
            <AttributionList matchup={hero} />
          </Panel>

          <Panel title="Where on track" subtitle="Coloured by where each driver gains time">
            <DecompTrackMap matchup={hero} />
          </Panel>
        </>
      )}

      {/* Beyond F1 — the single light-touch beat */}
      <Panel title="Why this matters beyond F1" subtitle="The transferable skill">
        <p className="py-1 text-sm text-zinc-400">
          Strip the motorsport away and this is signal-vs-noise extraction from a noisy,
          irregularly-sampled time series: align two traces on a common axis, decompose an
          aggregate into where it comes from, and use confidence intervals to refuse to call a
          random swing a finding. The same shape as root-cause attribution, A/B testing, and
          anomaly detection.
        </p>
      </Panel>

      {/* Explorer */}
      {index && (
        <Panel title="Explore other matchups" subtitle="Any teammate pair, any race — excluded ones say why">
          <div className="space-y-4 py-1">
            <MatchupPicker index={index} value={pick} onPick={setPick} />
            {picked ? (
              <div className="space-y-5">
                <p className="text-xs text-zinc-500">
                  {picked.meta.driverA.name} vs {picked.meta.driverB.name} ·{' '}
                  {picked.meta.eventName} · {gapLine(picked)}
                </p>
                <DeltaCurve matchup={picked} />
                <SectorVerdict matchup={picked} />
                <DecompTrackMap matchup={picked} />
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-zinc-500">Select a valid matchup.</p>
            )}
          </div>
        </Panel>
      )}

      {/* Method & trust */}
      <Panel title="Method & trust" subtitle="Why you can believe the split">
        <div className="space-y-3 py-1 text-sm text-zinc-400">
          <p>
            Both laps are resampled onto a common <strong className="text-zinc-200">distance</strong>{' '}
            grid, the gap is read from each car’s own timing, and the decomposed curve must reconcile
            to the official lap-time gap within 0.05s or it isn’t reported. Each sector’s edge is kept
            only if a <strong className="text-zinc-200">5,000-sample bootstrap</strong> 95% CI excludes
            zero — otherwise it’s labelled noise.
          </p>
          <p className="text-xs text-zinc-500">Full write-up: <StudyLinks className="text-zinc-300" /></p>
        </div>
      </Panel>
    </div>
  )
}
```

- [ ] **Step 2: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean (page is still unrouted; that’s fine).

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Decomposition.tsx
git commit -m "feat(web): decomposition flagship page (hero story + explorer)"
```

---

### Task 8: Routing reorientation

Make `/` the flagship; move the season dashboard to `/season`; update nav; drop the now-redundant thesis strip from the dashboard.

**Files:**
- Modify: `web/src/App.tsx`
- Modify: `web/src/pages/Dashboard.tsx` (remove the thesis strip added earlier; the flagship owns the thesis now)

**Interfaces:**
- Consumes: `Decomposition` (Task 7).

- [ ] **Step 1: Update the router + nav (`web/src/App.tsx`)**

Add the import and reorder routes/nav. Replace the import block, `Nav`'s `<nav>` links, and `<Routes>`:

```tsx
import { Decomposition } from './pages/Decomposition'
```

Nav links (inside `<nav className="flex items-center gap-5">`):

```tsx
        <NavLink to="/" className={link} end>
          Lap Gap
        </NavLink>
        <NavLink to="/season" className={link}>
          Season
        </NavLink>
        <NavLink to="/telemetry" className={link}>
          Telemetry
        </NavLink>
        <NavLink to="/about" className={link}>
          About
        </NavLink>
```

Routes:

```tsx
        <Routes>
          <Route path="/" element={<Decomposition />} />
          <Route path="/season" element={<Dashboard />} />
          <Route path="/telemetry" element={<Telemetry />} />
          <Route path="/about" element={<About />} />
        </Routes>
```

- [ ] **Step 2: Remove the redundant thesis strip from `web/src/pages/Dashboard.tsx`**

Delete the entire `{/* Thesis strip — names the method and points to the full analysis */}` `<section>...</section>` block (the one added earlier, containing "The question" kicker). Leave the rest of the Dashboard intact. Verify the `StudyLinks` import is still used elsewhere in the file; if it is now unused, remove it from the import to keep the build clean.

- [ ] **Step 3: Verify type-check + build**

Run: `cd web && npm run typecheck && npm run build`
Expected: clean. (If tsc flags an unused `StudyLinks`/`Panel` import in Dashboard, remove it.)

- [ ] **Step 4: Visual smoke test**

Run: `cd web && (npm run dev -- --port 5173 &) ; sleep 3 ; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5173/`
Expected: HTTP 200. Open `http://localhost:5173/` and confirm: `/` shows the hero story; `/season` shows the old dashboard; nav highlights work. Then stop the dev server: `lsof -ti tcp:5173 | xargs kill -9`.

- [ ] **Step 5: Commit**

```bash
git add web/src/App.tsx web/src/pages/Dashboard.tsx
git commit -m "feat(web): make decomposition the landing route; demote season dashboard"
```

---

### Task 9: README reorientation

Lead the repo with the decomposition as the headline; reframe the 3-chapter season work as a companion.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite the top of `README.md`**

Replace the H1 + hook + the "The method (and why it's the real subject)" block so the decomposition leads. New top (keep everything from "## The three chapters" downward, but introduce it as the companion analysis):

```markdown
# Pulling Signal From Noise: Where Does an F1 Lap Gap Come From?

**Two teammates, same car, ~0.07s apart over a qualifying lap. How much of that gap is real driver skill, and how much is lap-to-lap luck?** This project decomposes a single lap-time gap **spatially** (a cumulative time-delta curve sliced into corner-anchored micro-sectors) and **statistically** (a 5,000-sample bootstrap that flags which corners are real and which are noise), then names the driver input behind each real one.

> **Live flagship:** the interactive decomposition — hero story + explore any teammate pair at any race — is the front page of the [Pitwall web app](https://milescoler.github.io/antonelli-vs-russell/). One-page method write-up: [`f1-performance-decomposition/REPORT.md`](f1-performance-decomposition/REPORT.md).

The real subject isn't any one driver — it's **measurement discipline**: align two irregularly-sampled traces on a common distance axis, reconcile the decomposition against the officially-measured gap (a hard correctness gate), and use confidence intervals to refuse to call a noisy swing a finding. The clearest proof it's honest: an early qualifying result showed large per-corner deltas that were really a frozen speed sensor at Japan — a freeze-detection filter collapsed them to ~0.

## Companion analysis — a season-wide driver-vs-car study

Alongside the single-lap decomposition, a three-chapter season study controls for the car three more ways (same car across a season, same race, same track across years):
```

(Then keep the existing "The three chapters" table and the rest of the README unchanged.)

- [ ] **Step 2: Verify links resolve**

Run: `git ls-files f1-performance-decomposition/REPORT.md README.md`
Expected: both listed (paths valid).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: lead the repo with the lap-decomposition flagship"
```

---

### Task 10: End-to-end verification

**Files:** none (verification).

- [ ] **Step 1: Full type-check + production build**

Run: `cd web && npm run typecheck && npm run build`
Expected: both clean.

- [ ] **Step 2: Render the flagship from real/sample data**

Run: `cd web && (npm run dev -- --port 5173 &) ; sleep 3 ; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5173/ ; lsof -ti tcp:5173 | xargs kill -9`
Then open `http://localhost:5173/` and check the hero: curve renders, verdict bars are green/grey with whiskers, the trap callout shows, the track map is blue/red, and the explorer picker switches matchups (and greys excluded ones).

- [ ] **Step 3: The 60-second test**

Open `/` cold on a narrow viewport. Confirm the headline (where the gap is, how many corners are real vs noise, the trap) is legible without deep scrolling, and that "Read the full analysis" links resolve to GitHub.

- [ ] **Step 4: Commit any final copy tweaks**

```bash
git add -A
git commit -m "polish(web): decomposition flagship copy + layout"
```

---

## Self-Review

- **Spec coverage:** flagship `/` route ✓ (Task 8); hero story beats — hook/curve/verdict/trap/why/track/beyond-F1/method ✓ (Task 7 + components 2–5); explorer with honest exclusion ✓ (Tasks 6–7); JSON-driven web-native rendering ✓ (Recharts/SVG, no images); season dashboard demoted not deleted ✓ (Task 8); README reorientation ✓ (Task 9); light-touch "beyond F1" beat ✓ (Task 7). Nav label default "Lap Gap" and method behind concise copy ✓.
- **Placeholder scan:** every component has complete code; no TBDs. Verification uses tsc+build+visual because the project has no FE test runner (called out in Global Constraints).
- **Type consistency:** component props all take `{ matchup: DecompMatchup }` or the index types from Task 1; `DecompMatchup`/`Sector`/`IndexMatchup` field names match the JSON the Data plan emits (`deltaMean`, `ciLow`, `ciHigh`, `significant`, `callouts.noiseTrap`, `track[].rate`, `meta.officialGapS`). Hook names `useDecompIndex`/`useDecompMatchup` are consistent across Tasks 1, 7.

## Dependency on the Data plan
This plan requires `web/public/data/decomp/index.json` + matchup files (from the Data plan, real or synthetic demo). With only the synthetic demo present, the hero renders and the explorer shows a single matchup; the full matrix appears once CI runs the live build.
