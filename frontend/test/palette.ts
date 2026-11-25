import type { Palette } from '@/lib/charts/palette'

/** A palette for chart builders' tests: each color named for what it's for, so a test can say which was used */
export const testPalette: Palette = {
  ink: 'ink',
  inkMuted: 'ink-muted',
  line: 'line',
  surface: 'surface',
  temperature: { max: 'max', min: 'min', mean: 'mean' },
  precipitation: 'precipitation',
  et: 'et',
  degreeDays: 'degree-days',
  normal: 'normal',
  forecast: 'forecast',
  projection: 'projection',
  estimated: 'estimated',
  missing: 'missing',
  severity: ['s1', 's2', 's3', 's4', 's5'],
  probability: ['p1', 'p2', 'p3', 'p4'],
  dark: false,
}
