import { describe, expect, it } from 'vitest'

import type { DataAreas, DataLimits, GridProjection } from '@/types'

import {
  boxArea,
  gridEstimate,
  gridRequest,
  lambert,
  multiples,
  parseBox,
  windowExtent,
  type GridChoice,
  type GridContext,
} from './gridSize'

// The server's props (web.datapage) and the API's answers, recorded from the development archive over Wisconsin
// (2026-11-25): its window, the state of Wisconsin and Dane County as /grids measures them
const projection: GridProjection = {
  lon0: -95,
  lat1: 25,
  radius: 6371200,
  x0: -3271147.2882942683,
  y0: -263797.50271268317,
  dx: 2539.703,
}
const limits: DataLimits = {
  text_values: 2_000_000,
  file_values: 22_000_000,
  map_days: 366,
  map_hours: 744,
  stride: 50,
  res: 0.025,
}
const areas: DataAreas = {
  window: [878, 1123, 1352, 1588],
  states: [{ id: 'WI', name: 'Wisconsin', state: 'WI', j0: 886, j1: 1105, i0: 1358, i1: 1562, cells: 27218 }],
  counties: [{ id: '55025', name: 'Dane County', state: 'WI', j0: 903, j1: 924, i0: 1462, i1: 1491, cells: 547 }],
}
const ctx: GridContext = { limits, projection, areas }
const archive = { j0: 878, j1: 1123, i0: 1352, i1: 1588 }

const daily: GridChoice = {
  layer: { id: 'air_temperature_max', time_axis: 'day', stats: ['mean', 'min', 'max'] },
  span: 'day',
  start: '2025-06-01',
  end: '2025-06-01',
  stat: null,
  area: { kind: 'whole' },
  clip: false,
  format: 'netcdf',
  grid: 'native',
  res: 0.1,
  stride: 1,
  units: 'us',
}

describe('the grid', () => {
  it('places cells as agdata.grid.NDFD does', () => {
    // NDFD.latlon(913, 1477), Madison's cell, and back
    const { lat, lng } = lambert(projection).latLng(913, 1477)
    expect(lat).toBeCloseTo(43.0706, 4)
    expect(lng).toBeCloseTo(-89.3973, 4)
    const { j, i } = lambert(projection).index(lat, lng)
    expect(j).toBeCloseTo(913, 6)
    expect(i).toBeCloseTo(1477, 6)
  })

  it('finds a box’s cells as the API does', () => {
    // bbox=43,-90,44,-89: window [909, 957, 1456, 1491], and 1,555 cells with clip=true
    const found = boxArea(projection, archive, { south: 43, west: -90, north: 44, east: -89 })
    expect(found).toEqual({ window: { j0: 909, j1: 957, i0: 1456, i1: 1491 }, cells: 1555 })
    expect(boxArea(projection, archive, { south: 30, west: -100, north: 31, east: -99 })).toBeNull()
  })

  it('counts a latitude and longitude grid’s points as the API does', () => {
    // The whole window at 0.1°: shape [54, 74]; Dane County's rectangle at 0.1°: [4, 9]
    const whole = windowExtent(projection, archive)
    expect([multiples(whole.south, whole.north, 0.1), multiples(whole.west, whole.east, 0.1)]).toEqual([54, 74])
    const dane = windowExtent(projection, { j0: 903, j1: 924, i0: 1462, i1: 1491 })
    expect([multiples(dane.south, dane.north, 0.1), multiples(dane.west, dane.east, 0.1)]).toEqual([4, 9])
  })
})

describe('the estimate', () => {
  it('takes what the API takes: a year of days over the whole area as NetCDF', () => {
    const year = gridEstimate({ ...daily, span: 'range', start: '2025-01-01', end: '2025-12-31' }, ctx)!
    expect(year.values).toBe(365 * 57_820)
    expect(year.problem).toBeNull()
  })

  it('refuses what the API refuses, with its numbers', () => {
    // The API: "This request has 27,753,600 values (480 steps × 57,820 cells); a file holds up to 22,000,000."
    const hours = gridEstimate(
      {
        ...daily,
        layer: { id: 'air_temperature_hourly', time_axis: 'hour', stats: [] },
        span: 'range',
        start: '2025-07-01',
        end: '2025-07-20',
      },
      ctx,
    )!
    expect(hours.steps).toBe(480)
    expect(hours.problem).toMatch(/^This request has about 27,753,600 values \(480 maps × 57,820 cells\)/)
    expect(gridRequest({ ...daily, layer: { id: 'x', time_axis: 'hour', stats: [] }, span: 'range', start: '2025-07-01', end: '2025-07-20' }).params).toMatchObject({
      start: '2025-07-01T07:00Z',
      end: '2025-07-21T06:00Z',
    })
    // The API: "This request has 2,680,560 values (60 steps × 44,676 cells); JSON and CSV hold up to 2,000,000."
    const csv = gridEstimate(
      { ...daily, span: 'range', start: '2025-06-01', end: '2025-07-30', area: { kind: 'state', id: 'WI' }, format: 'csv' },
      ctx,
    )!
    expect(csv.problem).toMatch(/^This request has about 2,680,560 values \(60 maps × 44,676 cells\); JSON and CSV/)
    // The same as NetCDF fits, and so does the CSV with only the state's cells or every third
    const asFile = { ...daily, span: 'range' as const, start: '2025-06-01', end: '2025-07-30', area: { kind: 'state' as const, id: 'WI' } }
    expect(gridEstimate(asFile, ctx)!.problem).toBeNull()
    expect(gridEstimate({ ...asFile, format: 'csv', clip: true }, ctx)!.values).toBe(60 * 27_218)
    // stride=3 with clip: the API counts 3,024 cells
    expect(gridEstimate({ ...asFile, format: 'csv', clip: true, stride: 3 }, ctx)!.values).toBe(60 * 3024)
  })

  it('combines a range into one map with a statistic, within a map’s longest range', () => {
    const mean = { ...daily, span: 'range' as const, start: '2025-01-01', end: '2025-12-31', stat: 'mean', format: 'csv' as const }
    expect(gridEstimate(mean, ctx)).toMatchObject({ steps: 1, values: 57_820, problem: null })
    const long = gridEstimate({ ...mean, start: '2024-01-01' }, ctx)!
    expect(long.problem).toBe(
      'The range is 731 days long; a map covers up to 366, about a year. Choose a shorter range.',
    )
  })

  it('waits for the areas and for a whole box', () => {
    expect(gridEstimate({ ...daily, area: { kind: 'county', id: '55025' } }, { ...ctx, areas: null })).toBeNull()
    expect(gridEstimate({ ...daily, area: { kind: 'box', box: null } }, ctx)).toBeNull()
    const away = { kind: 'box' as const, box: { south: 30, west: -100, north: 31, east: -99 } }
    expect(gridEstimate({ ...daily, area: away }, ctx)!.problem).toBe(
      'The box has no grid cells in the area we cover. Choose a box that overlaps it.',
    )
    expect(parseBox({ south: '43', west: '-90', north: '44', east: '-89' })).toEqual({
      south: 43,
      west: -90,
      north: 44,
      east: -89,
    })
    expect(parseBox({ south: '44', west: '-90', north: '43', east: '-89' })).toBeNull()
  })
})

describe('the request', () => {
  it('asks /grids for the day or range, the area, the grid and the format', () => {
    expect(gridRequest({ ...daily, area: { kind: 'county', id: '55025' }, clip: true, format: 'csv' })).toEqual({
      path: '/grids/air_temperature_max',
      params: { date: '2025-06-01', region: '55025', clip: 'true', units: 'us', format: 'csv' },
    })
    const range = gridRequest({
      ...daily,
      span: 'range',
      end: '2025-06-30',
      stat: 'max',
      area: { kind: 'box', box: { south: 43, west: -90, north: 44, east: -89 } },
      grid: 'latlon',
      res: 0.1,
      units: 'metric',
    })
    expect(range.params).toEqual({
      start: '2025-06-01',
      end: '2025-06-30',
      stat: 'max',
      bbox: '43,-90,44,-89',
      grid: 'latlon',
      res: 0.1,
      units: 'metric',
      format: 'netcdf',
    })
    expect(gridRequest({ ...daily, layer: { id: 'elevation', time_axis: 'none', stats: [] } }).params).toEqual({
      units: 'us',
      format: 'netcdf',
    })
  })
})
