import { A_COLOR, B_COLOR } from '../lib/format'

/** Tiny diverging bar sparkline (pure SVG — light enough for 11 tiles).
 * Positive (A faster) bars go up in sky; negative (B faster) down in zinc. */
export function Sparkline({
  values,
  width = 96,
  height = 30,
}: {
  values: number[]
  width?: number
  height?: number
}) {
  if (values.length === 0) {
    return <div className="text-xs text-zinc-600">no data</div>
  }
  const max = Math.max(0.001, ...values.map((v) => Math.abs(v)))
  const mid = height / 2
  const bw = width / values.length
  return (
    <svg width={width} height={height} role="img" aria-label="lap-delta by round">
      <line x1={0} y1={mid} x2={width} y2={mid} stroke="#3f3f46" strokeWidth={0.75} />
      {values.map((v, i) => {
        const h = (Math.abs(v) / max) * (mid - 1)
        const x = i * bw + 1
        const y = v >= 0 ? mid - h : mid
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={Math.max(1.5, bw - 2)}
            height={Math.max(1, h)}
            rx={0.75}
            fill={v >= 0 ? A_COLOR : B_COLOR}
          />
        )
      })}
    </svg>
  )
}
