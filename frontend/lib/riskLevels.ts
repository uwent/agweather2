// A model's risk level as a color: the same level the same color everywhere (docs/frontend.md, Maps), from the
// `--color-risk-severity-*` tokens, which are the API's five risk levels (BuYlRd_5, Very low to Very high). Four
// levels take BuYlRd_4's colors (Very low, Moderate, High and Very high's). Two or three take the five's colors for
// the same names (Ben, 2026-11-26), so Low, Moderate and High are one color wherever they appear; fire blight's
// Extreme and apple scab's Infection, each its scale's top, take Very high's. agdata.palettes.RISK_STEPS is the same
// table, and the map's palettes for these scales are these colors (riskLevels.test.ts holds both to it).

/** A scale: its levels' names, lowest first, or only how many there are (two or three then read as Low, Moderate,
 * High and as Low, Very high) */
export type RiskScale = number | readonly string[]

export const RISK_STEPS: Record<string, number> = {
  'Very low': 0,
  Low: 1,
  Moderate: 2,
  High: 3,
  'Very high': 4,
  Extreme: 4,
  Infection: 4,
}

const DEFAULT_STEPS: Record<number, number[]> = { 1: [4], 2: [1, 4], 3: [1, 2, 3], 4: [0, 2, 3, 4], 5: [0, 1, 2, 3, 4] }

function count(scale: RiskScale): number {
  return typeof scale === 'number' ? scale : scale.length
}

/** Each level's step (0 to 4) on the five risk levels' colors */
export function riskSteps(scale: RiskScale): number[] {
  const n = count(scale)
  if (typeof scale === 'number' || n >= 4) return DEFAULT_STEPS[n] ?? []
  const named = scale.map((name) => RISK_STEPS[name])
  return named.every((s) => s !== undefined) ? named : (DEFAULT_STEPS[n] ?? [])
}

/** The step (0 to 4) of level `level` (0 the lowest) on its scale; undefined without a level */
export function riskStep(level: number | null | undefined, scale: RiskScale): number | undefined {
  const n = count(scale)
  if (level === null || level === undefined || !Number.isFinite(level) || n < 1) return undefined
  return riskSteps(scale)[Math.max(0, Math.min(n - 1, Math.round(level)))]
}

/** The CSS color for level `level` (0 the lowest) of a scale; undefined without a level */
export function riskColor(level: number | null | undefined, scale: RiskScale): string | undefined {
  const step = riskStep(level, scale)
  return step === undefined ? undefined : `var(--color-risk-severity-${step + 1})`
}

/** Where a level sits on its scale, 0 (lowest) to 1 (highest), for sorting cards' risks across scales */
export function riskRank(level: number | null | undefined, scale: RiskScale): number {
  const n = count(scale)
  if (level === null || level === undefined || !Number.isFinite(level) || n < 2) return -1
  return Math.max(0, Math.min(1, level / (n - 1)))
}
