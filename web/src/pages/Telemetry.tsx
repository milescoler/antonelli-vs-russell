import { useEffect, useState } from 'react'
import { Panel } from '../components/ui'
import { DriverSessionPicker } from '../components/DriverSessionPicker'
import { SpeedTrackMap } from '../components/SpeedTrackMap'
import { useSeason, useTelemetry } from '../lib/data'
import type { TelemetryDriver } from '../types'

export function Telemetry() {
  const { data: season, error: seasonError } = useSeason()

  // Slug defaults to the last session once season data arrives
  const [sessionSlug, setSessionSlug] = useState<string>('')
  const [driverCode, setDriverCode] = useState<string>('')

  // Set default session to last in list
  useEffect(() => {
    if (season && !sessionSlug) {
      const sessions = season.meta.sessions
      if (sessions.length > 0) {
        setSessionSlug(sessions[sessions.length - 1].slug)
      }
    }
  }, [season, sessionSlug])

  const { data: telemetry, error: telemetryError } = useTelemetry(sessionSlug || undefined)

  // When telemetry loads or session changes, default to first driver
  useEffect(() => {
    if (telemetry) {
      if (telemetry.drivers.length > 0) {
        setDriverCode(telemetry.drivers[0].code)
      } else {
        setDriverCode('')
      }
    }
  }, [telemetry])

  // Reset driver when session changes
  const handleSession = (slug: string) => {
    setSessionSlug(slug)
    setDriverCode('')
  }

  const sessions = season?.meta.sessions ?? []
  const drivers: { code: string; name: string }[] =
    telemetry?.drivers.map((d) => ({ code: d.code, name: d.name })) ?? []

  const selectedDriver: TelemetryDriver | undefined =
    telemetry?.drivers.find((d) => d.code === driverCode)

  return (
    <div className="space-y-9">
      {/* Hero header */}
      <section className="f1-bar">
        <div className="f1-kicker text-[11px] text-f1-red">Telemetry</div>
        <h1 className="text-3xl font-black uppercase italic tracking-tight text-white sm:text-4xl">
          Fastest Qualifying Lap
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Speed, braking, and throttle traces mapped onto the circuit. Select a session and driver
          to explore the lap.
        </p>
      </section>

      {/* Season error */}
      {seasonError && (
        <p className="rounded-lg border border-f1-red/40 bg-f1-red/10 p-4 text-sm text-red-300">
          Could not load sessions: {seasonError}
        </p>
      )}

      {/* Picker */}
      {sessions.length > 0 && (
        <DriverSessionPicker
          sessions={sessions}
          drivers={drivers}
          sessionSlug={sessionSlug}
          driverCode={driverCode}
          onSession={handleSession}
          onDriver={setDriverCode}
        />
      )}

      {/* Track map panel */}
      <Panel
        title="Speed Map"
        subtitle={
          selectedDriver
            ? `${selectedDriver.name} · ${telemetry?.session.eventName ?? ''}`
            : 'Select a driver to view the lap'
        }
      >
        {/* Telemetry loading */}
        {sessionSlug && !telemetry && !telemetryError && (
          <p className="py-8 text-center text-sm text-zinc-500">Loading telemetry…</p>
        )}

        {/* Telemetry error */}
        {telemetryError && (
          <p className="py-8 text-center text-sm text-red-400">
            Could not load telemetry: {telemetryError}
          </p>
        )}

        {/* No session yet */}
        {!sessionSlug && (
          <p className="py-8 text-center text-sm text-zinc-500">Select a session above.</p>
        )}

        {/* No driver in telemetry */}
        {telemetry && !selectedDriver && !telemetryError && (
          <p className="py-8 text-center text-sm text-zinc-500">
            No telemetry available for this driver.
          </p>
        )}

        {/* Map */}
        {selectedDriver && <SpeedTrackMap driver={selectedDriver} />}
      </Panel>
    </div>
  )
}
