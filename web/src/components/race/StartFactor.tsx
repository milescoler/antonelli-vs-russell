import type { StartFactor as StartFactorType, StartRow } from '../../types'
import { Panel, Badge } from '../ui'

const VERDICT_TONE = {
  real:        'sky',
  noise:       'zinc',
  inherited:   'amber',
  insufficient: 'zinc',
} as const

function PositionCell({ pos }: { pos: number | null }) {
  if (pos === null) return <span className="text-zinc-600">—</span>
  return <span className="tabular-nums">{pos}</span>
}

function GainedCell({ gained }: { gained: number | null }) {
  if (gained === null) return <span className="text-zinc-600">—</span>
  if (gained > 0)
    return (
      <span className="tabular-nums font-semibold text-green-400">
        +{gained}
      </span>
    )
  if (gained < 0)
    return (
      <span className="tabular-nums font-semibold text-red-400">
        {gained}
      </span>
    )
  return <span className="tabular-nums text-zinc-500">0</span>
}

const ROLE_LABEL: Record<string, string> = {
  WIN: 'WIN',
  P2: 'P2',
  POLE: 'POLE',
  // legacy (pre-fix) shapes — kept for safety
  A: 'WIN',
  B: 'POLE',
}

function StartRowItem({ row }: { row: StartRow }) {
  const roleLabel = ROLE_LABEL[row.role] ?? row.role
  return (
    <tr className="border-b border-carbon-line/50 last:border-0">
      {/* role */}
      <td className="py-2 pr-3 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
        {roleLabel}
      </td>
      {/* code */}
      <td className="py-2 pr-3">
        <span className="text-xs font-bold uppercase tracking-wide text-white">
          {row.code}
        </span>
        {row.dnf && (
          <span className="ml-1.5 text-[10px] font-semibold uppercase text-red-400">DNF</span>
        )}
      </td>
      {/* grid */}
      <td className="py-2 pr-3 text-xs text-zinc-400">
        <PositionCell pos={row.grid} />
      </td>
      {/* arrow */}
      <td className="py-2 pr-1 text-zinc-600 text-xs">→</td>
      {/* lap 1 */}
      <td className="py-2 pr-3 text-xs text-zinc-400">
        <PositionCell pos={row.lap1Pos} />
      </td>
      {/* arrow */}
      <td className="py-2 pr-1 text-zinc-600 text-xs">→</td>
      {/* finish */}
      <td className="py-2 pr-3 text-xs text-zinc-400">
        {row.dnf ? (
          <span className="text-red-500">{row.status}</span>
        ) : (
          <PositionCell pos={row.finish} />
        )}
      </td>
      {/* positions gained */}
      <td className="py-2 text-xs">
        <GainedCell gained={row.positionsGained} />
      </td>
    </tr>
  )
}

export function StartFactor({ factor }: { factor: StartFactorType }) {
  const tone = VERDICT_TONE[factor.verdict]

  return (
    <Panel
      title="Start Factor"
      right={<Badge tone={tone}>{factor.verdict}</Badge>}
    >
      <p className="mb-3 text-sm text-zinc-300">{factor.headline}</p>
      <div className="overflow-x-auto rounded border border-carbon-line bg-carbon-soft/30 px-3 py-1">
        <table className="w-full min-w-[340px] border-collapse">
          <thead>
            <tr className="border-b border-carbon-line">
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Role
              </th>
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Driver
              </th>
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Grid
              </th>
              <th className="pb-1.5" />
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Lap 1
              </th>
              <th className="pb-1.5" />
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Finish
              </th>
              <th className="pb-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                +/−
              </th>
            </tr>
          </thead>
          <tbody>
            {factor.rows.map((row, i) => (
              <StartRowItem key={`${row.code}-${i}`} row={row} />
            ))}
          </tbody>
        </table>
      </div>
      {factor.caveat && (
        <p className="mt-2 text-[11px] text-zinc-600">{factor.caveat}</p>
      )}
    </Panel>
  )
}
