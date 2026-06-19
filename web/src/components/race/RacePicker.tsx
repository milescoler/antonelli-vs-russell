import type { RaceDecompIndex } from '../../types'

const SELECT_CLS =
  'rounded-sm border border-carbon-line bg-carbon-card px-3 py-1.5 text-xs font-semibold ' +
  'uppercase tracking-wide text-zinc-200 focus:outline-none focus:border-zinc-500 ' +
  'cursor-pointer hover:border-zinc-500 transition'

export function RacePicker({
  index,
  value,
  onPick,
}: {
  index: RaceDecompIndex
  value: string
  onPick: (slug: string) => void
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Race</label>
        <select
          className={SELECT_CLS}
          value={value}
          onChange={(e) => onPick(e.target.value)}
        >
          {index.races.map((r) => (
            <option key={r.slug} value={r.slug}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
