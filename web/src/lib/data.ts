import { useEffect, useState } from 'react'
import type { IndexData, TeamData } from '../types'

// import.meta.env.BASE_URL is the Vite `base` (ends with '/'), so data fetches
// resolve correctly whether served at the root or a GitHub Pages subpath.
const BASE = import.meta.env.BASE_URL

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}data/${path}`)
  if (!res.ok) throw new Error(`Failed to load ${path} (HTTP ${res.status})`)
  return (await res.json()) as T
}

export function useIndex() {
  const [data, setData] = useState<IndexData | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    getJSON<IndexData>('index.json')
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [])
  return { data, error }
}

export function useTeam(slug: string | undefined) {
  const [data, setData] = useState<TeamData | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!slug) return
    let live = true
    setData(null)
    setError(null)
    getJSON<TeamData>(`teams/${slug}.json`)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [slug])
  return { data, error }
}
