import { Link, useParams } from 'react-router-dom'
import { TeamDashboard } from '../components/TeamDashboard'

// Deep-link route (/team/:slug) for shareable links — renders the same dashboard
// panels as the main grid's inline expansion.
export function TeamPage() {
  const { slug } = useParams()
  return (
    <div className="space-y-4">
      <Link to="/" className="text-sm text-sky-400 hover:text-sky-300">
        ← all teams
      </Link>
      <TeamDashboard slug={slug ?? null} />
    </div>
  )
}
