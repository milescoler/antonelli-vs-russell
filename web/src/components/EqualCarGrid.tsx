import type { DriverRatings, EqualCarIsland } from '../types'

const FASTER = '#38bdf8'
const SLOWER = '#fb923c'
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

function IslandGrid({ island }: { island: EqualCarIsland }) {
  const max = Math.max(
    0.05,
    ...island.drivers.flatMap((d) => [d.theta, d.ciLow, d.ciHigh].map((v) => Math.abs(v ?? 0))),
  )
  const pos = (v: number) => 50 + clamp((v / max) * 50, -50, 50)
  const teams = [...new Set(island.drivers.map((d) => d.team).filter(Boolean))]
  return (
    <div className="rounded-md border border-carbon-line bg-carbon-soft/40 p-3">
      <div className="mb-2 text-xs text-zinc-400">
        <span className="font-semibold text-zinc-200">{teams.join(' + ')}</span>{' '}
        <span className="text-zinc-600">· equal-car order (faster ← → slower)</span>
      </div>
      <div className="space-y-1">
        {island.drivers.map((d) => {
          const t = d.theta ?? 0
          const c = t <= 0 ? FASTER : SLOWER
          const left = t <= 0 ? pos(t) : 50
          const w = Math.abs(pos(t) - 50)
          const hasCI = d.ciLow !== null && d.ciHigh !== null
          return (
            <div key={d.code} className="flex items-center gap-2">
              <span className="w-4 text-right text-[11px] font-bold text-zinc-600">{d.rank}</span>
              <span className="h-4 w-1 rounded-sm" style={{ background: d.teamColor || '#3f3f46' }} />
              <span className="w-10 text-sm font-bold text-white">{d.code}</span>
              <div className="relative h-4 flex-1">
                <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-700" />
                <div
                  className="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-sm"
                  style={{ left: `${left}%`, width: `${w}%`, background: c, opacity: 0.85 }}
                />
                {hasCI && (
                  <div
                    className="absolute top-1/2 h-px -translate-y-1/2 bg-zinc-400"
                    style={{
                      left: `${pos(d.ciLow as number)}%`,
                      width: `${pos(d.ciHigh as number) - pos(d.ciLow as number)}%`,
                    }}
                  />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function EqualCarGrid({ ratings }: { ratings: DriverRatings }) {
  const multi = ratings.equalCar.islands.filter((i) => i.multiTeam)
  const isolatedTeams = ratings.islands.components
    .filter((c) => !c.multiTeam)
    .map((c) => [...new Set(c.teamSeasons.map((t) => t.team))].join('/'))

  return (
    <div className="space-y-3">
      {multi.length === 0 ? (
        <p className="text-sm text-zinc-500">No teams are linked by a shared driver — no cross-team comparison is possible.</p>
      ) : (
        multi.map((isl) => <IslandGrid key={isl.component} island={isl} />)
      )}
      <p className="text-[11px] leading-relaxed text-zinc-600">
        The only teams the data can compare are those a driver crossed between (above). The other{' '}
        {isolatedTeams.length} teams never swapped a driver, so they're isolated islands — there's no
        honest way to rank drivers across them. Bars are centered on each island's average driver;
        whiskers are bootstrap 90% intervals.
      </p>
    </div>
  )
}
