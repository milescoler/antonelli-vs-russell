import { Panel } from '../components/ui'

export function About() {
  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red">About Pitwall</div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          About
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          What Pitwall tracks and how it works.
        </p>
      </section>

      <Panel title="Data Sources" subtitle="Where the numbers come from.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            All session data is sourced from{' '}
            <strong className="text-zinc-200">FastF1</strong>, the open-source Python library
            for Formula 1 telemetry and timing.
          </p>
          <p>
            Standings, qualifying deltas, race pace, and tire degradation are computed from
            official timing data and updated after each round.
          </p>
        </div>
      </Panel>

      <Panel title="Method" subtitle="How pace and tire metrics are calculated.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            Race pace uses median lap times from clean green-flag stints only. Tire degradation
            is the slope of lap time versus stint age. Values are not fuel-corrected — this is
            noted, not modelled away.
          </p>
          <p>
            Qualifying pace is each driver's normalized session delta, averaged across rounds
            with sufficient data.
          </p>
        </div>
      </Panel>

      <Panel title="Limitations" subtitle="What this tool does not claim.">
        <p className="py-2 text-sm text-zinc-400">
          Pitwall is not a win-probability model, not betting odds, and not an official Formula 1
          product. It is not affiliated with Formula 1 or the FIA. All data is for informational
          purposes only.
        </p>
      </Panel>
    </div>
  )
}
