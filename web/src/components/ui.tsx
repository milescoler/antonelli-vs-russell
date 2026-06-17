import type { ReactNode } from 'react'

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
    <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-zinc-100">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-zinc-500">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  )
}

type Tone = 'zinc' | 'amber' | 'red' | 'sky'

const TONES: Record<Tone, string> = {
  zinc: 'border-zinc-700 bg-zinc-800/60 text-zinc-300',
  amber: 'border-amber-700/50 bg-amber-900/30 text-amber-300',
  red: 'border-red-800/50 bg-red-950/40 text-red-300',
  sky: 'border-sky-800/50 bg-sky-950/40 text-sky-300',
}

export function Badge({ children, tone = 'zinc' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONES[tone]}`}
    >
      {children}
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
