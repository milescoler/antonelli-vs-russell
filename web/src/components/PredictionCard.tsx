import { useState } from 'react'
import { Info } from 'lucide-react'
import type { NextRace, PredictionDriver } from '../types'

const accent = (c: string | null) => c || '#e10600'

export function PredictionCard({
  nextRace,
  drivers,
  method,
}: {
  nextRace: NextRace | null
  drivers: PredictionDriver[]
  method: string
}) {
  const [showMethod, setShowMethod] = useState(false)
  const maxOdds = Math.max(...drivers.map((d) => d.winOdds ?? 0), 0.0001)

  return (
    <section className="overflow-hidden rounded-lg border border-carbon-line bg-carbon-card">
      <div className="flex items-center justify-between border-b border-carbon-line bg-f1-red/10 px-4 py-3">
        <div className="f1-bar">
          <div className="f1-kicker text-[11px] text-f1-red">Next race · form-based odds</div>
          <div className="text-base font-bold text-white">
            {nextRace ? nextRace.eventName : 'Season complete'}
          </div>
          {nextRace && (
            <div className="text-xs text-zinc-500">
              {nextRace.country} · {nextRace.eventDate}
            </div>
          )}
        </div>
        <button
          onClick={() => setShowMethod((s) => !s)}
          className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-zinc-500 hover:text-zinc-300"
        >
          <Info size={13} /> how?
        </button>
      </div>

      {showMethod && (
        <p className="border-b border-carbon-line bg-carbon-soft px-4 py-2.5 text-xs leading-relaxed text-zinc-400">
          {method}
        </p>
      )}

      <div className="space-y-2 p-4">
        {drivers.map((d, i) => {
          const pct = (d.winOdds ?? 0) * 100
          const w = ((d.winOdds ?? 0) / maxOdds) * 100
          return (
            <div key={d.code} className="flex items-center gap-3">
              <span className="w-8 text-sm font-bold text-white">{d.code}</span>
              <div className="relative h-6 flex-1 overflow-hidden rounded-sm bg-carbon-soft">
                <div
                  className="h-full rounded-sm"
                  style={{ width: `${w}%`, background: accent(d.teamColor), opacity: i === 0 ? 1 : 0.7 }}
                />
                <span className="absolute inset-y-0 right-2 flex items-center text-xs font-bold tabular-nums text-white">
                  {pct.toFixed(0)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
      <p className="px-4 pb-3 text-[11px] text-zinc-600">
        A transparent recent-form heuristic — not official betting odds.
      </p>
    </section>
  )
}
