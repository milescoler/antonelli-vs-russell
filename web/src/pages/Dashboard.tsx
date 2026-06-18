import { useEffect, useRef, useState } from 'react'
import { useIndex, useRatings, useStandings } from '../lib/data'
import { OverviewGrid } from '../components/OverviewGrid'
import { TeamDashboard } from '../components/TeamDashboard'
import { StandingsTable } from '../components/StandingsTable'
import { DriverRanking } from '../components/DriverRanking'
import { EqualCarGrid } from '../components/EqualCarGrid'
import { Panel } from '../components/ui'

export function Dashboard() {
  const { data, error } = useIndex()
  const { data: ratings } = useRatings()
  const { data: st } = useStandings()
  const [selected, setSelected] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (data && !selected) {
      const has = data.teams.some((t) => t.slug === 'mercedes')
      setSelected(has ? 'mercedes' : (data.teams[0]?.slug ?? null))
    }
  }, [data, selected])

  const onSelect = (slug: string) => {
    setSelected(slug)
    detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red">
          2026 season · {data ? `${data.rounds.length} rounds in` : 'loading'}
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          Who's actually driving best?
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          The car flatters everyone. The one fair test is teammates — same machinery, so the gap is
          mostly the driver. This ranks every driver by how decisively they beat their teammate, and
          is honest about where the data can (and can't) go further.
        </p>
      </section>

      {/* HEADLINE: car-adjusted driver ranking */}
      <Panel
        title="Driver Power Ranking — margin over teammate"
        subtitle={ratings?.headline.note ?? 'Same car, so it’s mostly the driver. % of lap time; + = faster.'}
      >
        {ratings ? (
          <DriverRanking ranking={ratings.headline.ranking} />
        ) : (
          <p className="py-8 text-center text-sm text-zinc-500">Loading ranking…</p>
        )}
      </Panel>

      {/* equal-car (what's actually comparable) + championship context */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Equal-car — what the data can compare"
          subtitle={ratings?.equalCar.note ?? ''}
        >
          {ratings ? <EqualCarGrid ratings={ratings} /> : <p className="text-sm text-zinc-500">Loading…</p>}
        </Panel>
        <Panel title="Championship" subtitle="Real points — who's actually scoring (context).">
          {st ? <StandingsTable rows={st.standings} limit={8} /> : <p className="text-sm text-zinc-500">Loading…</p>}
        </Panel>
      </section>

      {/* HOW: the teammate battles */}
      <section>
        <div className="f1-bar mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wide text-white">
            How — go inside any teammate battle
          </h2>
          <p className="text-xs text-zinc-500">
            Biggest qualifying gap first. Click a team for the track map, segment split, and race
            breakdown behind its number.
          </p>
        </div>
        {error && (
          <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
            Couldn't load the grid: {error}
          </p>
        )}
        {!data && !error && <p className="text-sm text-zinc-500">Loading grid…</p>}
        {data && <OverviewGrid teams={data.teams} selected={selected} onSelect={onSelect} />}
      </section>

      <div ref={detailRef} className="scroll-mt-20 border-t border-carbon-line pt-6">
        <TeamDashboard slug={selected} />
      </div>
    </div>
  )
}
