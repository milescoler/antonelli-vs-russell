import {
  Bar, BarChart, Cell, ErrorBar, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DecompMatchup } from '../../types'
import { axisTick, tooltipStyle, zero } from '../charts/common'

const REAL = '#22c55e'   // CI excludes zero
const NOISE = '#52525b'  // CI straddles zero

export function SectorVerdict({ matchup }: { matchup: DecompMatchup }) {
  // Recharts ErrorBar wants asymmetric offsets [down, up] from the bar value.
  const data = matchup.sectors.map((s) => {
    const mean = s.deltaMean ?? 0
    const lo = s.ciLow ?? mean
    const hi = s.ciHigh ?? mean
    return { ...s, mean, err: [mean - lo, hi - mean] as [number, number] }
  })
  const nReal = matchup.sectors.filter((s) => s.significant).length

  return (
    <div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
            <XAxis dataKey="i" tick={axisTick} stroke={zero}
              label={{ value: 'micro-sector', position: 'insideBottom', offset: -8, fill: '#71717a', fontSize: 10 }} />
            <YAxis tick={axisTick} width={48}
              tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}s`} stroke={zero} />
            <ReferenceLine y={0} stroke={zero} />
            <Tooltip
              {...tooltipStyle}
              formatter={(v: number, _n, p) => {
                const s = p.payload
                const tag = s.significant ? 'real' : 'noise'
                return [`${v > 0 ? '+' : ''}${v.toFixed(3)}s  [${(s.ciLow ?? 0).toFixed(3)}, ${(s.ciHigh ?? 0).toFixed(3)}]  ${tag}`, `sector ${s.i}`]
              }}
              labelFormatter={() => ''}
            />
            <Bar dataKey="mean" isAnimationActive={false}>
              {data.map((s) => <Cell key={s.i} fill={s.significant ? REAL : NOISE} />)}
              <ErrorBar dataKey="err" width={3} strokeWidth={1} stroke="#a1a1aa" direction="y" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-center text-[11px] text-zinc-500">
        <span style={{ color: REAL }}>■</span> {nReal} real (CI excludes 0) ·{' '}
        <span style={{ color: NOISE }}>■</span> {matchup.sectors.length - nReal} within noise.
        Bars are mean Δ per sector; whiskers are the 95% bootstrap CI.
      </p>
    </div>
  )
}
