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
            grid, the gap is read from each car's own timing, and the decomposed curve must reconcile
            to the official lap-time gap within 0.05s or it isn't reported. Each sector's edge is kept
            only if a <strong className="text-zinc-200">5,000-sample bootstrap</strong> 95% CI excludes
            zero — otherwise it's labelled noise.
          </p>
          <p className="text-xs text-zinc-500">Full write-up: <StudyLinks className="text-zinc-300" /></p>
        </div>
      </Panel>
    </div>
  )
}
