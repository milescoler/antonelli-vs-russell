export const tooltipStyle = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#e4e4e7' },
  itemStyle: { color: '#e4e4e7' },
}

export const axisTick = { fill: '#a1a1aa', fontSize: 11 }
export const grid = '#27272a'
export const zero = '#52525b'

export const shortEvent = (name: string) => name.replace(' Grand Prix', '')

export function Empty({ note = 'No data for this round.' }: { note?: string }) {
  return <p className="py-10 text-center text-sm text-zinc-600">{note}</p>
}
