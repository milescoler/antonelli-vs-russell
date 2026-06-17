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
import type { SegmentCategoryMean } from '../../types'
import { A_COLOR, B_COLOR, CATEGORY_LABEL } from '../../lib/format'
import { axisTick, Empty, grid, tooltipStyle, zero } from './common'

export function SegmentSplitChart({ segments }: { segments: SegmentCategoryMean[] }) {
  const data = segments
    .filter((s) => s.meanDelta_s !== null)
    .map((s) => ({
      name: CATEGORY_LABEL[s.category] ?? s.category,
      delta: s.meanDelta_s as number,
      n: s.nSegments,
    }))

  if (data.length === 0) return <Empty />

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -10, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} />
        <XAxis dataKey="name" tick={axisTick} interval={0} />
        <YAxis tick={axisTick} width={56} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`} />
        <ReferenceLine y={0} stroke={zero} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: '#ffffff08' }}
          formatter={(v: number | string, _n, p) => [
            `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(3)} s/lap  (${p?.payload?.n} segs)`,
            'mean delta',
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
