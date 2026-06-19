import { useEffect, useState } from 'react'
import { Panel, Badge, StudyLinks } from '../components/ui'
import { DeltaCurve } from '../components/decomp/DeltaCurve'
import { SectorVerdict } from '../components/decomp/SectorVerdict'
import { AttributionList } from '../components/decomp/AttributionList'
import { DecompTrackMap } from '../components/decomp/DecompTrackMap'
import { TyreFactor } from '../components/race/TyreFactor'
import { PaceFactor } from '../components/race/PaceFactor'
import { StartFactor } from '../components/race/StartFactor'
import { RacePicker } from '../components/race/RacePicker'
import { useRaceIndex, useRaceDecomp } from '../lib/data'
import type { DecompMatchup, Verdict } from '../types'

const VERDICT_TONE: Record<Verdict, 'sky' | 'zinc' | 'amber'> = {
  real: 'sky',
  noise: 'zinc',
  inherited: 'amber',
  insufficient: 'zinc',
}

export function RaceDecomp() {
  const { data: index, error: indexError } = useRaceIndex()

  const [pick, setPick] = useState<string>('')
  useEffect(() => {
    if (index && !pick) setPick(index.hero)
  }, [index, pick])

  const { data: race, error: raceError } = useRaceDecomp(pick || undefined)

  // Count verdicts
  const factorVerdicts = race
    ? [
        race.factors.where.verdict,
        race.factors.tyre.verdict,
        race.factors.pace.verdict,
        race.factors.start.verdict,
      ]
    : []
  const nReal = factorVerdicts.filter((v) => v === 'real').length
  const nNoise = factorVerdicts.filter((v) => v === 'noise').length

  // Hero subtitle
  const heroSub = race
    ? `${race.meta.winner.name} beat ${race.meta.p2.name} by ${
        race.meta.marginS !== null ? `${race.meta.marginS.toFixed(3)}s` : '—'
      } at ${race.meta.eventName} — decomposed into four causes, each ruled real or noise.`
    : 'Decomposing a race win into four causes and ruling each real or noise.'

  // where factor decomp cast
  const whereDecomp =
    race?.factors.where.decomp != null
      ? (race.factors.where.decomp as unknown as DecompMatchup)
      : null

  return (
    <div className="space-y-9">
      {/* Hero */}
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] uppercase tracking-widest text-f1-red">
          Race-win decomposition
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          What actually won this race — and what was noise?
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">{heroSub}</p>
      </section>

      {indexError && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load race index: {indexError}
        </p>
      )}
      {raceError && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load race data: {raceError}
        </p>
      )}

      {race && (
        <>
          {/* Stat strip */}
          <section className="grid grid-cols-3 gap-3">
            {[
              [
                'Winning margin',
                race.meta.marginS !== null
                  ? `${race.meta.marginS.toFixed(3)}s`
                  : '—',
              ],
              ['Real factors', `${nReal} / 4`],
              ['Within noise', `${nNoise} / 4`],
            ].map(([k, v]) => (
              <div
                key={k}
                className="rounded-lg border border-carbon-line bg-carbon-soft p-3 text-center"
              >
                <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
                  {k}
                </div>
                <div className="mt-1 font-mono text-sm text-white">{v}</div>
              </div>
            ))}
          </section>

          {race.meta.winnerInherited && (
            <p className="rounded border border-amber-700/50 bg-amber-900/30 px-3 py-2 text-xs text-amber-300">
              Lead inherited — winner benefited from a rival DNF. Verdicts below account for this.
            </p>
          )}

          {/* Where on track */}
          <Panel
            title="Where on track"
            subtitle="Where did the winner gain time lap-to-lap?"
            right={
              <Badge tone={VERDICT_TONE[race.factors.where.verdict]}>
                {race.factors.where.verdict}
              </Badge>
            }
          >
            <p className="mb-3 text-sm text-zinc-300">{race.factors.where.headline}</p>
            {whereDecomp ? (
              <div className="space-y-5">
                <DeltaCurve matchup={whereDecomp} />
                <SectorVerdict matchup={whereDecomp} />
                <AttributionList matchup={whereDecomp} />
                <DecompTrackMap matchup={whereDecomp} />
              </div>
            ) : null}
            {race.factors.where.caveat && (
              <p className="mt-3 text-[11px] text-zinc-600">{race.factors.where.caveat}</p>
            )}
          </Panel>

          {/* Tyre */}
          <TyreFactor factor={race.factors.tyre} />

          {/* Pace */}
          <PaceFactor factor={race.factors.pace} />

          {/* Start */}
          <StartFactor factor={race.factors.start} />
        </>
      )}

      {!race && !raceError && pick && (
        <p className="py-8 text-center text-sm text-zinc-500">Loading race data…</p>
      )}

      {/* Why this matters beyond F1 */}
      <Panel title="Why this matters beyond F1" subtitle="The transferable skill">
        <p className="py-1 text-sm text-zinc-400">
          Decomposing an outcome (a race win) into its true causes and refusing to credit a
          cause that's within noise is outcome attribution under uncertainty — the same shape as
          root-cause analysis, A/B-test readouts, and anomaly detection.
        </p>
      </Panel>

      {/* Explorer */}
      {index && (
        <Panel
          title="Explore other races"
          subtitle="Every race in the dataset — select to rerun the decomposition"
        >
          <div className="space-y-4 py-1">
            <RacePicker index={index} value={pick} onPick={setPick} />
            {race ? (
              <p className="text-xs text-zinc-500">
                {race.meta.winner.name} beat {race.meta.p2.name} ·{' '}
                {race.meta.eventName} ·{' '}
                {race.meta.marginS !== null
                  ? `${race.meta.marginS.toFixed(3)}s margin`
                  : 'margin unknown'}
                {' · '}
                {nReal} real factor{nReal !== 1 ? 's' : ''}, {nNoise} noise
              </p>
            ) : (
              <p className="py-6 text-center text-sm text-zinc-500">
                Select a race above.
              </p>
            )}
          </div>
        </Panel>
      )}

      {/* Method & trust */}
      <Panel title="Method & trust" subtitle="Why you can believe the split">
        <div className="space-y-3 py-1 text-sm text-zinc-400">
          <p>
            Laps are filtered to{' '}
            <strong className="text-zinc-200">clean laps</strong> (green flag, not lap 1,
            not in/out laps). Where-on-track uses{' '}
            <strong className="text-zinc-200">like-compound</strong> comparisons only. Fuel
            load is <strong className="text-zinc-200">not corrected</strong> — named
            explicitly so you know. The where-on-track factor runs{' '}
            <strong className="text-zinc-200">5,000-sample bootstrap CIs</strong> on
            comparable mid-stint laps to separate real sector edges from noise. The tyre,
            pace, and start verdicts are threshold-based point estimates — not CI-gated.
          </p>
          <p className="text-xs text-zinc-500">
            Full write-up: <StudyLinks className="text-zinc-300" />
          </p>
        </div>
      </Panel>
    </div>
  )
}
