import { shortEvent } from './charts/common'

export function RoundPicker({
  rounds,
  value,
  onChange,
}: {
  rounds: { round: number; eventName: string }[]
  value: number
  onChange: (round: number) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {rounds.map((r) => {
        const active = r.round === value
        return (
          <button
            key={r.round}
            onClick={() => onChange(r.round)}
            className={
              'rounded-md border px-2.5 py-1 text-xs transition ' +
              (active
                ? 'border-sky-500 bg-sky-500/15 text-sky-200'
                : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200')
            }
          >
            {shortEvent(r.eventName)}
          </button>
        )
      })}
    </div>
  )
}
