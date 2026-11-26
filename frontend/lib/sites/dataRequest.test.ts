import { describe, expect, it } from 'vitest'

import variablesAnswer from '@/test/fixtures/site/variables.json'
import type { VariableInfo } from '@/types/api'

import {
  addsUp,
  dataRequest,
  downloadBytes,
  formatBytes,
  MAX_POINTS,
  MAX_ROWS,
  pointsRequest,
  sizeProblem,
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

describe('several locations (/data)', () => {
  const two = [
    { lat: 43.07, lng: -89.4 },
    { lat: 44.5, lng: -89.5 },
  ]

  it('asks for them as points, and one as lat and lng', () => {
    const built = pointsRequest(daily, two, today)
    expect(built.params).toMatchObject({ lat: null, lng: null, points: '43.07,-89.4;44.5,-89.5' })
    expect(built.url).toContain('points=43.07%2C-89.4%3B44.5%2C-89.5')
    expect(pointsRequest(daily, [two[0]], today).url).toContain('lat=43.07&lng=-89.4')
  })

  it('refuses more locations, or more rows, than the API takes', () => {
    const many = Array.from({ length: MAX_POINTS + 1 }, (_, k) => ({ lat: 43 + k / 100, lng: -89 }))
    expect(sizeProblem(daily, today, many.length)).toBe(
      'You chose 51 locations; a request can include up to 50. Remove some, or download them in several requests.',
    )
    expect(sizeProblem(daily, today, 0)).toBe('Choose at least one location.')
    // 50 locations × 2,200 days is 110,000 rows: the API's "This request would return 110,000 rows (50 locations)"
    const long = { ...daily, start: '2020-01-01', end: '2026-01-08', forecast: false }
    expect(sizeProblem(long, today, 50)).toBe(
      `This request would return 110,000 rows (50 locations); a request can return up to ${MAX_ROWS.toLocaleString('en-US')}. Choose fewer locations or a shorter period.`,
    )
    expect(sizeProblem(long, today, 45)).toBeNull()
    // Totals count the days read too
    expect(sizeProblem({ ...long, kind: 'totals' }, today, 50)).toMatch(/^This request would return 110,000 rows/)
  })

  it('says about how large a download is', () => {
    // A year of three daily variables at one location: the API's CSV was 14,644 bytes
    const year = { ...daily, start: '2025-01-01', end: '2025-12-31', forecast: false }
    const bytes = downloadBytes(year, today, 1)!
    expect(bytes).toBeGreaterThan(12_000)
    expect(bytes).toBeLessThan(18_000)
    expect(downloadBytes(year, today, 2)! / bytes).toBeGreaterThan(1.8)
    expect(formatBytes(bytes)).toMatch(/^about 1\d KB$/)
    expect(formatBytes(2_480_000)).toBe('about 2.5 MB')
    expect(formatBytes(500)).toBe('under 1 KB')
  })
})
