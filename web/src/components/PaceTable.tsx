import type { PaceRow } from '../types'

// Fastest driver (rank 1, smallest mean) gets full bar width.
// All others scale relative to the fastest's mean.
function paceBarWidth(row: PaceRow, maxMean: number, minMean: number): number {
  if (row.mean === null) return 0
  if (maxMean === minMean) return 100
  // invert: fastest (smallest mean) = 100%, slowest (largest mean) = ~0%
  return Math.max(4, ((maxMean - row.mean) / (maxMean - minMean)) * 100)
}

function formatMean(mean: number | null, rank: number, unit: string): string {
  if (mean === null) return '—'
  if (rank === 1) return '0.00%'
  return `+${mean.toFixed(2)}%`
}

export function PaceTable({ rows, unit }: { rows: PaceRow[]; unit: string }) {
  const validMeans = rows.map((r) => r.mean).filter((m): m is number => m !== null)
  const minMean = validMeans.length ? Math.min(...validMeans) : 0
  const maxMean = validMeans.length ? Math.max(...validMeans) : 1

  const roundCount = rows[0]?.byRound.length ?? 0

  return (
    <div>
      <div className="mb-3 text-[11px] text-zinc-500 tabular-nums">
        {unit} · n = {roundCount} rounds
      </div>
      <div className="space-y-1.5">
        {rows.map((row) => {
          const barPct = paceBarWidth(row, maxMean, minMean)
          return (
            <div key={row.code} className="flex items-center gap-3">
              {/* rank */}
              <span className="w-5 shrink-0 text-right text-xs font-semibold tabular-nums text-zinc-500">
                {row.rank}
              </span>

              {/* team-color bar accent */}
              <span
                className="h-6 w-1 shrink-0 rounded-full"
                style={{ background: row.teamColor }}
              />

              {/* code + name */}
              <div className="w-28 shrink-0">
                <span className="text-xs font-bold uppercase tracking-wide text-white tabular-nums">
                  {row.code}
                </span>
                <span className="ml-1.5 text-[11px] text-zinc-500 truncate">{row.name}</span>
              </div>

              {/* horizontal pace bar */}
              <div className="flex-1 min-w-0">
                <div className="relative h-4 rounded-sm bg-carbon-soft overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 rounded-sm transition-all"
                    style={{
                      width: `${barPct}%`,
                      background: row.teamColor,
                      opacity: 0.75,
                    }}
                  />
                </div>
              </div>

              {/* mean value */}
              <span className="w-16 shrink-0 text-right text-xs font-semibold tabular-nums text-zinc-300">
                {formatMean(row.mean, row.rank, unit)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
