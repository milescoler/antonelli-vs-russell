import { Panel, StudyLinks } from '../components/ui'

export function About() {
  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red uppercase tracking-widest">
          Pitwall
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          About
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          What Pitwall tracks, the question behind it, and how it works.
        </p>
      </section>

      <Panel
        title="The Question Behind the Dashboard"
        subtitle="Separating the driver from the car."
      >
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            This dashboard is the descriptive front end of a study with one goal: separate{' '}
            <strong className="text-zinc-200">driver skill (signal)</strong> from{' '}
            <strong className="text-zinc-200">car performance (noise)</strong>. A fast car flatters
            a driver everywhere, so the study controls for the car three ways — same car (Antonelli
            vs his teammate Russell), same race, and same track across seasons — and is{' '}
            <strong className="text-zinc-200">disciplined about uncertainty</strong>, so a noisy
            swing is never reported as a real edge.
          </p>
          <p>
            The clearest example of why that discipline matters: an early version of the qualifying
            analysis found large per-corner gaps at Japan that turned out to be a{' '}
            <strong className="text-zinc-200">frozen speed sensor</strong> — a freeze-detection
            filter collapsed them to ~0. Catching that, and knowing when you{' '}
            <em className="not-italic text-zinc-200">haven't</em> found real signal, is the whole
            skill.
          </p>
          <p className="text-xs text-zinc-500">
            Read the full analysis: <StudyLinks className="text-zinc-300" />
          </p>
        </div>
      </Panel>

      <Panel title="What Pitwall Is" subtitle="A 2026 F1 season performance dashboard.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            Pitwall is a performance dashboard for the{' '}
            <strong className="text-zinc-200">2026 Formula 1 season</strong>. It covers
            championship standings for drivers and constructors, qualifying and race pace
            rankings, tyre strategy data, and single-lap telemetry — all in one place.
          </p>
          <p>
            The goal is straightforward: present what the timing sheets actually say, without
            model assumptions layered on top.
          </p>
        </div>
      </Panel>

      <Panel title="Data" subtitle="Where the numbers come from and what they mean.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            All session data — qualifying times, race laps, points, and tyre information — is
            sourced from <strong className="text-zinc-200">FastF1</strong>, the open-source
            Python library for Formula 1 telemetry and timing. Data is updated after each
            completed round.
          </p>
          <p>
            Pace figures are expressed as a percentage off the session's fastest time, which
            normalises for track and conditions. With approximately{' '}
            <strong className="text-zinc-200">7 rounds</strong> completed so far, sample sizes
            are small — trends are directional, not definitive.
          </p>
        </div>
      </Panel>

      <Panel title="What Pitwall Is Not" subtitle="Scope and affiliation.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            Pitwall is deliberately descriptive: it shows what the timing sheets say — not
            win-probability estimates, betting odds, or predictions. The inference — dividing the
            car out from the driver, with the noise checks that go with it — lives in the case
            study and notebooks, kept separate on purpose so the raw numbers and the analysis never
            get confused.
          </p>
          <p>
            Pitwall is not affiliated with Formula 1, Formula One Management, the FIA, or any
            constructor or driver. All data is for informational purposes only.
          </p>
        </div>
      </Panel>

      <div className="border-t border-zinc-800 pt-6 text-xs text-zinc-600">
        <StudyLinks className="text-zinc-500" />
        <span className="mt-2 block">Built by Cole Richards. Data via FastF1.</span>
      </div>
    </div>
  )
}
