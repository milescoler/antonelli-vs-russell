import { Panel } from '../components/ui'
import { StandingsBoard } from '../components/StandingsBoard'
import { PaceTable } from '../components/PaceTable'
import { TireStrategy } from '../components/TireStrategy'
import { useSeason } from '../lib/data'

export function Dashboard() {
  const { data, error } = useSeason()

  return (
    <div className="space-y-9">
      {/* Hero header */}
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red uppercase tracking-widest">
          Pitwall
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          {data ? `${data.season} Season` : 'Season Dashboard'}
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          The descriptive layer behind a driver-vs-car study: standings, qualifying and race
          pace, and tyre strategy across the {data ? data.season : '2026'} grid — the raw timing
          this project pulls signal from.
        </p>
      </section>

      {/* Error state */}
      {error && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load season data: {error}
        </p>
      )}

      {/* Loading state */}
      {!data && !error && (
        <Panel title="Loading" subtitle="Fetching season data…">
          <p className="py-6 text-sm text-zinc-500">Loading season data…</p>
        </Panel>
      )}

      {/* Main content */}
      {data && (
        <>
          {/* Standings */}
          <StandingsBoard
            drivers={data.standings.drivers}
            constructors={data.standings.constructors}
          />

          {/* Qualifying pace */}
          <Panel
            title="Qualifying Pace"
            subtitle={`Ranked by average gap to pole · ${data.qualifying.length} drivers`}
          >
            <PaceTable rows={data.qualifying} unit="% off pole" />
          </Panel>

          {/* Race pace */}
          <Panel
            title="Race Pace"
            subtitle={`Ranked by average gap to race fastest · ${data.racePace.length} drivers`}
          >
            <PaceTable rows={data.racePace} unit="% off race-fastest" />
          </Panel>

          {/* Tyre strategy */}
          <Panel
            title="Tyre Strategy"
            subtitle={`Compounds used and degradation across ${data.meta.rounds.length} rounds`}
          >
            <TireStrategy drivers={data.tire} />
          </Panel>
        </>
      )}
    </div>
  )
}
