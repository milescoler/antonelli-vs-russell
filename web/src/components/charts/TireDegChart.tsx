import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TireDeg } from '../../types'
import { A_COLOR, B_COLOR } from '../../lib/format'
import { axisTick, Empty, grid, tooltipStyle, zero } from './common'

export function TireDegChart({ deg, aCode }: { deg: TireDeg[]; aCode: string }) {
  const data = deg
    .filter((d) => d.degSlope_s_per_lap !== null && d.stint !== null)
    .map((d) => ({
      name: `${d.code} S${d.stint}`,
      slope: d.degSlope_s_per_lap as number,
      isA: d.code === aCode,
      compound: d.compound,
    }))

  if (data.length === 0)
    return <Empty note="No stints long enough to fit degradation (need 5+ clean laps)." />

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -6, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} />
        <XAxis dataKey="name" tick={axisTick} interval={0} angle={-20} textAnchor="end" height={48} />
        <YAxis tick={axisTick} width={56} tickFormatter={(v) => `${v}`} />
        <ReferenceLine y={0} stroke={zero} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: '#ffffff08' }}
          formatter={(v: number | string, _n, p) => [
            `${Number(v).toFixed(3)} s/lap  (${p?.payload?.compound})`,
            'deg slope',
          ]}
        />
        <Bar dataKey="slope" radius={[2, 2, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.isA ? A_COLOR : B_COLOR} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
