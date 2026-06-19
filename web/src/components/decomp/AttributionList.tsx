import type { DecompMatchup } from '../../types'

export function AttributionList({ matchup }: { matchup: DecompMatchup }) {
  const { attribution, callouts, sectors } = matchup
  const trap = callouts.noiseTrap == null
    ? null
    : sectors.find((s) => s.i === callouts.noiseTrap) ?? null

  return (
    <div className="space-y-3">
      {attribution.length === 0 ? (
        <p className="text-sm text-zinc-400">
          No micro-sector advantage was statistically distinguishable from zero at this sample
          size — the lap-time gap is within lap-to-lap noise.
        </p>
      ) : (
        attribution.map((row) => (
          <div key={row.sector} className="rounded-md border border-carbon-line bg-carbon-soft p-3">
            <div className="text-[11px] font-bold uppercase tracking-widest text-zinc-500">
              Sector {row.sector} · faster: {row.driverFaster}
            </div>
            <p className="mt-1 text-sm text-zinc-300">{row.narrative}</p>
          </div>
        ))
      )}

      {trap && (
        <div className="rounded-md border border-f1-red/40 bg-f1-red/10 p-3">
          <div className="text-[11px] font-bold uppercase tracking-widest text-f1-red">
            The trap
          </div>
          <p className="mt-1 text-sm text-zinc-300">
            Sector {trap.i} shows a {(trap.deltaMean ?? 0) > 0 ? '+' : ''}
            {(trap.deltaMean ?? 0).toFixed(3)}s "edge", but its 95% CI [
            {(trap.ciLow ?? 0).toFixed(3)}, {(trap.ciHigh ?? 0).toFixed(3)}] straddles zero — not a
            real advantage, just a good/bad lap. Calling that out is the discipline.
          </p>
        </div>
      )}
    </div>
  )
}
