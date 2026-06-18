import { Panel } from '../components/ui'
import { useSeason } from '../lib/data'

export function Dashboard() {
  const { data, error } = useSeason()

  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red">
          {data ? `${data.season} season` : 'Loading…'}
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          Pitwall Dashboard
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Season standings, pace rankings, and tire data across the 2026 grid.
        </p>
      </section>

      {error && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load season data: {error}
        </p>
      )}

      <Panel title="Season Overview" subtitle="Full standings and pace data coming soon.">
        {data ? (
          <p className="py-6 text-sm text-zinc-400">
            {data.meta.drivers.length} drivers · {data.meta.rounds.length} rounds loaded
          </p>
        ) : (
          <p className="py-6 text-sm text-zinc-500">Loading season data…</p>
        )}
      </Panel>
    </div>
  )
}
