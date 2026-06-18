import type { MarginRow } from '../types'

const FASTER = '#38bdf8' // sky — beats teammate
const SLOWER = '#fb923c' // orange — beaten by teammate

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
const pos = (v: number, max: number) => 50 + clamp((v / max) * 50, -50, 50)

function VerdictChip({ verdict }: { verdict: MarginRow['verdict'] }) {
  if (verdict === 'reliably_faster')
    return <span className="rounded-sm bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-sky-300">clear</span>
  if (verdict === 'reliably_slower')
    return <span className="rounded-sm bg-orange-500/20 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-orange-300">clear</span>
  return <span className="rounded-sm bg-carbon-soft px-1.5 py-0.5 text-[10px] font-semibold uppercase text-zinc-500">too close</span>
}

export function DriverRanking({ ranking }: { ranking: MarginRow[] }) {
  const max = Math.max(
    0.1,
    ...ranking.flatMap((r) => [r.marginPct, r.ciLow, r.ciHigh].map((v) => Math.abs(v ?? 0))),
  )
  return (
    <div className="space-y-1">
      {ranking.map((r, i) => {
        const m = r.marginPct ?? 0
        const c = m >= 0 ? FASTER : SLOWER
        const barLeft = m >= 0 ? 50 : pos(m, max)
        const barW = Math.abs(pos(m, max) - 50)
        const hasCI = r.ciLow !== null && r.ciHigh !== null
        return (
          <div key={r.code} className="flex items-center gap-2 rounded-sm bg-carbon-soft/40 px-2 py-1.5">
            <span className="w-5 text-right text-xs font-bold tabular-nums text-zinc-600">{i + 1}</span>
            <span className="h-6 w-1 rounded-sm" style={{ background: r.teamColor || '#3f3f46' }} />
            <div className="w-24 shrink-0">
              <div className="text-sm font-bold text-white">{r.code}</div>
              <div className="text-[10px] text-zinc-500">vs {r.vs} · n={r.n}</div>
            </div>
            {/* diverging bar + CI whisker, centered at 0 */}
            <div className="relative h-6 flex-1">
              <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-700" />
              <div
                className="absolute top-1/2 h-3 -translate-y-1/2 rounded-sm"
                style={{ left: `${barLeft}%`, width: `${barW}%`, background: c, opacity: 0.85 }}
              />
              {hasCI && (
                <div
                  className="absolute top-1/2 h-px -translate-y-1/2 bg-zinc-400"
                  style={{
                    left: `${pos(r.ciLow as number, max)}%`,
                    width: `${pos(r.ciHigh as number, max) - pos(r.ciLow as number, max)}%`,
                  }}
                />
              )}
            </div>
            <span className="w-14 text-right text-xs font-bold tabular-nums text-white">
              {m >= 0 ? '+' : ''}{m.toFixed(2)}%
            </span>
            <span className="w-16 text-right"><VerdictChip verdict={r.verdict} /></span>
          </div>
        )
      })}
    </div>
  )
}
