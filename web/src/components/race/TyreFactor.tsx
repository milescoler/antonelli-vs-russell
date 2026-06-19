import type { TyreFactor as TyreFactorType, TyreStint } from '../../types'
import { Panel, Badge } from '../ui'

const COMPOUND_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  SOFT:         { bg: 'bg-red-600',    text: 'text-white', label: 'S' },
  MEDIUM:       { bg: 'bg-yellow-400', text: 'text-black', label: 'M' },
  HARD:         { bg: 'bg-zinc-300',   text: 'text-black', label: 'H' },
  INTERMEDIATE: { bg: 'bg-green-500',  text: 'text-white', label: 'I' },
  WET:          { bg: 'bg-blue-500',   text: 'text-white', label: 'W' },
}

function CompoundChip({ compound }: { compound: string }) {
  const style = COMPOUND_COLORS[compound.toUpperCase()] ?? {
    bg: 'bg-zinc-600',
    text: 'text-white',
    label: compound.charAt(0).toUpperCase(),
  }
  return (
    <span
      className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-black ${style.bg} ${style.text}`}
      title={compound}
    >
      {style.label}
    </span>
  )
}

const VERDICT_TONE = {
  real:        'sky',
  noise:       'zinc',
  inherited:   'amber',
  insufficient: 'zinc',
} as const

function DriverStintRow({ code, stints }: { code: string; stints: TyreStint[] }) {
  return (
    <div className="py-2 border-b border-carbon-line/50 last:border-0">
      <div className="flex items-start gap-2">
        <span className="w-8 shrink-0 text-[11px] font-bold uppercase tracking-wide text-white tabular-nums pt-0.5">
          {code}
        </span>
        <div className="flex flex-col gap-1.5 flex-1">
          {stints.map((stint) => (
            <div key={stint.stint} className="flex items-center gap-2 flex-wrap">
              <CompoundChip compound={stint.compound} />
              <span className="text-[11px] text-zinc-400">Stint {stint.stint}</span>
              {stint.degSlope_s_per_lap !== null ? (
                <span className="text-[11px] tabular-nums text-zinc-300 font-semibold">
                  {stint.degSlope_s_per_lap > 0 ? '+' : ''}
                  {stint.degSlope_s_per_lap.toFixed(3)} s/lap
                </span>
              ) : (
                <span className="text-[11px] text-zinc-600">
                  — <span className="text-zinc-700">(&#60;5 laps)</span>
                </span>
              )}
              {stint.nClean < 5 && stint.degSlope_s_per_lap === null && null}
              <span className="text-[10px] text-zinc-600">{stint.nClean} laps</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function TyreFactor({ factor }: { factor: TyreFactorType }) {
  // Group stints by driver code, preserving insertion order (winner first)
  const driverOrder: string[] = []
  const byDriver: Record<string, TyreStint[]> = {}
  for (const stint of factor.stints) {
    if (!byDriver[stint.code]) {
      driverOrder.push(stint.code)
      byDriver[stint.code] = []
    }
    byDriver[stint.code].push(stint)
  }

  const tone = VERDICT_TONE[factor.verdict]

  return (
    <Panel
      title="Tyre Factor"
      right={<Badge tone={tone}>{factor.verdict}</Badge>}
    >
      <p className="mb-3 text-sm text-zinc-300">{factor.headline}</p>
      <div className="rounded border border-carbon-line bg-carbon-soft/30 px-3 py-1">
        {driverOrder.map((code) => (
          <DriverStintRow key={code} code={code} stints={byDriver[code]} />
        ))}
      </div>
      {factor.caveat && (
        <p className="mt-2 text-[11px] text-zinc-600">{factor.caveat}</p>
      )}
    </Panel>
  )
}
