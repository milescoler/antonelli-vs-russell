import type { QualRound, TeamData } from '../types'

// Driver A = sky, Driver B = zinc (mirrors the notebook's blue/grey).
export const A_COLOR = '#38bdf8'
export const B_COLOR = '#a1a1aa'

export const CATEGORY_LABEL: Record<string, string> = {
  straight: 'Straights',
  slow_corner: 'Slow corners',
  medium_corner: 'Medium corners',
  fast_corner: 'Fast corners',
}

/** Signed, fixed-precision string; null -> em dash. */
export function signed(n: number | null | undefined, digits = 3): string {
  if (n === null || n === undefined) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(digits)
}

export function mean(nums: Array<number | null | undefined>): number | null {
  const xs = nums.filter((n): n is number => typeof n === 'number')
  if (xs.length === 0) return null
  return xs.reduce((a, b) => a + b, 0) / xs.length
}

/** A one-line, screenshot-friendly summary of a team's qualifying story. */
export function takeaway(team: TeamData): string {
  const { a, b } = team.pair
  const deltas = team.qualifying.byRound.map((r: QualRound) => r.lapDelta_s)
  const m = mean(deltas)
  const n = deltas.filter((d) => d !== null).length
  if (m === null || n === 0) return `${a.code} vs ${b.code}: not enough qualifying data yet.`
  const faster = m >= 0 ? a : b
  const slower = m >= 0 ? b : a
  const mag = Math.abs(m).toFixed(3)
  const dnfs = team.race.byRound.filter((r) => r.caveats.anyDnf).length
  const dnfNote = dnfs > 0 ? ` ${dnfs} round${dnfs > 1 ? 's' : ''} saw a DNF.` : ''
  return `Over ${n} round${n > 1 ? 's' : ''}, ${faster.code} out-qualifies ${slower.code} by ${mag}s/lap on average.${dnfNote}`
}
