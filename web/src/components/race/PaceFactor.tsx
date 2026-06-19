import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import type { PaceFactor as PaceFactorType } from '../../types'
import { Panel, Badge } from '../ui'
import { tooltipStyle, axisTick, grid, zero } from '../charts/common'

const VERDICT_TONE = {
  real:        'sky',
  noise:       'zinc',
  inherited:   'amber',
  insufficient: 'zinc',
} as const

export function PaceFactor({ factor }: { factor: PaceFactorType }) {
  const { gapTrace } = factor
  const data = gapTrace.laps.map((l, i) => ({
    lap: l,
    gap: gapTrace.gap_s[i],
  }))

  const tone = VERDICT_TONE[factor.verdict]

  return (
    <Panel
      title="Pace Factor"
      right={<Badge tone={tone}>{factor.verdict}</Badge>}
    >
      <p className="mb-3 text-sm text-zinc-300">{factor.headline}</p>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={grid} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="lap"
              tick={axisTick}
              label={{ value: 'Lap', position: 'insideBottomRight', offset: -4, fill: '#a1a1aa', fontSize: 11 }}
            />
            <YAxis
              tick={axisTick}
              tickFormatter={(v: number) => v.toFixed(1)}
              label={{ value: 'Gap (s)', angle: -90, position: 'insideLeft', offset: 8, fill: '#a1a1aa', fontSize: 11 }}
            />
            <Tooltip
              {...tooltipStyle}
              formatter={(value) => {
                const v = typeof value === 'number' ? value : null
                return v !== null ? [`${v.toFixed(2)} s`, 'Gap'] : ['—', 'Gap']
              }}
              labelFormatter={(label) => `Lap ${label}`}
            />
            <ReferenceLine y={0} stroke={zero} strokeDasharray="4 2" />
            <Line
              type="monotone"
              dataKey="gap"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1.5 text-[11px] text-zinc-600">
        Negative gap = {gapTrace.driverCode} leading / ahead of P2
      </p>
      {factor.caveat && (
        <p className="mt-1 text-[11px] text-zinc-600">{factor.caveat}</p>
      )}
    </Panel>
  )
}
