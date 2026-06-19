import { useMemo } from 'react'
import type { DecompIndex } from '../../types'

const SELECT_CLS =
  'rounded-sm border border-carbon-line bg-carbon-card px-3 py-1.5 text-xs font-semibold ' +
  'uppercase tracking-wide text-zinc-200 focus:outline-none focus:border-zinc-500 ' +
  'cursor-pointer hover:border-zinc-500 transition'

export function MatchupPicker({
  index, value, onPick,
}: { index: DecompIndex; value: string; onPick: (key: string) => void }) {
  const current = index.matchups.find((m) => m.key === value)
  const race = current?.race ?? index.races[0]?.slug

  const teamsForRace = useMemo(
    () => index.matchups.filter((m) => m.race === race),
    [index.matchups, race],
  )

  const pickRace = (slug: string) => {
    const first = index.matchups.find((m) => m.race === slug && m.valid)
      ?? index.matchups.find((m) => m.race === slug)
    if (first) onPick(first.key)
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Race</label>
        <select className={SELECT_CLS} value={race} onChange={(e) => pickRace(e.target.value)}>
          {index.races.map((r) => (
            <option key={r.slug} value={r.slug}>{r.name}</option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Teammates</label>
        <select className={SELECT_CLS} value={value} onChange={(e) => onPick(e.target.value)}>
          {teamsForRace.map((m) => (
            <option key={m.key} value={m.key} disabled={!m.valid}>
              {m.team}: {m.a} v {m.b}{m.valid ? '' : ` — ${m.reason ?? 'excluded'}`}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
