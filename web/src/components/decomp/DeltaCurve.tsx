import {
  Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { DecompMatchup } from '../../types'
import { axisTick, tooltipStyle, zero } from '../charts/common'

export function DeltaCurve({ matchup }: { matchup: DecompMatchup }) {
  const { deltaCurve, corners, meta } = matchup
  const a = meta.driverA.code
  const b = meta.driverB.code

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={deltaCurve} margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
          <XAxis
            dataKey="d" type="number" domain={['dataMin', 'dataMax']}
            tick={axisTick} tickFormatter={(v) => `${Math.round(v)}m`}
            stroke={zero}
          />
          <YAxis
            tick={axisTick} width={48}
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}s`}
            stroke={zero}
          />
          <ReferenceLine y={0} stroke={zero} />
          {corners.map((c) =>
            c.d == null ? null : (
              <ReferenceLine key={c.label} x={c.d} stroke="#3f3f46" strokeDasharray="2 3"
                label={{ value: c.label, position: 'top', fill: '#71717a', fontSize: 9 }} />
            ),
          )}
          <Tooltip
            {...tooltipStyle}
            formatter={(v: number) => [`${v > 0 ? '+' : ''}${v.toFixed(3)}s`, `${a} − ${b}`]}
            labelFormatter={(d: number) => `${Math.round(d)} m`}
          />
          <Line type="monotone" dataKey="delta" stroke="#e10600" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-center text-[11px] text-zinc-500">
        Cumulative time gap (<span className="text-zinc-300">{a} − {b}</span>) along the lap.
        Rising = {b} pulling ahead; the finish-line value is the official gap.
      </p>
    </div>
  )
}
