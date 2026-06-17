import type { TeamSummary } from '../types'
import { A_COLOR, B_COLOR } from '../lib/format'
import { Sparkline } from './Sparkline'
import { Badge } from './ui'

function headline(t: TeamSummary): { code: string; text: string } | null {
  const m = t.summary.meanLapDelta_s
  if (m === null) return null
  const { a, b } = t.canonicalPair
  const leader = m >= 0 ? a.code : b.code
  return { code: leader, text: `+${Math.abs(m).toFixed(3)}` }
}

/** Bigger teammate gap = higher up. Teams with no data sort last. */
const gapSize = (t: TeamSummary) =>
  t.summary.meanLapDelta_s === null ? -1 : Math.abs(t.summary.meanLapDelta_s)

export function OverviewGrid({
  teams,
  selected,
  onSelect,
}: {
  teams: TeamSummary[]
  selected: string | null
  onSelect: (slug: string) => void
}) {
  const ordered = [...teams].sort((x, y) => gapSize(y) - gapSize(x))
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {ordered.map((t) => {
        const { a, b } = t.canonicalPair
        const h = headline(t)
        const active = t.slug === selected
        return (
          <button
            key={t.slug}
            onClick={() => onSelect(t.slug)}
            className={
              'flex flex-col gap-2 rounded-xl border p-3 text-left transition ' +
              (active
                ? 'border-sky-500 bg-sky-500/10 ring-1 ring-sky-500/40'
                : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-600 hover:bg-zinc-900')
            }
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold tracking-tight text-zinc-100">
                {t.displayName}
              </span>
              {t.yoyAvailable && <Badge tone="sky">YoY</Badge>}
            </div>
            <div className="flex items-baseline gap-1.5 text-base font-bold">
              <span style={{ color: A_COLOR }}>{a.code}</span>
              <span className="text-[10px] font-normal text-zinc-600">vs</span>
              <span style={{ color: B_COLOR }}>{b.code}</span>
            </div>
            <div className="flex items-center justify-between">
              {h ? (
                <span className="text-xs text-zinc-400">
                  <span className="font-semibold text-zinc-200">{h.code}</span> {h.text}s
                </span>
              ) : (
                <span className="text-xs text-zinc-600">—</span>
              )}
              <Sparkline values={t.summary.lapDeltaByRound} width={84} height={26} />
            </div>
          </button>
        )
      })}
    </div>
  )
}
