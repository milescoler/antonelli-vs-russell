import { Badge } from './ui'

export function QualCaveats({
  qMismatch,
  sensorFreezeAny,
}: {
  qMismatch: boolean
  sensorFreezeAny: boolean
}) {
  if (!qMismatch && !sensorFreezeAny) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {qMismatch && <Badge tone="amber">Q-session mismatch</Badge>}
      {sensorFreezeAny && <Badge tone="amber">sensor freeze excluded</Badge>}
    </div>
  )
}

export function RaceCaveats({
  anyDnf,
  smallSampleDeg,
  noCleanLapsDriver,
}: {
  anyDnf: boolean
  smallSampleDeg: boolean
  noCleanLapsDriver: string[]
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {anyDnf && <Badge tone="red">DNF this round</Badge>}
      {smallSampleDeg && <Badge tone="amber">small-sample stints</Badge>}
      {noCleanLapsDriver.map((c) => (
        <Badge key={c} tone="amber">
          {c}: no clean laps
        </Badge>
      ))}
      <Badge tone="zinc">not fuel-corrected</Badge>
    </div>
  )
}
