// WISP 3: app/frontend/lib/charts/weatherCharts.test.ts (adapted: panels over the API's columns, from answers
// recorded from the dev server in frontend/test/fixtures/site)
import { describe, expect, it } from 'vitest'

import { tableRows, type Table } from '@/lib/tableRows'
import { units as unitsFor } from '@/lib/units'
import daily from '@/test/fixtures/site/daily.json'
import hourly from '@/test/fixtures/site/hourly.json'
import { testPalette as palette } from '@/test/palette'
import type { TableResponse } from '@/types/api'

import {
  panelColumns,
  panelCsvRows,
  panelOption,
  panelSummary,
  panelTable,
  shownPanels,
  tableTsv,
  weatherPanels,
  type WeatherPanel,
} from './weatherCharts'

const us = unitsFor('imperial')
const metric = unitsFor('metric')
const days = tableRows(daily as TableResponse)
const hours = tableRows(hourly as TableResponse)
const today = '2026-11-25'

type Option = {
  series: {
    id?: string
    name: string
    type: string
    data: unknown[]
    xAxisIndex: number
    markLine?: { data: object[] }
    markArea?: object
    lineStyle?: { opacity?: number }
  }[]
  grid: object[]
  yAxis: { name?: string }[]
  legend?: { data: string[] }
  tooltip: { formatter: (params: unknown) => string }
}

const panel = (key: string, hourly = false) => weatherPanels({ hourly }).find((p) => p.key === key)!
const option = (p: WeatherPanel, table: Table = days, extra: object = {}) =>
  panelOption(p, table, { units: us, palette, today, ...extra }) as unknown as Option

describe('weatherPanels', () => {
  it('asks for the catalog columns of each measure, daily or hourly', () => {
    expect(panelColumns(weatherPanels({ hourly: false }))).toEqual([
      'air_temperature_max',
      'air_temperature_min',
      'air_temperature_mean',
      'precipitation_sum',
      'relative_humidity_mean',
      'relative_humidity_min',
      'dew_point_mean',
      'wind_speed_mean',
      'wind_gust_max',
      'shortwave_radiation_sum',
      'et0_sum',
      'soil_temperature_4cm_mean',
      'soil_temperature_10cm_mean',
      'soil_temperature_30cm_mean',
      'soil_moisture_0_to_7cm_mean',
      'soil_moisture_7_to_28cm_mean',
      'soil_moisture_28_to_100cm_mean',
    ])
    expect(panelColumns(weatherPanels({ hourly: true }))).toContain('air_temperature')
    expect(panelColumns(weatherPanels({ hourly: true }))).not.toContain('air_temperature_max')
  })

  it('leaves out a panel with no values (the hourly fixture has no soil)', () => {
    expect(shownPanels(weatherPanels({ hourly: true }), hours).map((p) => p.key)).toEqual([
      'temperature',
      'precipitation',
      'humidity',
      'wind',
      'sun',
    ])
    expect(shownPanels(weatherPanels({ hourly: false }), days)).toHaveLength(7)
  })
})

describe('panelOption', () => {
  it('converts the stored values at display, so a change of units needs no new request', () => {
    const highs = (o: Option) => o.series.find((s) => s.name === 'High')!.data
    const first = days.days[0].values.air_temperature_max!
    expect(highs(option(panel('temperature')))[0]).toBeCloseTo((first * 9) / 5 + 32, 2)
    expect(
      highs(panelOption(panel('temperature'), days, { units: metric, palette, today }) as unknown as Option)[0],
    ).toBe(first)
    expect(option(panel('temperature')).yAxis[0].name).toBe('°F')
  })

  it('labels freezing in the reader’s units, and marks today', () => {
    const marks = option(panel('temperature')).series[0].markLine!.data
    expect(marks).toMatchObject([
      { xAxis: today, label: { formatter: 'Today' } },
      { yAxis: 32, label: { formatter: 'Freezing (32 °F)' } },
    ])
    const metricMarks = (
      panelOption(panel('temperature'), days, { units: metric, palette, today }) as unknown as Option
    ).series[0].markLine!.data
    expect(metricMarks[1]).toMatchObject({ yAxis: 0, label: { formatter: 'Freezing (0.0 °C)' } })
  })

  it('shades the forecast from today’s partial day and names it', () => {
    const o = option(panel('temperature'))
    const shading = o.series.filter((s) => s.id?.startsWith('shading-'))
    expect(shading).toHaveLength(1)
    const from = days.days.findIndex((day) => day.kind === 'partial')
    expect(shading[0].data[from - 1]).toBeNull()
    expect(shading[0].data[from]).toBe(1)
    expect(o.series[0].markArea).toMatchObject({ label: { formatter: 'Forecast' } })
  })

  it('draws a missing value as a gap and a running total that counts it as no rain', () => {
    const o = option(panel('precipitation'))
    expect(o.grid).toHaveLength(2)
    const bars = o.series.find((s) => s.name === 'Precipitation')!
    const missing = days.days.findIndex((day) => day.values.precipitation_sum === null)
    expect(bars.type).toBe('bar')
    expect(bars.data[missing]).toBeNull()
    const total = o.series.find((s) => s.name === 'Precipitation total')!.data as number[]
    expect(total[missing]).toBe(total[missing - 1])
    expect(total.at(-1)).toBeCloseTo(
      days.days.reduce((sum, day) => sum + (day.values.precipitation_sum ?? 0), 0) / 25.4,
      1,
    )
  })

  it('puts a related measure in its own unit in a grid below, never on a second axis of the same grid', () => {
    const o = option(panel('humidity'))
    expect(o.grid).toHaveLength(2)
    const dew = o.series.find((s) => s.name === 'Dew point')!
    expect(dew.xAxisIndex).toBe(1)
    expect(o.yAxis[0].name).toBe('%')
    expect(o.yAxis[1].name).toBe('Dew point (°F)')
  })

  it('draws a smoothing window over the values, which fade', () => {
    const o = option(panel('temperature'), days, { roll: 7 })
    const rolled = o.series.find((s) => s.name === 'High, 7-day mean')!
    expect(rolled.data[0]).toBeCloseTo((days.days[0].values.air_temperature_max_7d! * 9) / 5 + 32, 2)
    expect(o.series.find((s) => s.name === 'High')!.lineStyle!.opacity).toBe(0.35)
    expect(option(panel('precipitation'), days, { roll: 7 }).legend!.data).toContain('Precipitation, 7-day total')
    // A window the table doesn't hold isn't drawn
    expect(option(panel('temperature'), days, { roll: 14 }).series.some((s) => s.name.includes('14-day'))).toBe(false)
  })

  it('draws estimated values hollow', () => {
    const table: Table = {
      ...days,
      days: days.days.map((day, i) => (i === 2 ? { ...day, estimated: new Set(['air_temperature_max']) } : day)),
    }
    const highs = option(panel('temperature'), table).series.find((s) => s.name === 'High')!.data
    expect(highs[2]).toMatchObject({ symbol: 'emptyCircle' })
    expect(typeof highs[1]).toBe('number')
  })

  it('shows hours on the location’s clock, and a Now line at the latest observed hour', () => {
    const o = option(panel('temperature', true), hours)
    const latest = hours.days.findLast((day) => day.kind === 'observed')!.date
    expect(o.series[0].markLine!.data[0]).toMatchObject({ xAxis: latest, label: { formatter: 'Now' } })
    const html = o.tooltip.formatter([
      { dataIndex: 20, seriesIndex: 0, seriesName: 'Temperature', marker: '', value: 35.6 },
    ])
    expect(html).toContain('Nov 25, 2 p.m. CST')
    expect(html).toContain('36 °F') // °F to whole degrees
  })

  it('labels a long run of hours once a day, at local midnight', () => {
    const start = Date.parse('2026-11-20T00:00Z')
    const long: Table = {
      ...hours,
      days: Array.from({ length: 100 }, (_, i) => ({
        date: new Date(start + i * 3_600_000).toISOString().replace(':00.000Z', 'Z'),
        kind: 'observed' as const,
        values: { air_temperature: 1 },
        estimated: new Set<string>(),
        missing: new Set<string>(),
      })),
    }
    const axis = (
      option(panel('temperature', true), long) as unknown as {
        xAxis: { axisLabel: { interval: (i: number, d: string) => boolean } }[]
      }
    ).xAxis[0].axisLabel
    const shown = long.days.filter((day, i) => axis.interval(i, day.date)).map((day) => day.date)
    expect(shown).toEqual(['2026-11-20T06:00Z', '2026-11-21T06:00Z', '2026-11-22T06:00Z', '2026-11-23T06:00Z'])
  })

  it('says Missing in the tooltip where there is no value, and which days are forecast', () => {
    const o = option(panel('precipitation'))
    const missing = days.days.findIndex((day) => day.values.precipitation_sum === null)
    const html = o.tooltip.formatter([
      { dataIndex: missing, seriesIndex: 0, seriesName: 'Precipitation', marker: '', value: null },
    ])
    expect(html).toContain('Missing')
    expect(html).toContain('(today, partly forecast)')
  })
})

describe('panelSummary', () => {
  it('gives the highs and lows with their dates, and counts missing days', () => {
    const text = panelSummary(panel('temperature'), days, us)
    expect(text).toMatch(/^From Wed, Nov 4 to .+\./)
    expect(text).toMatch(/High: highest \d+ °F on \w{3}, \w{3} \d+, lowest \d+ °F on/)
    const rain = panelSummary(panel('precipitation'), days, us)
    expect(rain).toMatch(/Precipitation: [\d.]+ in observed, [\d.]+ in forecast\./)
    // Today's partial day counts as forecast, so its gap isn't an observed day missing
    expect(rain).not.toContain('missing')
  })

  it('says how many observed days are estimated or missing (D45)', () => {
    const table: Table = {
      ...days,
      days: days.days.map((day, i) =>
        i < 2
          ? { ...day, estimated: new Set(['air_temperature_max']) }
          : i === 3
            ? {
                ...day,
                values: { ...day.values, air_temperature_min: null },
                missing: new Set(['air_temperature_min']),
              }
            : day,
      ),
    }
    const text = panelSummary(panel('temperature'), table, us)
    expect(text).toContain('High includes 2 days estimated.')
    expect(text).toContain('Low is missing on 1 day.')
  })

  it('says when there is nothing to summarize', () => {
    expect(panelSummary(panel('temperature'), { ...days, days: [] }, us)).toBe('No values for these days yet.')
  })
})

describe('panelTable and panelCsvRows', () => {
  it('lists each measure with its unit, newest first, the forecast flagged', () => {
    const table = panelTable(panel('humidity'), days, us)
    expect(table.columns).toEqual(['Mean humidity (%)', 'Lowest humidity (%)', 'Dew point (°F)'])
    expect(table.rows[0].date).toBe(days.days.at(-1)!.date)
    expect(table.rows[0].forecast).toBe(true)
    expect(table.rows.at(-1)!.forecast).toBe(false)
  })

  it('adds the smoothing column shown, and marks estimated values', () => {
    const marked: Table = {
      ...days,
      days: days.days.map((day) => ({ ...day, estimated: new Set(['air_temperature_max']) })),
    }
    const table = panelTable(panel('temperature'), marked, metric, 7)
    expect(table.columns.slice(0, 2)).toEqual(['High (°C)', 'High, 7-day mean (°C)'])
    expect(table.rows.at(-1)!.values[0]).toMatch(/ \(estimated\)$/)
  })

  it('heads hourly rows with their hour', () => {
    const table = panelTable(panel('temperature', true), hours, us)
    expect(table.rows.at(-1)!.label).toBe('Nov 24, 6 p.m. CST')
  })

  it('writes a CSV oldest first with the kind of each row, a missing value blank', () => {
    const rows = panelCsvRows(panel('precipitation'), days, metric)
    expect(rows[0]).toEqual(['Date', 'Kind', 'Precipitation (mm)'])
    expect(rows[1][0]).toBe('2026-11-04')
    expect(rows.find((row) => row[1] === 'partial')![2]).toBeNull()
    expect(panelCsvRows(panel('temperature', true), hours, us)[0][0]).toBe('Time (UTC)')
  })
})

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
