import type { StartRow } from '../types'
import { A_COLOR, B_COLOR } from '../lib/format'
import { Badge } from './ui'

const roleColor = (role: string) =>
  role === 'A' ? A_COLOR : role === 'B' ? B_COLOR : '#ef4444'

const pos = (n: number | null) => (n === null ? '—' : `P${n}`)

export function StartConversion({ start }: { start: StartRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-zinc-500">
            <th className="py-1.5 pr-3 font-medium">Driver</th>
            <th className="py-1.5 px-3 font-medium">Grid</th>
            <th className="py-1.5 px-3 font-medium">Lap 1</th>
            <th className="py-1.5 pl-3 font-medium">Finish</th>
          </tr>
        </thead>
        <tbody className="text-zinc-200">
          {start.map((r) => (
            <tr key={r.role} className="border-t border-zinc-800">
              <td className="py-2 pr-3">
                <span className="inline-flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: roleColor(r.role) }} />
                  <span className="font-medium">{r.code}</span>
                  <span className="text-xs text-zinc-500">{r.role === 'P2' ? 'field P2' : r.role}</span>
                </span>
              </td>
              <td className="py-2 px-3 tabular-nums">{pos(r.grid)}</td>
              <td className="py-2 px-3 tabular-nums">{pos(r.lap1Pos)}</td>
              <td className="py-2 pl-3 tabular-nums">
                {r.dnf ? <Badge tone="red">DNF{r.finish ? ` (P${r.finish})` : ''}</Badge> : pos(r.finish)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
