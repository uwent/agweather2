import { describe, expect, it } from 'vitest'

import type { TableResponse } from '@/types/api'
import daily from '@/test/fixtures/site/daily.json'
import hourly from '@/test/fixtures/site/hourly.json'
import modelRun from '@/test/fixtures/site/model-run.json'

import { flagCounts, isForecast, tableRows, unitSymbol } from './tableRows'

describe('unitSymbol', () => {
  it('names the unit of each label the API gives', () => {
    expect(unitSymbol('°C')).toBe('degC')
    expect(unitSymbol('°F')).toBe('degF')
    expect(unitSymbol('km/h')).toBe('km_h')
    expect(unitSymbol('mm')).toBe('mm')
    expect(unitSymbol('in')).toBe('in')
    expect(unitSymbol('MJ/m²')).toBe('MJ_m2')
    expect(unitSymbol('m³/m³')).toBe('m3_m3')
    expect(unitSymbol('%')).toBe('percent')
    expect(unitSymbol('h')).toBe('hour')
    expect(unitSymbol('')).toBeNull()
    expect(unitSymbol('furlongs')).toBeNull()
  })

  it('tells a difference of temperatures from a temperature by its column', () => {
    expect(unitSymbol('°C', 'dew_point_depression_mean')).toBe('delta_degC')
    expect(unitSymbol('°F', 'dew_point_depression_min')).toBe('delta_degF')
  })
})

describe('tableRows', () => {
  it("reads a daily answer's rows with their kinds and units, dropping the days past the forecast", () => {
    const table = tableRows(daily as TableResponse)
    expect(table.hourly).toBe(false)
    expect(table.days[0].date).toBe('2026-11-04')
    expect(table.days.map((day) => day.kind)).toContain('partial')
    expect(table.days.at(-1)!.kind).toBe('forecast')
    expect(table.days.every((day) => day.kind !== null)).toBe(true)
    expect(table.units.air_temperature_max).toBe('degC')
    expect(table.units.air_temperature_max_7d).toBe('degC')
    expect(table.units.wind_speed_mean).toBe('km_h')
    expect(table.units.soil_moisture_0_to_7cm_mean).toBe('m3_m3')
    expect(table.location?.county).toBe('Waushara County')
    expect(table.days[0].values).not.toHaveProperty('kind')
  })

  it('marks a null as missing', () => {
    const table = tableRows(daily as TableResponse)
    const today = table.days.find((day) => day.kind === 'partial')!
    expect(today.values.precipitation_sum).toBeNull()
    expect(today.missing.has('precipitation_sum')).toBe(true)
    expect(flagCounts(table.days, 'precipitation_sum').missing).toBe(1)
  })

  it("reads hours, and a model run's estimated flags", () => {
    const hours = tableRows(hourly as TableResponse)
    expect(hours.hourly).toBe(true)
    expect(hours.days[0].date).toBe('2026-11-25T00:00Z')

    const run = tableRows(modelRun as TableResponse)
    expect(run.units.temperature_mean_rh_over_90_from_6pm).toBe('degC')
    expect(run.days[0].values).not.toHaveProperty('temperature_mean_rh_over_90_from_6pm_estimated')
    expect(run.days[0].values).not.toHaveProperty('risk_label') // text
  })

  it('takes `_estimated` and `_missing` columns as flags on their column', () => {
    const table = tableRows({
      meta: { units: { dsv: '' }, warnings: ['A note.'] } as unknown as TableResponse['meta'],
      data: {
        date: ['2026-07-01', '2026-07-02', '2026-07-03'],
        kind: ['observed', 'forecast', 'projection'],
        dsv: [1, 2, null],
        dsv_estimated: [false, true, false],
        dsv_missing: [true, false, false],
      },
    })
    expect(table.days.map((day) => [...day.estimated])).toEqual([[], ['dsv'], []])
    expect(table.days.map((day) => [...day.missing])).toEqual([['dsv'], [], ['dsv']])
    expect(flagCounts(table.days, 'dsv')).toEqual({ estimated: 1, missing: 2 })
    expect(table.warnings).toEqual(['A note.'])
    expect(table.days.map(isForecast)).toEqual([false, true, false])
  })
})
