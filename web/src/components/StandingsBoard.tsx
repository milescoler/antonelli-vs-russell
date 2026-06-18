import { Panel } from './ui'
import type { StandingDriver, Constructor } from '../types'

// Inline SVG sparkline: lower finish position = taller bar (P1 = max height)
function FormSparkline({ finishes }: { finishes: (number | null)[] }) {
  const W = 60
  const H = 18
  const barW = 4
  const gap = 2
  const maxPos = 20 // scale: P1–P20

  return (
    <svg width={W} height={H} className="shrink-0 opacity-70" aria-hidden="true">
      {finishes.slice(-10).map((pos, i) => {
        if (pos === null) return null
        const barH = Math.max(2, Math.round(((maxPos - pos + 1) / maxPos) * H))
        const x = i * (barW + gap)
        const y = H - barH
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barW}
            height={barH}
            rx={1}
            className="fill-zinc-500"
          />
        )
      })}
    </svg>
  )
}

function DriverRow({ driver, rank }: { driver: StandingDriver; rank: number }) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-carbon-line last:border-0">
      {/* rank */}
      <span className="w-5 shrink-0 text-right text-xs font-semibold tabular-nums text-zinc-500">
        {rank}
      </span>

      {/* team-color bar */}
      <span
        className="h-8 w-1 shrink-0 rounded-full"
        style={{ background: driver.teamColor }}
      />

      {/* code + name + meta */}
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-bold uppercase tracking-wide text-white tabular-nums">
            {driver.code}
          </span>
          <span className="truncate text-xs text-zinc-400">{driver.name}</span>
        </div>
        <div className="mt-0.5 text-[10px] text-zinc-500 tabular-nums">
          {driver.wins}W
          {' · '}
          {driver.podiums} podiums
          {driver.avgFinish !== null && ` · avg P${driver.avgFinish.toFixed(1)}`}
        </div>
      </div>

      {/* sparkline */}
      <FormSparkline finishes={driver.finishes} />

      {/* points */}
      <span className="w-12 shrink-0 text-right text-base font-black tabular-nums text-white">
        {driver.points ?? '—'}
      </span>
    </div>
  )
}

function ConstructorRow({ ctor, rank }: { ctor: Constructor; rank: number }) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-carbon-line last:border-0">
      <span className="w-5 shrink-0 text-right text-xs font-semibold tabular-nums text-zinc-500">
        {rank}
      </span>

      <span
        className="h-8 w-1 shrink-0 rounded-full"
        style={{ background: ctor.teamColor }}
      />

      <div className="min-w-0 flex-1">
        <span className="text-sm font-bold uppercase tracking-wide text-white">
          {ctor.team}
        </span>
        <div className="mt-0.5 text-[10px] text-zinc-500 tabular-nums">
          {ctor.wins}W
        </div>
      </div>

      <span className="w-12 shrink-0 text-right text-base font-black tabular-nums text-white">
        {ctor.points ?? '—'}
      </span>
    </div>
  )
}

export function StandingsBoard({
  drivers,
  constructors,
}: {
  drivers: StandingDriver[]
  constructors: Constructor[]
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Panel
        title="Drivers"
        subtitle={`${drivers.length} drivers · points standings`}
        right={
          <span className="f1-kicker text-[10px] text-zinc-500 uppercase tracking-widest">
            PTS
          </span>
        }
      >
        <div>
          {drivers.map((d, i) => (
            <DriverRow key={d.code} driver={d} rank={i + 1} />
          ))}
        </div>
      </Panel>

      <Panel
        title="Constructors"
        subtitle={`${constructors.length} teams · points standings`}
        right={
          <span className="f1-kicker text-[10px] text-zinc-500 uppercase tracking-widest">
            PTS
          </span>
        }
      >
        <div>
          {constructors.map((c, i) => (
            <ConstructorRow key={c.team} ctor={c} rank={i + 1} />
          ))}
        </div>
      </Panel>
    </div>
  )
}
