interface Props {
  sessions: { slug: string; eventName: string }[]
  drivers: { code: string; name: string }[]
  sessionSlug: string
  driverCode: string
  onSession: (slug: string) => void
  onDriver: (code: string) => void
}

const SELECT_CLS =
  'rounded-sm border border-carbon-line bg-carbon-card px-3 py-1.5 text-xs font-semibold ' +
  'uppercase tracking-wide text-zinc-200 focus:outline-none focus:border-zinc-500 ' +
  'cursor-pointer hover:border-zinc-500 transition'

export function DriverSessionPicker({
  sessions,
  drivers,
  sessionSlug,
  driverCode,
  onSession,
  onDriver,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Session picker */}
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Session
        </label>
        <select
          value={sessionSlug}
          onChange={(e) => onSession(e.target.value)}
          className={SELECT_CLS}
        >
          {sessions.map((s) => (
            <option key={s.slug} value={s.slug}>
              {s.eventName}
            </option>
          ))}
        </select>
      </div>

      {/* Driver picker */}
      <div className="flex flex-col gap-0.5">
        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          Driver
        </label>
        <select
          value={driverCode}
          onChange={(e) => onDriver(e.target.value)}
          className={SELECT_CLS}
          disabled={drivers.length === 0}
        >
          {drivers.length === 0 && (
            <option value="">—</option>
          )}
          {drivers.map((d) => (
            <option key={d.code} value={d.code}>
              {d.code} — {d.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
