import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { StintPace } from '../../types'
import { A_COLOR, B_COLOR } from '../../lib/format'
import { axisTick, Empty, grid, tooltipStyle } from './common'

export function StintPaceChart({
  stints,
  aCode,
  bCode,
}: {
  stints: StintPace[]
  aCode: string
  bCode: string
}) {
  const byStint = new Map<number, Record<string, number | string>>()
  let lo = Infinity
  let hi = -Infinity
  for (const s of stints) {
    if (s.stint === null || s.medianLaptime_s === null) continue
    const row = byStint.get(s.stint) ?? { stint: `Stint ${s.stint}` }
    row[s.code] = s.medianLaptime_s
    byStint.set(s.stint, row)
    lo = Math.min(lo, s.medianLaptime_s)
    hi = Math.max(hi, s.medianLaptime_s)
  }
  const data = [...byStint.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r)
  if (data.length === 0) return <Empty note="No clean-lap pace this round." />

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} />
        <XAxis dataKey="stint" tick={axisTick} />
        <YAxis
          tick={axisTick}
          width={52}
          domain={[Math.floor(lo - 0.8), Math.ceil(hi + 0.8)]}
          tickFormatter={(v) => `${v}s`}
          allowDecimals={false}
        />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: '#ffffff08' }}
          formatter={(v: number | string) => [`${Number(v).toFixed(3)} s`, '']}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey={aCode} fill={A_COLOR} radius={[2, 2, 0, 0]} />
        <Bar dataKey={bCode} fill={B_COLOR} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
