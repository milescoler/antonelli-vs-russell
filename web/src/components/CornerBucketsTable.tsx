import type { CornerBucket } from '../types'
import { CATEGORY_LABEL, signed } from '../lib/format'
import { Empty } from './charts/common'

export function CornerBucketsTable({
  buckets,
  aCode,
}: {
  buckets: CornerBucket[]
  aCode: string
}) {
  if (buckets.length === 0) return <Empty />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-zinc-500">
            <th className="py-1.5 pr-3 font-medium">Corner type</th>
            <th className="py-1.5 px-3 text-right font-medium">Apex Δ (km/h)</th>
            <th className="py-1.5 px-3 text-right font-medium">Brake Δ (m)</th>
            <th className="py-1.5 px-3 text-right font-medium">Throttle Δ (m)</th>
            <th className="py-1.5 pl-3 text-right font-medium">n</th>
          </tr>
        </thead>
        <tbody className="text-zinc-300">
          {buckets.map((b) => (
            <tr key={b.category} className="border-t border-zinc-800">
              <td className="py-1.5 pr-3">{CATEGORY_LABEL[b.category] ?? b.category}</td>
              <td className="py-1.5 px-3 text-right tabular-nums">{signed(b.apexDeltaKph_mean, 1)}</td>
              <td className="py-1.5 px-3 text-right tabular-nums">{signed(b.brakeOnDelta_m_mean, 1)}</td>
              <td className="py-1.5 px-3 text-right tabular-nums">{signed(b.throttleFullDelta_m_mean, 1)}</td>
              <td className="py-1.5 pl-3 text-right tabular-nums text-zinc-500">{b.nCorners}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-zinc-500">
        + apex = {aCode} carries more speed · − brake = {aCode} brakes later · − throttle ={' '}
        {aCode} to full throttle sooner.
      </p>
    </div>
  )
}
