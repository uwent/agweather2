import { describe, expect, it } from 'vitest'

import { units } from '@/lib/units'

import { cellSummary, cellTable, shownValues } from './cellChart'
import type { CellSeries } from './cellSeries'

const series = (changes: Partial<CellSeries> = {}): CellSeries => ({
  times: ['2026-07-06', '2026-07-07', '2026-07-08'],
  values: [50, null, 68],
  kinds: ['observed', 'observed', 'forecast'],
  unit: '°F',
  labels: null,
  warnings: [],
  ...changes,
})

describe('the cell’s chart', () => {
  it('shows US values in the reader’s units', () => {
    expect(shownValues(series(), 'degC', units('imperial'))).toEqual({ values: [50, null, 68], unit: '°F' })
    const metric = shownValues(series(), 'degC', units('metric'))
    expect(metric.unit).toBe('°C')
    expect(metric.values.map((v) => (v === null ? null : Math.round(v)))).toEqual([10, null, 20])
    expect(shownValues(series({ values: [100] }), 'degF_day', units('metric')).values[0]).toBeCloseTo(55.56, 2)
  })

  it('leaves risk levels as they are', () => {
    const levels = series({ values: [0, 1, 2], labels: ['Very low', 'Low', 'Moderate'] })
    expect(shownValues(levels, 'index', units('metric')).values).toEqual([0, 1, 2])
  })

  it('says what the chart shows, with its forecast and missing days', () => {
    expect(cellSummary(series(), [50, null, 68], '°F', null, 0)).toBe(
      'From Jul 6 to Jul 8, values run from 50 °F (Jul 6) to 68 °F (Jul 8). The last day is a forecast. 1 day has no value.',
    )
    expect(cellSummary(series(), [0, 2, 1], '', ['Very low', 'Low', 'Moderate'], 0)).toContain(
      'from Very low (Jul 6) to Moderate (Jul 7)',
    )
  })

  it('lists the values newest first, the forecast marked', () => {
    expect(cellTable(series(), [50, null, 68], 'Low (°F)', null, 0)).toEqual({
      columns: ['Low (°F)'],
      rows: [
        { date: '2026-07-08', forecast: true, values: ['68'] },
        { date: '2026-07-07', forecast: false, values: [null] },
        { date: '2026-07-06', forecast: false, values: ['50'] },
      ],
    })
  })
})
