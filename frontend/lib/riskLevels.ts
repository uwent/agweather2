// A model's risk level as a color: the same level the same color everywhere (docs/frontend.md, Maps), from the
// `--color-risk-*` tokens, which are the API's categorical palettes (BuYlRd_5 for the five severity levels, Very low
// to Very high; BuYlRd_4 for four, Very low to High). A scale of two or three levels (apple scab's Low and
// Infection; fire blight's Low, High and Extreme) takes the four-level colors at its lowest, its highest and, for
// three, yellow between: the same blue-to-red reading without a token of its own.

/** The CSS color for level `level` (0 the lowest) of a scale of `count` levels; undefined without a level */
export function riskColor(level: number | null | undefined, count: number): string | undefined {
  if (level === null || level === undefined || !Number.isFinite(level) || count < 1) return undefined
  const k = Math.max(0, Math.min(count - 1, Math.round(level)))
  if (count === 5) return `var(--color-risk-severity-${k + 1})`
  if (count === 4) return `var(--color-risk-probability-${k + 1})`
  const steps = count === 3 ? [1, 2, 4] : count === 2 ? [1, 4] : [4]
  return `var(--color-risk-probability-${steps[k]})`
}

/** Where a level sits on its scale, 0 (lowest) to 1 (highest), for sorting cards' risks across scales */
export function riskRank(level: number | null | undefined, count: number): number {
  if (level === null || level === undefined || !Number.isFinite(level) || count < 2) return -1
  return Math.max(0, Math.min(1, level / (count - 1)))
}
