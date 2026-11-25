// WISP 3: app/frontend/lib/charts/palette.ts (adapted: our chart series in place of WISP's irrigation and map colors)
import { currentTheme } from '../theme'

// Chart colors from the design tokens (entrypoints/data.css), resolved for the current color scheme.
// ECharts can't parse oklch(), so each color is converted to rgb by painting it on a canvas.

export type Palette = {
  ink: string
  inkMuted: string
  line: string
  surface: string
  /** Daily high, low and mean temperature (an hour's temperature takes the mean's) */
  temperature: { max: string; min: string; mean: string }
  precipitation: string
  /** Evapotranspiration */
  et: string
  degreeDays: string
  /** The 30-year normal, drawn dashed */
  normal: string
  /** The forecast's shading, drawn faint */
  forecast: string
  /** The projection's P10–P90 band, drawn faint under its P50 line */
  projection: string
  /** Estimated days' hollow points */
  estimated: string
  /** Missing days' hatching */
  missing: string
  /**
   * Risk levels, lowest first, in the API's categorical palettes (agdata.palettes, D93): severity
   * (Very low … Very high, BuYlRd_5) and probability (Very low … High, BuYlRd_4). The same in light
   * and dark, so a level is one color wherever it's shown.
   */
  severity: [string, string, string, string, string]
  probability: [string, string, string, string]
  dark: boolean
}

const TOKENS = {
  ink: '--color-ink',
  inkMuted: '--color-ink-muted',
  line: '--color-line',
  surface: '--color-surface-raised',
  precipitation: '--color-chart-precipitation',
  et: '--color-chart-et',
  degreeDays: '--color-chart-degree-days',
  normal: '--color-chart-normal',
  forecast: '--color-chart-forecast',
  projection: '--color-chart-projection',
  estimated: '--color-chart-estimated',
  missing: '--color-chart-missing',
} as const

/** A color from readPalette as #rrggbb, for libraries that take only hex */
export function hex(color: string): `#${string}` {
  const rgb = color.match(/^rgb\((\d+), (\d+), (\d+)\)$/)
  if (!rgb) return color as `#${string}`
  return `#${rgb
    .slice(1)
    .map((n) => Number(n).toString(16).padStart(2, '0'))
    .join('')}`
}

export function readPalette(element: Element = document.documentElement): Palette {
  const style = getComputedStyle(element)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const context = canvas.getContext('2d', { willReadFrequently: true })
  const color = (token: string) => {
    const value = style.getPropertyValue(token).trim()
    if (!context || !value) return value || '#888888'
    context.clearRect(0, 0, 1, 1)
    context.fillStyle = value
    context.fillRect(0, 0, 1, 1)
    const [r, g, b] = context.getImageData(0, 0, 1, 1).data
    return `rgb(${r}, ${g}, ${b})`
  }
  const named = Object.fromEntries(Object.entries(TOKENS).map(([key, token]) => [key, color(token)])) as Record<
    keyof typeof TOKENS,
    string
  >
  const levels = (name: string, count: number) =>
    Array.from({ length: count }, (_, i) => color(`--color-risk-${name}-${i + 1}`))
  return {
    ...named,
    temperature: {
      max: color('--color-chart-temperature-max'),
      min: color('--color-chart-temperature-min'),
      mean: color('--color-chart-temperature-mean'),
    },
    severity: levels('severity', 5) as Palette['severity'],
    probability: levels('probability', 4) as Palette['probability'],
    dark: currentTheme() === 'dark',
  }
}

/** Shared axis, grid and tooltip styling */
export function baseOption(palette: Palette) {
  const axisLabel = { color: palette.inkMuted, fontSize: 11 }
  return {
    animation: false,
    textStyle: { fontFamily: getComputedStyle(document.body).fontFamily, color: palette.ink },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: palette.surface,
      borderColor: palette.line,
      textStyle: { color: palette.ink, fontSize: 12 },
      axisPointer: { type: 'line' as const, lineStyle: { color: palette.inkMuted, width: 1 } },
      confine: true,
    },
    axisLabel,
    splitLine: { lineStyle: { color: palette.line, opacity: 0.6 } },
    axisLine: { lineStyle: { color: palette.line } },
  }
}
