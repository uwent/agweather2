// WISP 3: app/frontend/lib/charts/weatherCharts.test.ts (only tableTsv's case)
import { describe, expect, it } from 'vitest'

import { tableTsv } from './weatherCharts'

describe('tableTsv', () => {
  it('writes a header, then a row a day with its forecast flag, missing values blank', () => {
    const table = {
      columns: ['High (°F)', 'Note'],
      rows: [
        { date: '2026-07-02', forecast: true, values: ['80.0', 'tab\there'] },
        { date: '2026-07-01', forecast: false, values: ['78.5', null] },
      ],
    }
    expect(tableTsv(table).split('\n')).toEqual([
      'Date\tForecast\tHigh (°F)\tNote',
      '2026-07-02\tyes\t80.0\ttab here',
      '2026-07-01\tno\t78.5\t',
    ])
  })
})
