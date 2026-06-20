import { useEffect, useState } from 'react'
import { Panel, StudyLinks } from '../components/ui'
import { DeltaCurve } from '../components/decomp/DeltaCurve'
import { SectorVerdict } from '../components/decomp/SectorVerdict'
import { AttributionList } from '../components/decomp/AttributionList'
import { DecompTrackMap } from '../components/decomp/DecompTrackMap'
import { TyreFactor } from '../components/race/TyreFactor'
import { PaceFactor } from '../components/race/PaceFactor'
import { StartFactor } from '../components/race/StartFactor'
import { RacePicker } from '../components/race/RacePicker'
import { useRaceIndex, useRaceDecomp } from '../lib/data'
import type { DecompMatchup, Verdict, RaceDecomp as RaceDecompData } from '../types'

type FactorKey = 'pace' | 'where' | 'tyre' | 'start'

const FACTOR_META: { key: FactorKey; label: string; short: string }[] = [
  { key: 'pace', label: 'Race pace', short: 'race pace' },
  { key: 'where', label: 'Where on track', short: 'corner-level pace' },
  { key: 'tyre', label: 'Tyre management', short: 'tyre management' },
  { key: 'start', label: 'Start & track position', short: 'the start' },
]

const VERDICT_DOT: Record<Verdict, string> = {
  real: 'bg-emerald-500',
  noise: 'bg-zinc-600',
  inherited: 'bg-amber-500',
  insufficient: 'bg-zinc-700',
}
const VERDICT_STAMP: Record<Verdict, string> = {
  real: 'REAL',
  noise: 'noise',
  inherited: 'inherited',
  insufficient: 'n/a',
}
const VERDICT_STAMP_CLASS: Record<Verdict, string> = {
  real: 'text-emerald-400',
  noise: 'text-zinc-500',
  inherited: 'text-amber-400',
  insufficient: 'text-zinc-600',
}
// real first, then inherited, noise, insufficient
const VERDICT_RANK: Record<Verdict, number> = { real: 0, inherited: 1, noise: 2, insufficient: 3 }

function joinList(items: string[]): string {
  if (items.length === 0) return ''
  if (items.length === 1) return items[0]
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`
}

function takeaway(race: RaceDecompData): string {
  const reals = FACTOR_META.filter((f) => race.factors[f.key].verdict === 'real').map((f) => f.short)
  const noises = FACTOR_META.filter((f) => race.factors[f.key].verdict === 'noise').map((f) => f.short)
  let s = reals.length
    ? `Won on ${joinList(reals)}.`
    : 'No single factor stood out as a clear, repeatable cause at this sample size.'
  if (race.meta.winnerInherited) {
    s += ' The lead was inherited — a rival ahead retired.'
  } else if (noises.length) {
    const list = joinList(noises)
    s += ` ${list.charAt(0).toUpperCase()}${list.slice(1)} ${noises.length > 1 ? 'were' : 'was'} within noise.`
  }
  return s
}

export function RaceDecomp() {
  const { data: index, error: indexError } = useRaceIndex()

  const [pick, setPick] = useState<string>('')
  useEffect(() => {
    if (index && !pick) setPick(index.hero)
  }, [index, pick])

  const { data: race, error: raceError } = useRaceDecomp(pick || undefined)

  // which factor's evidence is expanded (accordion); collapse when the race changes
  const [open, setOpen] = useState<FactorKey | null>(null)
  useEffect(() => {
    setOpen(null)
  }, [pick])

  const whereDecomp =
    race?.factors.where.decomp != null
      ? (race.factors.where.decomp as unknown as DecompMatchup)
      : null

  const margin = (m: number | null) => (m !== null ? `${m.toFixed(3)}s` : '—')

  // factor rows, real-first
  const rows = race
    ? [...FACTOR_META].sort(
        (a, b) =>
          VERDICT_RANK[race.factors[a.key].verdict] - VERDICT_RANK[race.factors[b.key].verdict],
      )
    : []

  function evidence(key: FactorKey) {
    if (!race) return null
    if (key === 'where') {
      return whereDecomp ? (
        <div className="space-y-5">
          <DeltaCurve matchup={whereDecomp} />
          <SectorVerdict matchup={whereDecomp} />
          <AttributionList matchup={whereDecomp} />
          <DecompTrackMap matchup={whereDecomp} />
        </div>
      ) : (
        <p className="text-sm text-zinc-500">
          No corner-level breakdown — the winner and runner-up never ran enough comparable laps
          to decompose where on track.
        </p>
      )
    }
    if (key === 'tyre') return <TyreFactor factor={race.factors.tyre} embedded />
    if (key === 'pace') return <PaceFactor factor={race.factors.pace} embedded />
    return <StartFactor factor={race.factors.start} embedded />
  }

  return (
    <div className="space-y-9">
      {/* Hero — lead with the statistic: how much P1 beat P2 by */}
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] uppercase tracking-widest text-f1-red">
          {race ? `${race.meta.eventName} · ${race.meta.year}` : 'Race-win decomposition'}
        </div>
        {race ? (
          <div className="mt-3">
            <p className="text-base font-medium tracking-tight text-zinc-400 sm:text-lg">
              <span className="font-semibold text-white">{race.meta.winner.name}</span> beat{' '}
              <span className="font-semibold text-zinc-200">{race.meta.p2.name}</span> by
            </p>
            <div className="-mt-1 flex items-baseline gap-1.5">
              <span className="text-6xl font-black tabular-nums tracking-tighter text-white sm:text-8xl">
                {race.meta.marginS !== null ? race.meta.marginS.toFixed(3) : '—'}
              </span>
              <span className="text-3xl font-bold text-zinc-500 sm:text-4xl">s</span>
            </div>
            <p className="mt-3 max-w-xl text-sm text-zinc-500">
              The winning margin, decomposed into its real causes — and the noise.
            </p>
          </div>
        ) : (
          <h1 className="mt-2 text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
            What won the race?
          </h1>
        )}
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

      {/* Scorecard */}
      {race && (
        <Panel
          title="What actually won it?"
          subtitle="Four causes, each ruled real or noise · tap a factor for the evidence"
        >
          <div className="divide-y divide-carbon-line">
            {rows.map((f) => {
              const fx = race.factors[f.key]
              const isOpen = open === f.key
              return (
                <div key={f.key}>
                  <button
                    onClick={() => setOpen(isOpen ? null : f.key)}
                    className="flex w-full items-start gap-3 py-3 text-left transition hover:bg-carbon-soft/40"
                    aria-expanded={isOpen}
                  >
                    <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${VERDICT_DOT[fx.verdict]}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{f.label}</span>
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider ${VERDICT_STAMP_CLASS[fx.verdict]}`}
                        >
                          {VERDICT_STAMP[fx.verdict]}
                        </span>
                      </div>
                      <p className="mt-0.5 text-sm text-zinc-400">{fx.headline}</p>
                    </div>
                    <span
                      className={`mt-0.5 shrink-0 select-none text-lg leading-none text-zinc-600 transition-transform ${
                        isOpen ? 'rotate-90' : ''
                      }`}
                    >
                      ›
                    </span>
                  </button>
                  {isOpen && (
                    <div className="pb-6 pt-1">
                      {evidence(f.key)}
                      {f.key === 'where' && fx.caveat && (
                        <p className="mt-3 text-[11px] text-zinc-600">{fx.caveat}</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Auto takeaway */}
          <p className="mt-4 rounded border border-carbon-line bg-carbon-soft/50 px-3 py-2.5 text-sm text-zinc-200">
            <span className="font-semibold text-white">→ </span>
            {takeaway(race)}
          </p>
        </Panel>
      )}

      {!race && !raceError && pick && (
        <p className="py-8 text-center text-sm text-zinc-500">Loading race data…</p>
      )}

      {/* Why this matters beyond F1 */}
      <Panel title="Why this matters beyond F1" subtitle="The transferable skill">
        <p className="py-1 text-sm text-zinc-400">
          Decomposing an outcome (a race win) into its true causes and refusing to credit a cause
          that's within noise is outcome attribution under uncertainty — the same shape as
          root-cause analysis, A/B-test readouts, and anomaly detection.
        </p>
      </Panel>

      {/* Explorer */}
      {index && (
        <Panel title="Explore other races" subtitle="Pick any race and read its scorecard">
          <div className="space-y-3 py-1">
            <RacePicker index={index} value={pick} onPick={setPick} />
            {race && (
              <p className="text-xs text-zinc-500">
                {race.meta.winner.name} beat {race.meta.p2.name} · {race.meta.eventName} ·{' '}
                {margin(race.meta.marginS)} margin
              </p>
            )}
          </div>
        </Panel>
      )}

      {/* Method & trust */}
      <Panel title="Method & trust" subtitle="Why you can believe the split">
        <div className="space-y-3 py-1 text-sm text-zinc-400">
          <p>
            Laps are filtered to <strong className="text-zinc-200">clean laps</strong> (green flag,
            not lap 1, not in/out laps). Where-on-track uses{' '}
            <strong className="text-zinc-200">like-compound</strong> comparisons only. Fuel load is{' '}
            <strong className="text-zinc-200">not corrected</strong> — named explicitly so you know.
            The where-on-track factor runs{' '}
            <strong className="text-zinc-200">5,000-sample bootstrap CIs</strong> on comparable
            mid-stint laps to separate real sector edges from noise. The tyre, pace, and start
            verdicts are threshold-based point estimates — not CI-gated.
          </p>
          <p className="text-xs text-zinc-500">
            Full write-up: <StudyLinks className="text-zinc-300" />
          </p>
        </div>
      </Panel>
    </div>
  )
}
