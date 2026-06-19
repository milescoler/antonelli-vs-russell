import { Panel, StudyLinks } from '../components/ui'

export function About() {
  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red uppercase tracking-widest">
          What Won the Race?
        </div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          About
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          The question, the method, and what the tool actually does.
        </p>
      </section>

      <Panel
        title="The Question"
        subtitle="Outcome attribution under uncertainty."
      >
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            After every race, one driver wins by some margin. But{' '}
            <strong className="text-zinc-200">why?</strong> This tool decomposes the winning
            margin — winner vs P2 finisher — into four causes and issues a verdict on each:
          </p>
          <ul className="ml-4 list-disc space-y-1">
            <li>
              <strong className="text-zinc-200">Where on track / which laps</strong> — which
              corners or stint windows actually built the gap
            </li>
            <li>
              <strong className="text-zinc-200">Tyre strategy &amp; degradation</strong> — did
              one driver gain from undercut, overcut, or slower tyre wear?
            </li>
            <li>
              <strong className="text-zinc-200">Race pace</strong> — on comparable laps
              (same compound, similar tyre age), who was actually faster?
            </li>
            <li>
              <strong className="text-zinc-200">Start &amp; track position</strong> — did the
              result turn on a grid slot, a lap-1 move, or traffic that never cleared?
            </li>
          </ul>
          <p>
            Each factor receives a verdict:{' '}
            <strong className="text-zinc-200">real</strong> (the data support it),{' '}
            <strong className="text-zinc-200">noise</strong> (bootstrap CIs span zero),{' '}
            <strong className="text-zinc-200">inherited</strong> (the gap came from a rival
            retirement), or{' '}
            <strong className="text-zinc-200">insufficient data</strong> (too few comparable
            laps to say).
          </p>
        </div>
      </Panel>

      <Panel title="The Method" subtitle="Comparable laps, bootstrap CIs, honest exclusion.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            Race pace is read only across{' '}
            <strong className="text-zinc-200">matching compounds at similar tyre age</strong>{' '}
            — apples-to-apples stint windows. The where-on-track factor uses a{' '}
            <strong className="text-zinc-200">5,000-sample bootstrap</strong> to put confidence
            intervals on each track sector; a sector only earns a "real" verdict when the CI
            excludes zero. Stints under five clean laps report no verdict rather than a noisy
            number.
          </p>
          <p>
            Fuel load is <strong className="text-zinc-200">not corrected</strong> — named, not
            modelled. Safety-car and VSC laps are excluded. Claims are{' '}
            <strong className="text-zinc-200">"in this dataset"</strong>, not real-world F1
            history.
          </p>
        </div>
      </Panel>

      <Panel title="What the Results Actually Show" subtitle="Three examples of honest findings.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            <strong className="text-zinc-200">Monaco</strong> — pole-to-flag, multiple factors
            ruled real: pace, tyre management, and where on track all pointed the same way. The
            start factor was noise (he simply led pole-to-flag). The clearest "everything
            aligned" race.
          </p>
          <p>
            <strong className="text-zinc-200">Canada</strong> — Antonelli's win was{' '}
            <strong className="text-zinc-200">inherited</strong>: polesitter Russell led until
            his DNF on lap 2. The tool says so explicitly rather than crediting a pass that
            didn't happen.
          </p>
          <p>
            <strong className="text-zinc-200">Japan</strong> — Antonelli won from pole despite
            dropping five places on lap 1. The tool's honest read: the win was driven by{' '}
            <strong className="text-zinc-200">race pace</strong> (real, ~0.28 s/lap faster);
            the where-on-track factor is{' '}
            <strong className="text-zinc-200">insufficient</strong> — too few comparable laps
            to decompose the recovery lap by lap.
          </p>
          <p>
            <strong className="text-zinc-200">Australia</strong> — the winner was actually
            slower on race pace; track position, not outright speed, decided it. The tool calls
            this out rather than attributing the win to pace it can't find.
          </p>
        </div>
      </Panel>

      <Panel title="Measurement Discipline" subtitle="Why the honest exclusions matter.">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            The clearest proof the method is honest: an early telemetry pass at Japan found
            large per-sector deltas that turned out to be a{' '}
            <strong className="text-zinc-200">frozen speed sensor</strong> — a freeze-detection
            filter collapsed them to ~0. Catching that, and knowing when you{' '}
            <em className="not-italic text-zinc-200">haven't</em> found real signal, is the whole
            skill.
          </p>
          <p>
            The same discipline runs through every verdict here: small samples are flagged,
            noisy factors are called noise, and inherited wins are called inherited. If the data
            can't support a verdict, the tool says so.
          </p>
          <p className="text-xs text-zinc-500">
            Full method write-up: <StudyLinks className="text-zinc-300" />
          </p>
        </div>
      </Panel>

      <Panel title="Scope &amp; Affiliation" subtitle="">
        <div className="space-y-3 py-2 text-sm text-zinc-400">
          <p>
            This tool is descriptive and analytical — it does not produce win-probability
            estimates, betting odds, or predictions. It is not affiliated with Formula 1,
            Formula One Management, the FIA, or any constructor or driver. All data is for
            informational purposes only.
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
