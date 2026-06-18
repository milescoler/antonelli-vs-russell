// Mirrors the JSON schema emitted by scripts/build_site_data.py.
// Any float can be null (NaN serialized to null).

export interface DriverRef {
  code: string
  number: number
  name: string
}

export interface Pair {
  a: DriverRef
  b: DriverRef
}

export interface RoundInfo {
  round: number
  slug: string
  eventName: string
  eventDate: string
  format: string
  hasQualifying: boolean
  hasRace: boolean
}

export interface TeamSummaryStat {
  meanLapDelta_s: number | null
  lapDeltaByRound: number[]
  yoyDeltaOfDeltas_s: number | null
}

export interface TeamSummary {
  slug: string
  displayName: string
  canonicalPair: Pair
  yoyAvailable: boolean
  roundsCovered: number[]
  hasSwap: boolean
  summary: TeamSummaryStat
}

export interface IndexData {
  schemaVersion: number
  season: number
  lastUpdated: string
  source: string
  rounds: RoundInfo[]
  teams: TeamSummary[]
}

export interface SegmentCategoryMean {
  category: string
  meanDelta_s: number | null
  nSegments: number
}

export interface CornerBucket {
  category: string
  apexDeltaKph_mean: number | null
  brakeOnDelta_m_mean: number | null
  throttleFullDelta_m_mean: number | null
  nCorners: number
}

export interface TrackCorner {
  x: number
  y: number
  apexDeltaKph: number | null
  brakeOnDelta: number | null
  throttleFullDelta: number | null
}

export interface TrackGeometry {
  path: { x: number[]; y: number[]; delta: (number | null)[] }
  corners: TrackCorner[]
}

export interface QualRound {
  round: number
  eventName: string
  pairThisRound: { aCode: string; bCode: string }
  isCanonicalPair: boolean
  lapTimeA_s: number | null
  lapTimeB_s: number | null
  lapDelta_s: number | null
  qSessionA: number | null
  qSessionB: number | null
  caveats: { qMismatch: boolean; sensorFreezeAny: boolean }
  segmentCategoryMeans: SegmentCategoryMean[]
  cornerSignatureBuckets: CornerBucket[]
  track: TrackGeometry | null
}

export interface Yoy {
  season: number
  meanLapDelta_s_2026: number | null
  meanLapDelta_s_2025: number | null
  deltaOfDeltas_s: number | null
  nRoundsCompared: number
}

export interface StartRow {
  role: 'A' | 'B' | 'P2'
  code: string
  grid: number | null
  lap1Pos: number | null
  positionsGained: number | null
  finish: number | null
  status: string
  dnf: boolean
}

export interface StintPace {
  code: string
  stint: number | null
  compound: string
  medianLaptime_s: number | null
  nClean: number | null
}

export interface TireDeg {
  code: string
  stint: number | null
  compound: string
  degSlope_s_per_lap: number | null
  nClean: number | null
}

export interface GapTrace {
  driverCode: string
  laps: number[]
  gap_s: (number | null)[]
  leading: boolean[]
}

export interface RaceRound {
  round: number
  eventName: string
  pairThisRound: { aCode: string; bCode: string }
  isCanonicalPair: boolean
  start: StartRow[]
  stintPace: StintPace[]
  tireDeg: TireDeg[]
  gapTrace: GapTrace
  caveats: {
    anyDnf: boolean
    smallSampleDeg: boolean
    noCleanLapsDriver: string[]
    fuelNotCorrected: boolean
  }
}

export interface StandingRow {
  code: string
  name: string
  team: string
  teamColor: string | null
  points: number | null
  wins: number
  podiums: number
  avgFinish: number | null
  bestFinish: number | null
  finishes: (number | null)[]
}

export interface NextRace {
  round: number
  eventName: string
  country: string
  location: string
  eventDate: string
  format: string
}

export interface StandingsData {
  schemaVersion: number
  season: number
  nextRace: NextRace | null
  standings: StandingRow[]
}

export interface MarginRow {
  code: string
  name: string
  team: string | null
  teamColor: string | null
  vs: string
  marginPct: number | null
  ciLow: number | null
  ciHigh: number | null
  n: number
  winRate: number | null
  signTestP: number | null
  verdict: 'reliably_faster' | 'reliably_slower' | 'inconclusive'
  deltas: (number | null)[]
}

export interface IslandComponent {
  id: number
  teamSeasons: { year: number; team: string }[]
  drivers: string[]
  multiTeam: boolean
}

export interface EqualCarDriver {
  code: string
  name: string
  team: string | null
  teamColor: string | null
  theta: number | null
  ciLow: number | null
  ciHigh: number | null
  rank: number
}

export interface EqualCarIsland {
  component: number
  multiTeam: boolean
  drivers: EqualCarDriver[]
}

export interface DriverRatings {
  schemaVersion: number
  season: number
  headline: { metric: string; note: string; ranking: MarginRow[] }
  islands: { note: string; components: IslandComponent[] }
  equalCar: { note: string; islands: EqualCarIsland[] }
}

export interface TeamData {
  schemaVersion: number
  slug: string
  displayName: string
  pair: Pair
  signConvention: string
  qualifying: { byRound: QualRound[]; yoy?: Yoy }
  race: { byRound: RaceRound[] }
  caveatsGlobal: { fuelNotCorrected: boolean; syntheticHistory: boolean; notes: string[] }
}
