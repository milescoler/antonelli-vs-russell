import { useEffect, useRef, useState } from 'react'
import { useIndex, useStandings } from '../lib/data'
import { OverviewGrid } from '../components/OverviewGrid'
import { TeamDashboard } from '../components/TeamDashboard'
import { StandingsTable } from '../components/StandingsTable'
import { PredictionCard } from '../components/PredictionCard'

export function Dashboard() {
  const { data, error } = useIndex()
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
          Driver vs Car
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Who's winning, how they're doing it, and who's in form for the next round — with the car
          divided out by comparing teammates.
        </p>
      </section>

      {/* WHO'S DOING THE BEST: next-race form + championship */}
      <section className="grid gap-4 lg:grid-cols-2">
        {st ? (
          <PredictionCard
            nextRace={st.nextRace}
            drivers={st.prediction.drivers}
            method={st.prediction.method}
          />
        ) : (
          <LoadingCard label="prediction" />
        )}
        <div className="rounded-lg border border-carbon-line bg-carbon-card p-4 sm:p-5">
          <div className="f1-bar mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wide text-white">Championship</h2>
            <p className="text-xs text-zinc-500">Real points — who's actually doing the best.</p>
          </div>
          {st ? <StandingsTable rows={st.standings} limit={8} /> : <p className="text-sm text-zinc-500">Loading…</p>}
        </div>
      </section>

      {/* HOW: the teammate battles */}
      <section>
        <div className="f1-bar mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wide text-white">
            How — teammate battles
          </h2>
          <p className="text-xs text-zinc-500">
            Each team's season qualifying edge (positive = lower-car-number driver faster), biggest
            gap first. Click a team for the full breakdown.
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

function LoadingCard({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-carbon-line bg-carbon-card p-6 text-sm text-zinc-500">
      Loading {label}…
    </div>
  )
}
