import type { TelemetryDriver } from '../types'

// Map a normalized speed value [0,1] to an HSL color.
// 0 → blue (hue 220), 1 → red (hue 0). Passes through cyan, green, yellow.
function speedColor(t: number): string {
  const hue = Math.round(220 - t * 220) // 220 → 0
  return `hsl(${hue},100%,55%)`
}

export function SpeedTrackMap({ driver }: { driver: TelemetryDriver }) {
  const { x, y, speed, brake } = driver.path
  const n = x.length

  if (n < 2) {
    return (
      <p className="py-8 text-center text-sm text-zinc-500">
        No telemetry data available for this lap.
      </p>
    )
  }

  // --- Coordinate normalization ---
  const PAD = 24
  const VIEW_SIZE = 600

  const minX = Math.min(...x)
  const maxX = Math.max(...x)
  const minY = Math.min(...y)
  const maxY = Math.max(...y)
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1
  const scale = (VIEW_SIZE - PAD * 2) / Math.max(spanX, spanY)

  // Normalize to SVG coords: invert Y (telemetry y-up → SVG y-down)
  const svgX = (v: number) => PAD + (v - minX) * scale
  const svgY = (v: number) => VIEW_SIZE - PAD - (v - minY) * scale

  // Speed range for color mapping
  const minSpeed = Math.min(...speed)
  const maxSpeed = Math.max(...speed)
  const speedRange = maxSpeed - minSpeed || 1

  // --- Legend dimensions ---
  const LEG_X = PAD
  const LEG_Y = VIEW_SIZE - PAD + 8  // below the track; viewBox will be taller
  const LEG_W = 120
  const LEG_H = 8
  const TOTAL_H = VIEW_SIZE + 44

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${VIEW_SIZE} ${TOTAL_H}`}
        className="mx-auto block w-full max-w-[600px]"
        style={{ background: 'transparent' }}
        aria-label={`Track map for ${driver.name}`}
      >
        {/* Track segments colored by speed */}
        {Array.from({ length: n - 1 }, (_, i) => {
          const t = (speed[i] - minSpeed) / speedRange
          const color = speedColor(t)
          return (
            <line
              key={i}
              x1={svgX(x[i])}
              y1={svgY(y[i])}
              x2={svgX(x[i + 1])}
              y2={svgY(y[i + 1])}
              stroke={color}
              strokeWidth={5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )
        })}

        {/* Braking dots */}
        {Array.from({ length: n }, (_, i) =>
          brake[i] > 0 ? (
            <circle
              key={`b${i}`}
              cx={svgX(x[i])}
              cy={svgY(y[i])}
              r={3}
              fill="#111"
              stroke="#555"
              strokeWidth={0.8}
              opacity={0.7}
            />
          ) : null,
        )}

        {/* Start/finish marker */}
        <circle cx={svgX(x[0])} cy={svgY(y[0])} r={6} fill="white" stroke="#e10600" strokeWidth={2} />

        {/* Legend: gradient bar */}
        <defs>
          <linearGradient id="speedGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(220,100%,55%)" />
            <stop offset="50%" stopColor="hsl(110,100%,55%)" />
            <stop offset="100%" stopColor="hsl(0,100%,55%)" />
          </linearGradient>
        </defs>
        <rect x={LEG_X} y={LEG_Y} width={LEG_W} height={LEG_H} rx={3} fill="url(#speedGrad)" />
        <text x={LEG_X} y={LEG_Y + LEG_H + 14} fontSize={10} fill="#9ca3af" fontFamily="inherit">
          Slow
        </text>
        <text x={LEG_X + LEG_W} y={LEG_Y + LEG_H + 14} fontSize={10} fill="#9ca3af" fontFamily="inherit" textAnchor="end">
          Fast
        </text>
        {/* Braking key */}
        <circle cx={LEG_X + LEG_W + 20} cy={LEG_Y + LEG_H / 2} r={3} fill="#111" stroke="#555" strokeWidth={0.8} />
        <text x={LEG_X + LEG_W + 28} y={LEG_Y + LEG_H / 2 + 4} fontSize={10} fill="#9ca3af" fontFamily="inherit">
          Braking
        </text>
      </svg>
    </div>
  )
}
