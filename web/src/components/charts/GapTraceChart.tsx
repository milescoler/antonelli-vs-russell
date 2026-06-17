import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { GapTrace } from '../../types'
import { A_COLOR } from '../../lib/format'
import { axisTick, Empty, grid, tooltipStyle, zero } from './common'

export function GapTraceChart({ gap }: { gap: GapTrace }) {
  const data = gap.laps
    .map((lap, i) => ({ lap, gap: gap.gap_s[i] }))
    .filter((d) => d.gap !== null)

  if (data.length === 0)
    return <Empty note="No gap trace — driver didn't lead or retired early." />

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -10, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} />
        <XAxis
          dataKey="lap"
          tick={axisTick}
          label={{ value: 'lap', position: 'insideBottom', offset: -2, fill: '#71717a', fontSize: 11 }}
        />
        <YAxis tick={axisTick} width={48} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`} />
        <ReferenceLine y={0} stroke={zero} />
        <Tooltip
          {...tooltipStyle}
          formatter={(v: number | string) => [`${Number(v).toFixed(2)} s`, 'gap']}
          labelFormatter={(l) => `Lap ${l}`}
        />
        <Line
          type="monotone"
          dataKey="gap"
          stroke={A_COLOR}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
