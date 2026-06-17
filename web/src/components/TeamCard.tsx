import { Link } from 'react-router-dom'
import type { TeamSummary } from '../types'
import { Badge } from './ui'

export function TeamCard({ team }: { team: TeamSummary }) {
  const { a, b } = team.canonicalPair
  return (
    <Link
      to={`/team/${team.slug}`}
      className="group flex flex-col gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 transition hover:border-sky-700/60 hover:bg-zinc-900"
    >
      <div className="text-sm font-semibold tracking-tight text-zinc-100 group-hover:text-white">
        {team.displayName}
      </div>
      <div className="flex items-center gap-2 text-lg font-bold">
        <span style={{ color: '#38bdf8' }}>{a.code}</span>
        <span className="text-xs font-normal text-zinc-600">vs</span>
        <span style={{ color: '#a1a1aa' }}>{b.code}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {team.yoyAvailable && <Badge tone="sky">YoY vs 2025</Badge>}
        {team.hasSwap && <Badge tone="amber">lineup change</Badge>}
      </div>
    </Link>
  )
}
