import { useEffect, useRef, useState } from 'react'
import { useIndex } from '../lib/data'
import { OverviewGrid } from '../components/OverviewGrid'
import { TeamDashboard } from '../components/TeamDashboard'

export function Dashboard() {
  const { data, error } = useIndex()
  const [selected, setSelected] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  // Default to Mercedes (the Antonelli story) so the dashboard isn't empty.
  useEffect(() => {
    if (data && !selected) {
      const has = data.teams.some((t) => t.slug === 'mercedes')
      setSelected(has ? 'mercedes' : (data.teams[0]?.slug ?? null))
    }
  }, [data, selected])

  const onSelect = (slug: string) => {
    setSelected(slug)
    detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          Driver vs Car — the 2026 grid
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Same car, same season: whatever separates two teammates is mostly the driver. Each tile
          shows the season qualifying edge and its round-by-round shape (sky = the lower-car-number
          driver faster). Click a team for the full breakdown.
        </p>
      </section>

      {error && (
        <p className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-300">
          Couldn't load the grid: {error}
        </p>
      )}
      {!data && !error && <p className="text-sm text-zinc-500">Loading grid…</p>}
      {data && <OverviewGrid teams={data.teams} selected={selected} onSelect={onSelect} />}

      <div ref={detailRef} className="scroll-mt-20 border-t border-zinc-800 pt-6">
        <TeamDashboard slug={selected} />
      </div>
    </div>
  )
}
