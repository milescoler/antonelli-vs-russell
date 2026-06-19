import type { DecompMatchup } from '../../types'

// Diverging color: t in [-1,1]. Negative (A faster here) -> blue; positive
// (B faster here) -> red; near zero -> grey.
function rateColor(t: number): string {
  const mag = Math.min(1, Math.abs(t))
  const light = 30 + mag * 30
  if (t < 0) return `hsl(210,90%,${light}%)`
  if (t > 0) return `hsl(0,90%,${light}%)`
  return 'hsl(0,0%,45%)'
}

export function DecompTrackMap({ matchup }: { matchup: DecompMatchup }) {
  const pts = matchup.track.filter((p) => p.x != null && p.y != null) as
    { x: number; y: number; rate: number | null }[]
  const n = pts.length
  if (n < 2) return <p className="py-8 text-center text-sm text-zinc-500">No track geometry.</p>

  const a = matchup.meta.driverA.code
  const b = matchup.meta.driverB.code
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const PAD = 24
  const VIEW = 600
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const scale = (VIEW - PAD * 2) / Math.max(maxX - minX || 1, maxY - minY || 1)
  const sx = (v: number) => PAD + (v - minX) * scale
  const sy = (v: number) => VIEW - PAD - (v - minY) * scale

  const maxRate = Math.max(1e-6, ...pts.map((p) => Math.abs(p.rate ?? 0)))

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${VIEW} ${VIEW + 36}`} className="mx-auto block w-full max-w-[600px]"
        aria-label={`Where time is won and lost, ${a} vs ${b}`}>
        {Array.from({ length: n - 1 }, (_, i) => (
          <line key={i} x1={sx(pts[i].x)} y1={sy(pts[i].y)} x2={sx(pts[i + 1].x)} y2={sy(pts[i + 1].y)}
            stroke={rateColor((pts[i].rate ?? 0) / maxRate)} strokeWidth={5}
            strokeLinecap="round" strokeLinejoin="round" />
        ))}
        <circle cx={sx(pts[0].x)} cy={sy(pts[0].y)} r={6} fill="white" stroke="#e10600" strokeWidth={2} />
        <text x={PAD} y={VIEW + 22} fontSize={11} fill="#60a5fa" fontFamily="inherit">{a} faster</text>
        <text x={VIEW - PAD} y={VIEW + 22} fontSize={11} fill="#f87171" fontFamily="inherit" textAnchor="end">{b} faster</text>
      </svg>
    </div>
  )
}
