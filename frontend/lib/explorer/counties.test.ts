import { describe, expect, it } from 'vitest'

import { cellText } from '@/lib/table'
import { units } from '@/lib/units'

import { countyColumns, countyRows, stateCode, summaryParams } from './counties'

describe('summaryParams', () => {
  it('asks for the tiles’ day, hour or range with their settings', () => {
    const params = { units: 'us', dd: 'modified_50_86', roll: null }
    expect(summaryParams({ layer: 'degree_days', time: '2026-07-08', stat: null, params }, 'WI')).toEqual({
      region: 'WI',
      units: 'us',
      dd: 'modified_50_86',
      date: '2026-07-08',
    })
    expect(
      summaryParams({ layer: 'degree_days', time: '2026-01-01..2026-07-08', stat: 'sum', params }, 'IA'),
    ).toMatchObject({ region: 'IA', start: '2026-01-01', end: '2026-07-08', stat: 'sum' })
    expect(summaryParams({ layer: 'air_temperature', time: '2026-07-08T15', stat: null, params: {} }, 'WI')).toEqual({
      region: 'WI',
      time: '2026-07-08T15',
    })
    expect(summaryParams({ layer: 'air_temperature_min', time: 'latest', stat: null, params: {} }, 'WI')).toEqual({
      region: 'WI',
    })
  })
})

describe('stateCode', () => {
  it('finds the coverage’s states by code or name', () => {
    expect(stateCode('WI')).toBe('WI')
    expect(stateCode('Wisconsin')).toBe('WI')
    expect(stateCode('CA')).toBeNull()
    expect(stateCode(null)).toBeNull()
  })
})

describe('countyRows and countyColumns', () => {
  it('keeps values in the stored unit and shows them in the reader’s', () => {
    const rows = countyRows(
      { fips: ['55025'], name: ['Dane County'], coverage: [100], mean: [32], min: [14], max: [50] },
      'degC',
    )
    expect(rows[0].mean).toBeCloseTo(0)
    expect(rows[0].min).toBeCloseTo(-10)
    const metric = countyColumns(rows, { unit: 'degC', units: units('metric'), categories: null })
    expect(metric.map((c) => c.label)).toEqual([
      'County',
      'Average (°C)',
      'Lowest (°C)',
      'Highest (°C)',
      'Land with data (%)',
    ])
    expect(cellText(metric[2], rows[0])).toBe('-10.0')
    const us = countyColumns(rows, { unit: 'degC', units: units('imperial'), categories: null })
    expect(cellText(us[1], rows[0])).toBe('32')
  })

  it('gives a map of levels the highest level and the land at each', () => {
    const rows = countyRows(
      {
        fips: ['55001', '55003'],
        name: ['Adams County', 'Ashland County'],
        coverage: [100, 98],
        pct_low: [20, 0],
        pct_high: [80, 0],
        highest: ['High', null],
      },
      'index',
    )
    const categories = [
      { value: 0, code: 'low', name: 'Low' },
      { value: 1, code: 'high', name: 'High' },
    ]
    const columns = countyColumns(rows, { unit: 'index', units: units('imperial'), categories })
    expect(columns.map((c) => c.label)).toEqual([
      'County',
      'Highest level',
      'Low (% of land)',
      'High (% of land)',
      'Land with data (%)',
    ])
    expect(columns[1].value(rows[0])).toBe(1)
    expect(cellText(columns[1], rows[1])).toBe('—')
    expect(cellText(columns[3], rows[0])).toBe('80')
  })

  it('names a stage map’s values by their codes', () => {
    const rows = countyRows({ fips: ['1'], name: ['A'], coverage: [100], mean: [9.6], min: [-1], max: [12] }, 'index')
    const categories = [
      { value: -1, code: null, name: 'Before VE' },
      { value: 0, code: 'VE', name: 'Emergence' },
      ...Array.from({ length: 12 }, (_, k) => ({ value: k + 1, code: `V${k + 1}`, name: `${k + 1} leaf collars` })),
    ]
    const columns = countyColumns(rows, { unit: 'index', units: units('imperial'), categories })
    expect(columns[1].label).toBe('Average')
    expect(cellText(columns[1], rows[0])).toBe('V10')
    expect(cellText(columns[2], rows[0])).toBe('Before VE')
  })
})
