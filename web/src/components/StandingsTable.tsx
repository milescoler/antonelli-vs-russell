import type { StandingRow } from '../types'

const accent = (c: string | null) => c || '#3f3f46'

export function StandingsTable({ rows, limit }: { rows: StandingRow[]; limit?: number }) {
  const shown = limit ? rows.slice(0, limit) : rows
  return (
    <div className="space-y-1">
      {shown.map((d, i) => (
        <div
          key={d.code}
          className="flex items-center gap-3 rounded-sm bg-carbon-soft/60 px-2 py-1.5"
        >
          <span className="w-5 text-right text-sm font-bold tabular-nums text-zinc-500">
            {i + 1}
          </span>
          <span className="h-7 w-1 rounded-sm" style={{ background: accent(d.teamColor) }} />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold text-white">{d.code}</span>
              <span className="truncate text-xs text-zinc-500">{d.team}</span>
            </div>
            <div className="text-[11px] text-zinc-600">
              {d.wins}W · {d.podiums} podiums · avg P{d.avgFinish ?? '—'}
            </div>
          </div>
          <span className="text-base font-black tabular-nums text-white">
            {d.points ?? 0}
            <span className="ml-1 text-[10px] font-semibold uppercase text-zinc-500">pts</span>
          </span>
        </div>
      ))}
    </div>
  )
}
