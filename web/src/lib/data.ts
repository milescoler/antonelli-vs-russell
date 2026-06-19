import { useEffect, useState } from 'react'
import type { SeasonData, SessionTelemetry } from '../types'
import type { DecompIndex, DecompMatchup } from '../types'

// import.meta.env.BASE_URL is the Vite `base` (ends with '/'), so data fetches
// resolve correctly whether served at the root or a GitHub Pages subpath.
const BASE = import.meta.env.BASE_URL

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}data/${path}`)
  if (!res.ok) throw new Error(`Failed to load ${path} (HTTP ${res.status})`)
  return (await res.json()) as T
}

export function useSeason() {
  const [data, setData] = useState<SeasonData | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    getJSON<SeasonData>('season.json')
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [])
  return { data, error }
}

export function useTelemetry(slug: string | undefined) {
  const [data, setData] = useState<SessionTelemetry | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!slug) return
    let live = true
    setData(null)
    setError(null)
    getJSON<SessionTelemetry>(`telemetry/${slug}.json`)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [slug])
  return { data, error }
}

export function useDecompIndex() {
  const [data, setData] = useState<DecompIndex | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    getJSON<DecompIndex>('decomp/index.json')
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [])
  return { data, error }
}

export function useDecompMatchup(key: string | undefined) {
  const [data, setData] = useState<DecompMatchup | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!key) return
    let live = true
    setData(null)
    setError(null)
    getJSON<DecompMatchup>(`decomp/${key}.json`)
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
    return () => {
      live = false
    }
  }, [key])
  return { data, error }
}
