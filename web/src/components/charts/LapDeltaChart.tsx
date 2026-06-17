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
import type { QualRound } from '../../types'
import { A_COLOR, B_COLOR } from '../../lib/format'
import { axisTick, Empty, grid, shortEvent, tooltipStyle, zero } from './common'

export function LapDeltaChart({
  rounds,
  aCode,
  bCode,
}: {
  rounds: QualRound[]
  aCode: string
  bCode: string
}) {
  const data = rounds
    .filter((r) => r.lapDelta_s !== null)
    .map((r) => ({ name: shortEvent(r.eventName), delta: r.lapDelta_s as number }))

  if (data.length === 0) return <Empty note="No qualifying data yet." />

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -10, bottom: 28 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} />
        <XAxis
          dataKey="name"
          tick={axisTick}
          angle={-28}
          textAnchor="end"
          height={56}
          interval={0}
        />
        <YAxis
          tick={axisTick}
          width={48}
          tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`}
          label={{ value: 's/lap', angle: -90, position: 'insideLeft', fill: '#71717a', fontSize: 11 }}
        />
        <ReferenceLine y={0} stroke={zero} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: '#ffffff08' }}
          formatter={(v: number | string) => [
            `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(3)} s`,
            `${aCode} − ${bCode}`,
          ]}
        />
        <Bar dataKey="delta" radius={[2, 2, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.delta >= 0 ? A_COLOR : B_COLOR} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
