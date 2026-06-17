import { Link } from 'react-router-dom'
import { useIndex } from '../lib/data'
import { TeamCard } from '../components/TeamCard'

export function Landing() {
  const { data, error } = useIndex()

  return (
    <div className="space-y-10">
      <section className="pt-4">
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          How much is the <span className="text-sky-400">driver</span>, and how much is the{' '}
          <span className="text-zinc-400">car</span>?
        </h1>
        <p className="mt-3 max-w-2xl text-zinc-400">
          Every result tangles the two together. The one fair test is teammates: same car, same
          season — so whatever separates them is mostly the driver. Pick a team to see the split,
          from qualifying pace down to how each one converts it on Sunday.
        </p>
      </section>

      <section className="rounded-2xl border border-sky-900/40 bg-gradient-to-br from-sky-950/40 to-zinc-900/20 p-5">
        <div className="text-xs font-semibold uppercase tracking-wide text-sky-400">
          Featured case study
        </div>
        <h2 className="mt-1 text-xl font-bold text-white">
          Separating Antonelli from the Mercedes
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          The rookie phenom won 5 of his first 7 — until Barcelona broke the run. The deepest
          version of this analysis lives on the Mercedes page: qualifying segment-by-segment,
          year-over-year vs his 2025 self, and how the wins were actually won.
        </p>
        <Link
          to="/team/mercedes"
          className="mt-3 inline-block rounded-md border border-sky-700 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-200 transition hover:bg-sky-500/20"
        >
          Open the Mercedes breakdown →
        </Link>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          All 2026 teams
        </h2>
        {error && (
          <p className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-300">
            Couldn't load data: {error}
          </p>
        )}
        {!data && !error && <p className="text-sm text-zinc-500">Loading teams…</p>}
        {data && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {data.teams.map((t) => (
              <TeamCard key={t.slug} team={t} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
