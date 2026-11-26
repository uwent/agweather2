import { describe, expect, it } from 'vitest'

import variablesAnswer from '@/test/fixtures/site/variables.json'
import type { VariableInfo } from '@/types/api'

import {
  addsUp,
  dataRequest,
  groupVariables,
  MAX_HOURS,
  OTHER_GROUP,
  variablesFor,
  type DataChoice,
} from './dataRequest'

const variables = variablesAnswer.data as VariableInfo[]
const today = '2026-11-25'
const daily: DataChoice = {
  kind: 'daily',
  vars: ['air_temperature_min', 'precipitation_sum'],
  start: '2026-01-01',
  end: '2026-11-25',
  forecast: true,
  units: 'us',
  format: 'csv',
  dd: 'modified_50_86',
  biofix: '',
  model: 'late-blight-dsv',
}

describe('the variables', () => {
  it('offers each kind its own: hours, days, and only the days that add up for totals', () => {
    expect(variablesFor('hourly', variables).every((v) => v.kind === 'hourly')).toBe(true)
    const totals = variablesFor('totals', variables).map((v) => v.name)
    expect(totals).toContain('precipitation_sum')
    expect(totals).toContain('hours_rh_over_90')
    expect(totals).toContain('water_balance')
    expect(totals).toContain('utah_chill_units')
    expect(totals).not.toContain('air_temperature_max')
    expect(addsUp({ name: 'et0_sum', statistic: 'sum', unit: 'mm' })).toBe(true)
    expect(variablesFor('model', variables)).toEqual([])
  })

  it('groups them by what they measure, temperature first, each variable once', () => {
    const shown = variablesFor('daily', variables)
    const groups = groupVariables(shown)
    expect(groups[0].label).toBe('Temperature')
    expect(groups[0].variables.map((v) => v.name)).toContain('air_temperature_max')
    const humidity = groups.find((g) => g.label === 'Humidity')!.variables.map((v) => v.name)
    expect(humidity).toContain('hours_rh_over_90')
    expect(humidity).toContain('dew_point_depression_mean')
    expect(groups.find((g) => g.label === OTHER_GROUP)!.variables.map((v) => v.name)).toContain('scab_infection')
    expect(groups.flatMap((g) => g.variables).length).toBe(shown.length)
  })
})

describe('the request', () => {
  it('builds the URL a script can fetch, through the forecast by default', () => {
    const built = dataRequest(daily, 44.12, -89.52, today)
    expect(built.problem).toBeNull()
    expect(built.url).toBe(
      '/api/v2/weather/daily?format=csv&lat=44.12&lng=-89.52&start=2026-01-01&units=us&vars=air_temperature_min%2Cprecipitation_sum',
    )
  })

  it('stops at the end date, and hours at its last hour', () => {
    const built = dataRequest({ ...daily, kind: 'hourly', forecast: false, start: '2026-11-18' }, 44.12, -89.52, today)
    expect(built.params).toMatchObject({ end: '2026-11-25T23', forecast: false })
    expect(built.path).toBe('/weather/hourly')
  })

  it('asks for degree days and a model run with their own parameters', () => {
    const dd = dataRequest(
      { ...daily, kind: 'degree-days', dd: 'modified_50_86, sine_41', biofix: '2026-05-01' },
      44.12,
      -89.52,
      today,
    )
    expect(dd.path).toBe('/degree-days')
    expect(dd.params).toMatchObject({ dd: 'modified_50_86,sine_41', biofix: '2026-05-01' })
    expect(dd.params.vars).toBeUndefined()
    const run = dataRequest({ ...daily, kind: 'model', format: 'json' }, 44.12, -89.52, today)
    expect(run.url).toBe(
      '/api/v2/models/late-blight-dsv/run?format=json&lat=44.12&lng=-89.52&start=2026-01-01&units=us',
    )
  })

  it('says before it fails when the request is larger than the API takes', () => {
    const hours = dataRequest({ ...daily, kind: 'hourly', start: '2024-01-01' }, 44.12, -89.52, today)
    expect(hours.problem).toMatch(
      /^This request covers 25,\d{3} hours \(Jan 1, 2024 to Dec 11, 2026\); a request can include up to 17,568, about two years\./,
    )
    expect(MAX_HOURS).toBe(17_568)
    const days = dataRequest(
      { ...daily, start: '2010-01-01', end: '2026-01-01', forecast: false },
      44.12,
      -89.52,
      today,
    )
    expect(days.problem).toMatch(/^This request covers 5,845 days; a request can include up to 3,660/)
    const backwards = dataRequest({ ...daily, end: '2025-01-01', forecast: false }, 44.12, -89.52, today)
    expect(backwards.problem).toBe(
      'The end date is before the start date. Choose an end date on or after the start date.',
    )
    expect(dataRequest({ ...daily, vars: [] }, 44.12, -89.52, today).problem).toBe('Choose at least one variable.')
  })
})
