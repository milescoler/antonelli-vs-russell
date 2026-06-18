import { useState } from 'react'
import { Panel } from '../components/ui'
import { useSeason, useTelemetry } from '../lib/data'

export function Telemetry() {
  const { data: season } = useSeason()
  const [slug, setSlug] = useState<string | undefined>(undefined)
  const { data: telemetry, error } = useTelemetry(slug)

  return (
    <div className="space-y-9">
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red">Speed Explorer</div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          Telemetry
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Per-session speed, brake, and throttle traces across the track map.
        </p>
      </section>

      <Panel title="Session Select" subtitle="Choose a session to explore telemetry.">
        {season ? (
          <div className="flex flex-wrap gap-2 py-2">
            {season.meta.sessions.map((s) => (
              <button
                key={s.slug}
                onClick={() => setSlug(s.slug)}
                className={
                  'rounded-sm border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition ' +
                  (slug === s.slug
                    ? 'border-f1-red bg-f1-red/20 text-white'
                    : 'border-carbon-line text-zinc-400 hover:border-zinc-500 hover:text-zinc-200')
                }
              >
                {s.eventName}
              </button>
            ))}
          </div>
        ) : (
          <p className="py-4 text-sm text-zinc-500">Loading sessions…</p>
        )}
      </Panel>

      <Panel title="Telemetry Viewer" subtitle="Interactive speed map coming soon.">
        {error && (
          <p className="py-4 text-sm text-red-400">Could not load telemetry: {error}</p>
        )}
        {!slug && <p className="py-6 text-sm text-zinc-500">Select a session above.</p>}
        {slug && telemetry && (
          <p className="py-6 text-sm text-zinc-400">
            {telemetry.session.eventName} · {telemetry.drivers.length} drivers loaded
          </p>
        )}
        {slug && !telemetry && !error && (
          <p className="py-6 text-sm text-zinc-500">Loading telemetry…</p>
        )}
      </Panel>
    </div>
  )
}
