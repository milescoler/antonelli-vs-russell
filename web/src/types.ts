// Mirrors the JSON schema emitted by the pipeline scripts.
// Any float can be null (NaN serialized to null).

export interface RoundInfo {
  round: number
  slug: string
  eventName: string
  eventDate: string
}

export interface SessionRef {
  slug: string
  round: number
  eventName: string
}

export interface DriverRef {
  code: string
  name: string
  team: string
  teamColor: string
}

export interface StandingDriver {
  code: string
  name: string
  team: string
  teamColor: string
  points: number | null
  wins: number
  podiums: number
  avgFinish: number | null
  bestFinish: number | null
  finishes: (number | null)[]
}

export interface Constructor {
  team: string
  teamColor: string
  points: number | null
  wins: number
  podiums: number
}

export interface PaceRow {
  code: string
  name: string
  team: string
  teamColor: string
  mean: number | null
  rank: number
  byRound: { round: number; value: number | null }[]
}

export interface Stint {
  round: number
  stint: number
  compound: string
  medianLap_s: number | null
  degSlope: number | null
  nClean: number
}

export interface TireDriver {
  code: string
  name: string
  team: string
  teamColor: string
  stints: Stint[]
}

export interface Meta {
  rounds: RoundInfo[]
  sessions: SessionRef[]
  drivers: DriverRef[]
}

export interface SeasonData {
  schemaVersion: number
  season: number
  lastUpdated: string
  source: string
  meta: Meta
  standings: {
    drivers: StandingDriver[]
    constructors: Constructor[]
  }
  qualifying: PaceRow[]
  racePace: PaceRow[]
  tire: TireDriver[]
}

// Telemetry types

export interface TrackPath {
  x: number[]
  y: number[]
  speed: number[]
  brake: number[]
  throttle: number[]
}

export interface Corner {
  x: number
  y: number
}

export interface TelemetryDriver {
  code: string
  name: string
  team: string
  teamColor: string
  path: TrackPath
  corners: Corner[]
}

export interface SessionTelemetry {
  session: {
    slug: string
    round: number
    eventName: string
  }
  drivers: TelemetryDriver[]
}

// --- Lap decomposition (decomp/*.json) ---

export interface CurvePoint { d: number; delta: number | null }
export interface CornerMark { d: number | null; label: string }

export interface Sector {
  i: number
  startM: number | null
  endM: number | null
  midM: number | null
  deltaMean: number | null
  ciLow: number | null
  ciHigh: number | null
  significant: boolean
  faster: string | null
}

export interface AttributionItem {
  sector: number
  driverFaster: string
  deltaS: number | null
  significant: boolean
  narrative: string
}

export interface TrackPoint { x: number | null; y: number | null; rate: number | null }

export interface DecompDriver { code: string; name: string; team: string; color: string | null }

export interface DecompMatchup {
  meta: {
    race: string
    eventName: string
    round: number
    year: number
    session: string
    driverA: DecompDriver
    driverB: DecompDriver
    officialGapS: number | null
    reconResidualS: number | null
    nCleanLapsA: number
    nCleanLapsB: number
  }
  deltaCurve: CurvePoint[]
  corners: CornerMark[]
  sectors: Sector[]
  attribution: AttributionItem[]
  callouts: { topSignificant: number[]; noiseTrap: number | null }
  track: TrackPoint[]
}

export interface IndexMatchup {
  key: string
  race: string
  team: string
  teamColor: string | null
  a: string
  b: string
  valid: boolean
  officialGapS?: number | null
  significantCount?: number
  reason?: string
}

export interface DecompIndex {
  hero: string
  races: { slug: string; name: string; round: number }[]
  matchups: IndexMatchup[]
}

// --- Race-win decomposition (race/*.json) ---

export type Verdict = 'real' | 'noise' | 'inherited' | 'insufficient'

export interface FactorBase {
  verdict: Verdict
  magnitudeS: number | null
  magnitudeUnit?: string
  headline: string
  caveat: string | null
}

export interface WhereDecomp {
  deltaCurve: CurvePoint[]
  corners: CornerMark[]
  sectors: Sector[]
  attribution: AttributionItem[]
  callouts: { topSignificant: number[]; noiseTrap: number | null }
  track: TrackPoint[]
  meta: {
    driverA: { code: string }
    driverB: { code: string }
    nPairs: number
    nUniqueLapsA: number
    nUniqueLapsB: number
    marginCurveS: number | null
  }
}

export interface WhereFactor extends FactorBase {
  decomp: WhereDecomp | null
}

export interface TyreStint {
  code: string
  stint: number
  compound: string
  degSlope_s_per_lap: number | null
  nClean: number
  medianLaptime_s?: number | null
}

export interface TyreFactor extends FactorBase {
  stints: TyreStint[]
}

export interface GapTrace {
  driverCode: string
  laps: number[]
  gap_s: (number | null)[]
  leading: boolean[]
}

export interface PaceFactor extends FactorBase {
  stints: TyreStint[]
  gapTrace: GapTrace
}

export interface StartRow {
  role: string
  code: string
  grid: number | null
  lap1Pos: number | null
  positionsGained: number | null
  finish: number | null
  status: string
  dnf: boolean
}

export interface StartFactor extends FactorBase {
  rows: StartRow[]
}

export interface RaceDriverRef {
  code: string
  name: string
  team: string
  color: string
}

export interface RaceMeta {
  race: string
  eventName: string
  round: number
  year: number
  winner: RaceDriverRef
  p2: RaceDriverRef
  marginS: number | null
  anyDnf: boolean
  winnerInherited: boolean
  winnerStartedPole: boolean
  poleSitter: string | null
}

export interface RaceDecomp {
  meta: RaceMeta
  signConvention: string
  factors: {
    where: WhereFactor
    tyre: TyreFactor
    pace: PaceFactor
    start: StartFactor
  }
  caveats: {
    anyDnf: boolean
    fuelNotCorrected: boolean
    noCleanLapsDriver: string[]
  }
}

export interface RaceIndexEntry {
  slug: string
  round: number
  valid: boolean
  winner?: string
  p2?: string
  marginS?: number | null
  realFactorCount?: number
  reason?: string
}

export interface RaceDecompIndex {
  hero: string
  races: { slug: string; name: string; round: number }[]
  entries: RaceIndexEntry[]
}
