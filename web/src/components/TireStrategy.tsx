import type { TireDriver, Stint } from '../types'
import { mean } from '../lib/format'

const COMPOUND_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  SOFT:         { bg: 'bg-red-600',    text: 'text-white',     label: 'S' },
  MEDIUM:       { bg: 'bg-yellow-400', text: 'text-black',     label: 'M' },
  HARD:         { bg: 'bg-zinc-300',   text: 'text-black',     label: 'H' },
  INTERMEDIATE: { bg: 'bg-green-500',  text: 'text-white',     label: 'I' },
  WET:          { bg: 'bg-blue-500',   text: 'text-white',     label: 'W' },
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

function avgDegSlope(stints: Stint[]): number | null {
  return mean(stints.map((s) => s.degSlope))
}

function uniqueCompounds(stints: Stint[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const s of stints) {
    const c = s.compound.toUpperCase()
    if (!seen.has(c)) {
      seen.add(c)
      result.push(c)
    }
  }
  return result
}

export function TireStrategy({ drivers }: { drivers: TireDriver[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-carbon-line">
            <th className="pb-2 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-500 w-8">
              #
            </th>
            <th className="pb-2 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-500 w-4" />
            <th className="pb-2 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Driver
            </th>
            <th className="pb-2 text-left text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Compounds
            </th>
            <th className="pb-2 text-right text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Avg deg (s/lap)
            </th>
            <th className="pb-2 text-right text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Stints
            </th>
          </tr>
        </thead>
        <tbody>
          {drivers.map((driver, i) => {
            const deg = avgDegSlope(driver.stints)
            const compounds = uniqueCompounds(driver.stints)
            return (
              <tr
                key={driver.code}
                className="border-b border-carbon-line/50 last:border-0 hover:bg-carbon-soft/40 transition-colors"
              >
                {/* rank */}
                <td className="py-2.5 text-xs tabular-nums text-zinc-500">{i + 1}</td>

                {/* team-color bar */}
                <td className="py-2.5">
                  <span
                    className="inline-block h-5 w-1 rounded-full"
                    style={{ background: driver.teamColor }}
                  />
                </td>

                {/* driver */}
                <td className="py-2.5">
                  <span className="font-bold uppercase tracking-wide text-white tabular-nums text-xs">
                    {driver.code}
                  </span>
                  <span className="ml-1.5 text-[11px] text-zinc-400">{driver.name}</span>
                </td>

                {/* compound chips */}
                <td className="py-2.5">
                  <div className="flex items-center gap-1 flex-wrap">
                    {compounds.map((c) => (
                      <CompoundChip key={c} compound={c} />
                    ))}
                  </div>
                </td>

                {/* avg degradation slope */}
                <td className="py-2.5 text-right text-xs tabular-nums text-zinc-300 font-semibold">
                  {deg !== null ? deg.toFixed(3) : '—'}
                </td>

                {/* stint count */}
                <td className="py-2.5 text-right text-xs tabular-nums text-zinc-500">
                  {driver.stints.length}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
