import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTeam } from '../lib/data'
import { A_COLOR, B_COLOR, signed, takeaway } from '../lib/format'
import { Badge, LegendDot, Panel } from '../components/ui'
import { shortEvent } from '../components/charts/common'
import { LapDeltaChart } from '../components/charts/LapDeltaChart'
import { SegmentSplitChart } from '../components/charts/SegmentSplitChart'
import { GapTraceChart } from '../components/charts/GapTraceChart'
import { StintPaceChart } from '../components/charts/StintPaceChart'
import { TireDegChart } from '../components/charts/TireDegChart'
import { CornerBucketsTable } from '../components/CornerBucketsTable'
import { StartConversion } from '../components/StartConversion'
import { RoundPicker } from '../components/RoundPicker'
import { QualCaveats, RaceCaveats } from '../components/CaveatBadges'

export function TeamPage() {
  const { slug } = useParams()
  const { data: team, error } = useTeam(slug)

  const rounds = useMemo(() => {
    if (!team) return []
    const m = new Map<number, string>()
    team.qualifying.byRound.forEach((r) => m.set(r.round, r.eventName))
    team.race.byRound.forEach((r) => m.set(r.round, r.eventName))
    return [...m.entries()].sort((a, b) => a[0] - b[0]).map(([round, eventName]) => ({ round, eventName }))
  }, [team])

  const [sel, setSel] = useState<number | null>(null)
  const selected = sel ?? (rounds.length ? rounds[rounds.length - 1].round : null)

  if (error)
    return (
      <div className="space-y-4">
        <Link to="/" className="text-sm text-sky-400">← all teams</Link>
        <p className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-300">
          Couldn't load this team: {error}
        </p>
      </div>
    )
  if (!team) return <p className="text-sm text-zinc-500">Loading…</p>

  const { a, b } = team.pair
  const qr = team.qualifying.byRound.find((r) => r.round === selected)
  const rr = team.race.byRound.find((r) => r.round === selected)
  const yoy = team.qualifying.yoy
  const hasSwap = [...team.qualifying.byRound, ...team.race.byRound].some(
    (r) => !r.isCanonicalPair,
  )

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-sky-400 hover:text-sky-300">← all teams</Link>

      <header className="space-y-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white">{team.displayName}</h1>
          {hasSwap && <Badge tone="amber">lineup change this season</Badge>}
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
          <Driver color={A_COLOR} label="A" code={a.code} number={a.number} name={a.name} />
          <span className="text-zinc-600">vs</span>
          <Driver color={B_COLOR} label="B" code={b.code} number={b.number} name={b.name} />
        </div>
        <p className="max-w-2xl text-sm text-zinc-300">{takeaway(team)}</p>
      </header>

      <Panel
        title="Qualifying — head-to-head by round"
        subtitle="Fastest-lap delta. Positive = A faster (same car, so this is mostly the driver)."
        right={
          <div className="hidden gap-3 sm:flex">
            <LegendDot color={A_COLOR} label={`${a.code} faster`} />
            <LegendDot color={B_COLOR} label={`${b.code} faster`} />
          </div>
        }
      >
        <LapDeltaChart rounds={team.qualifying.byRound} aCode={a.code} bCode={b.code} />
      </Panel>

      {yoy && (
        <Panel
          title="Year over year vs 2025"
          subtitle={`Same pairing, same ${yoy.nRoundsCompared} circuits, one season apart.`}
        >
          <div className="flex flex-wrap gap-6">
            <Stat label="2025 mean" value={`${signed(yoy.meanLapDelta_s_2025)} s`} />
            <Stat label="2026 mean" value={`${signed(yoy.meanLapDelta_s_2026)} s`} />
            <Stat
              label="Year-over-year shift"
              value={`${signed(yoy.deltaOfDeltas_s)} s`}
              big
              hint={`${a.code} relative to ${b.code}`}
            />
          </div>
        </Panel>
      )}

      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Drill into a round
        </span>
        {selected !== null && (
          <RoundPicker rounds={rounds} value={selected} onChange={setSel} />
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title={qr ? `Where the time goes — ${shortEvent(qr.eventName)}` : 'Qualifying detail'}
          subtitle="Mean per-segment delta by corner type. Positive = A faster."
          right={qr ? <QualCaveats {...qr.caveats} /> : undefined}
        >
          {qr ? <SegmentSplitChart segments={qr.segmentCategoryMeans} /> : <NoRound />}
        </Panel>

        <Panel title="Corner signatures" subtitle="How A drives the corner vs B, by corner speed.">
          {qr ? <CornerBucketsTable buckets={qr.cornerSignatureBuckets} aCode={a.code} /> : <NoRound />}
        </Panel>
      </div>

      {rr && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Race — {shortEvent(rr.eventName)}
            </h2>
            <RaceCaveats {...rr.caveats} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Start conversion" subtitle="Grid → lap 1 → finish (P2 = field reference).">
              <StartConversion start={rr.start} />
            </Panel>
            <Panel title="Race pace by stint" subtitle="Median clean-lap time, like-compound.">
              <StintPaceChart stints={rr.stintPace} aCode={a.code} bCode={b.code} />
            </Panel>
            <Panel title="Tire degradation" subtitle="Per-stint slope (s/lap). Stints with 5+ clean laps only.">
              <TireDegChart deg={rr.tireDeg} aCode={a.code} />
            </Panel>
            <Panel title={`${a.code} gap trace`} subtitle="Per lap. Negative = leading / ahead of P2.">
              <GapTraceChart gap={rr.gapTrace} />
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}

function Driver({
  color,
  label,
  code,
  number,
  name,
}: {
  color: string
  label: string
  code: string
  number: number
  name: string
}) {
  return (
    <span className="inline-flex items-baseline gap-2">
      <span className="text-lg font-bold" style={{ color }}>
        {code}
      </span>
      <span className="text-xs text-zinc-500">
        #{number} · {name} · <span className="uppercase">{label}</span>
      </span>
    </span>
  )
}

function Stat({
  label,
  value,
  hint,
  big,
}: {
  label: string
  value: string
  hint?: string
  big?: boolean
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={(big ? 'text-2xl' : 'text-lg') + ' font-bold tabular-nums text-zinc-100'}>
        {value}
      </div>
      {hint && <div className="text-[11px] text-zinc-500">{hint}</div>}
    </div>
  )
}

function NoRound() {
  return <p className="py-10 text-center text-sm text-zinc-600">No qualifying data for this round.</p>
}
