export function MethodPage() {
  return (
    <article className="max-w-2xl space-y-5">
      <div className="f1-bar">
        <h1 className="text-2xl font-black uppercase italic tracking-tight text-white">
          Method & honesty
        </h1>
      </div>

      <p className="text-sm leading-relaxed text-zinc-400">
        Every result tangles driver and car together. The one fair test is{' '}
        <strong className="text-zinc-200">teammates</strong> — same car, same season — so whatever
        separates them is mostly the driver. The whole tool is built on that, and is careful to claim
        only what the data supports.
      </p>

      <Section title="The headline — margin over teammate">
        For each qualifying session we take each driver's fastest lap as a percentage off the
        session's fastest (track-normalized), then the gap to their teammate. Averaged over the
        season that's the rating. Because it's ~7 rounds, we report a small-sample (Student-t)
        interval and a sign test — so most duels honestly read <em>too close to call</em>. That's the
        point: we'd rather say "not separable yet" than fake precision.
      </Section>

      <Section title="Why there's no simple 1–22 skill ladder">
        To rank drivers <em>across</em> teams you need someone who drove for both, to link the teams
        onto one scale. In 2025→2026 almost nobody moved — so Mercedes, Ferrari, McLaren and the rest
        are <strong className="text-zinc-200">isolated islands</strong>. The data literally cannot say
        whether, say, Antonelli outdrives Hamilton in equal cars. The "equal-car" view therefore only
        compares drivers <em>within</em> a linked island (the Red Bull/Racing Bulls family, joined by
        drivers who crossed between them) and shows everything with bootstrap intervals. The
        Sauber→Audi rebrand is continuity, not a transfer, so it doesn't bridge teams.
      </Section>

      <Section title="The race & track detail">
        Behind each teammate battle: FastF1 race laps (clean green-flag laps only) for start
        conversion, stint pace and tire degradation; and the qualifying telemetry drawn as a track
        map colored by who's faster where. Pace and degradation aren't fuel-corrected — named, not
        modelled away.
      </Section>

      <Section title="What this is not">
        Not a win-probability model, not betting odds, not an absolute skill ranking. Championship
        points are shown only as real-world context. Findings are directional; uncertainty is on
        every chart.
      </Section>

      <p className="text-xs text-zinc-600">Data via FastF1. Built by Cole Richards.</p>
    </article>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-bold uppercase tracking-wide text-f1-red">{title}</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{children}</p>
    </section>
  )
}
