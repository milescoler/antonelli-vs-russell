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
