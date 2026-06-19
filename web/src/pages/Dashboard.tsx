import { Panel, StudyLinks } from '../components/ui'
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

      {/* Thesis strip — names the method and points to the full analysis */}
      <section className="rounded-lg border border-carbon-line bg-carbon-soft p-4 sm:p-5">
        <div className="f1-bar">
          <div className="f1-kicker text-[11px] uppercase tracking-widest text-f1-red">
            The question
          </div>
          <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-zinc-300">
            How much of Antonelli's 5-from-7 start is the <em className="not-italic text-white">driver</em>,
            and how much is the <em className="not-italic text-white">Mercedes</em>? A fast car flatters a
            driver everywhere, so the only trustworthy signal is whatever survives once you divide the car
            out. The study does that three ways — same car (teammate), same race, same track across years —
            and is ruthless about labeling noise as noise instead of dressing it up as a finding. This
            dashboard is the descriptive layer it runs on.
          </p>
          <p className="mt-3 text-xs text-zinc-500">
            Read the full analysis: <StudyLinks className="text-zinc-300" />
          </p>
        </div>
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
