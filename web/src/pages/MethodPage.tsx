export function MethodPage() {
  return (
    <article className="prose-invert max-w-2xl space-y-5 text-zinc-300">
      <h1 className="text-2xl font-bold text-white">Method & limitations</h1>

      <p>
        The throughline of this tool is simple: <strong>a fast car flatters a driver everywhere</strong>,
        so the signal worth trusting is whatever survives once the car is divided out. The cleanest
        way to divide it out is to compare <strong>teammates</strong> — same car, same season.
      </p>

      <Section title="Qualifying (Chapter 1)">
        FastF1 telemetry for each 2026 qualifying session. We take each driver's fastest valid lap,
        resample it onto a uniform 5&nbsp;m distance grid, and read per-segment times from the
        timing channel. The headline is the lap-time delta (positive = driver A faster, where A is
        the lower car number). Segment-category means and corner signatures (apex speed, brake and
        throttle points) show <em>where</em> the time comes from. A sliding-window check flags and
        excludes segments where a frozen speed sensor corrupts the telemetry.
      </Section>

      <Section title="Race (Chapter 2)">
        FastF1 race sessions, laps only. Metrics build on a shared clean-lap filter (green-flag
        racing laps, not lap 1, no in/out/pit laps): start conversion (grid → lap 1 → finish),
        per-stint median pace read like-compound only, tire-degradation slope per stint, and a
        per-lap gap to the rival. Pace and degradation are <strong>not</strong> fuel-corrected —
        named, not modelled away.
      </Section>

      <Section title="Year-over-year">
        Shown only where the same pairing drove the same team last season. Tracks are matched across
        years by circuit, so the comparison is genuinely same-car, same-place, one year apart.
      </Section>

      <Section title="What this is not">
        Not a driver-vs-the-field model — comparing a driver to the whole grid loses the car control
        that makes this honest. Small samples (a partial season, thin race data) make findings
        directional, not conclusive. DNFs, traffic, tire age and setup divergence are surfaced as
        caveats rather than corrected away.
      </Section>

      <p className="text-sm text-zinc-500">
        Data via FastF1. Sign convention shown on each chart. Built by Cole Richards.
      </p>
    </article>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-sky-400">{title}</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{children}</p>
    </section>
  )
}
