import { useMemo, useState } from 'react'
import type { TrackGeometry } from '../../types'
import { signed } from '../../lib/format'
import { Empty } from './common'

// Diverging heatmap colors for the track (distinct from the categorical bars):
// cool = A faster, warm = B faster, dim = sensor-excluded / no data.
const FASTER_A = '#38bdf8' // sky
const FASTER_B = '#fb923c' // orange
const NEUTRAL = '#3f3f46' // zinc-700

function color(delta: number | null): string {
  if (delta === null) return NEUTRAL
  return delta >= 0 ? FASTER_A : FASTER_B
}

const VIEW_W = 600
const PAD = 26

export function TrackMap({
  track,
  aCode,
  bCode,
}: {
  track: TrackGeometry | null
  aCode: string
  bCode: string
}) {
  const [hover, setHover] = useState<number | null>(null)

  const geo = useMemo(() => {
    if (!track || track.path.x.length < 2) return null
    const { x, y } = track.path
    const minX = Math.min(...x)
    const maxX = Math.max(...x)
    const minY = Math.min(...y)
    const maxY = Math.max(...y)
    const spanX = maxX - minX || 1
    const spanY = maxY - minY || 1
    const scale = (VIEW_W - 2 * PAD) / Math.max(spanX, spanY)
    const w = spanX * scale + 2 * PAD
    const h = spanY * scale + 2 * PAD
    const sx = (vx: number) => PAD + (vx - minX) * scale
    const sy = (vy: number) => h - PAD - (vy - minY) * scale // invert Y (telemetry is y-up)
    return { sx, sy, w, h }
  }, [track])

  if (!track || !geo) return <Empty note="No track map for this round." />

  const { x, y, delta } = track.path
  const { sx, sy, w, h } = geo

  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 420 }} role="img">
        {/* the racing line, segment-colored by who's faster there */}
        {x.slice(0, -1).map((_, i) => (
          <line
            key={i}
            x1={sx(x[i])}
            y1={sy(y[i])}
            x2={sx(x[i + 1])}
            y2={sy(y[i + 1])}
            stroke={color(delta[i])}
            strokeWidth={6}
            strokeLinecap="round"
          />
        ))}
        {/* start/finish marker */}
        <circle cx={sx(x[0])} cy={sy(y[0])} r={5} fill="#fafafa" stroke="#0a0a0b" strokeWidth={1.5} />
        {/* corner markers */}
        {track.corners.map((c, i) => (
          <circle
            key={i}
            cx={sx(c.x)}
            cy={sy(c.y)}
            r={hover === i ? 8 : 5}
            fill="#0a0a0b"
            stroke={hover === i ? '#fafafa' : '#a1a1aa'}
            strokeWidth={2}
            className="cursor-pointer"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
        {/* hover tooltip */}
        {hover !== null && (
          <CornerTip
            cx={sx(track.corners[hover].x)}
            cy={sy(track.corners[hover].y)}
            w={w}
            corner={track.corners[hover]}
            aCode={aCode}
          />
        )}
      </svg>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs text-zinc-400">
        <span className="flex items-center gap-3">
          <Swatch color={FASTER_A} label={`${aCode} faster`} />
          <Swatch color={FASTER_B} label={`${bCode} faster`} />
          <Swatch color={NEUTRAL} label="excluded" />
        </span>
        <span className="text-zinc-600">hover a corner • ● = start/finish</span>
      </div>
    </div>
  )
}

function CornerTip({
  cx,
  cy,
  w,
  corner,
  aCode,
}: {
  cx: number
  cy: number
  w: number
  corner: { apexDeltaKph: number | null; brakeOnDelta: number | null; throttleFullDelta: number | null }
  aCode: string
}) {
  const bw = 168
  const bh = 60
  // clamp so the box stays inside the viewBox
  const tx = Math.min(Math.max(cx + 10, 4), w - bw - 4)
  const ty = Math.max(cy - bh - 8, 4)
  return (
    <g pointerEvents="none">
      <rect x={tx} y={ty} width={bw} height={bh} rx={6} fill="#18181b" stroke="#3f3f46" />
      <text x={tx + 10} y={ty + 18} fill="#e4e4e7" fontSize={12} fontWeight={600}>
        {aCode} vs teammate
      </text>
      <text x={tx + 10} y={ty + 34} fill="#a1a1aa" fontSize={11}>
        apex {signed(corner.apexDeltaKph, 1)} km/h · brake {signed(corner.brakeOnDelta, 1)} m
      </text>
      <text x={tx + 10} y={ty + 49} fill="#a1a1aa" fontSize={11}>
        throttle {signed(corner.throttleFullDelta, 1)} m (− = earlier/later for {aCode})
      </text>
    </g>
  )
}

function Swatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2.5 w-4 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  )
}
