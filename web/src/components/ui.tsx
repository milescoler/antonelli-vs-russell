import type { ReactNode } from 'react'
import { STUDY_LINKS } from '../lib/links'

export function Panel({
  title,
  subtitle,
  right,
  children,
}: {
  title: string
  subtitle?: string
  right?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-carbon-line bg-carbon-card p-4 sm:p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="f1-bar">
          <h3 className="text-sm font-bold uppercase tracking-wide text-white">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs normal-case text-zinc-500">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  )
}

type Tone = 'zinc' | 'amber' | 'red' | 'sky'

const TONES: Record<Tone, string> = {
  zinc: 'border-carbon-line bg-carbon-soft text-zinc-300',
  amber: 'border-amber-700/50 bg-amber-900/30 text-amber-300',
  red: 'border-f1-red/50 bg-f1-red/15 text-red-300',
  sky: 'border-sky-800/50 bg-sky-950/40 text-sky-300',
}

export function Badge({ children, tone = 'zinc' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${TONES[tone]}`}
    >
      {children}
    </span>
  )
}

// Links out to the full analysis (case study, notebooks, source). The dashboard
// is the descriptive layer; the inference lives in the repo, so every surface
// offers a path to it.
export function StudyLinks({ className = '' }: { className?: string }) {
  const items: [string, string][] = [
    ['Case study', STUDY_LINKS.caseStudy],
    ['Notebooks', STUDY_LINKS.notebooks],
    ['Source', STUDY_LINKS.source],
  ]
  return (
    <span className={className}>
      {items.map(([label, href], i) => (
        <span key={href}>
          {i > 0 && <span className="px-1.5 text-zinc-600">·</span>}
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold underline decoration-zinc-600 underline-offset-2 transition hover:text-f1-red hover:decoration-f1-red"
          >
            {label}
          </a>
        </span>
      ))}
    </span>
  )
}

export function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-zinc-400">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  )
}
