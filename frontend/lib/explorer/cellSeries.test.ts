import { describe, expect, it } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import { defaults } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import { readSeries, seriesRequest } from './cellSeries'
import { type ExplorerView, tileRequest, VIEW_FIELDS } from './view'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })
const AT = { lat: 43.07311, lng: -89.40123 }

function both(changes: Partial<ExplorerView>, id: string) {
  const l = layer(id)
  const v = view(changes)
  const tiles = tileRequest(v, l)!
  return { tiles, series: seriesRequest(v, l, tiles, AT)! }
}

describe('the cell panel’s series sends the map’s settings', () => {
  it('in the same units, at the clicked point', () => {
    const { tiles, series } = both({ date: '2026-07-08' }, 'air_temperature_max')
    expect(series.params).toMatchObject({ lat: 43.0731, lng: -89.4012, units: tiles.params.units })
    expect(series).toMatchObject({
      path: '/weather/daily',
      column: 'air_temperature_max',
      from: '2026-06-25',
      to: '2026-07-08',
    })
  })

  it('runs through the forecast from the latest day', () => {
    const { series } = both({}, 'air_temperature_max')
    expect(series.params.end).toBeNull()
    expect(series.to).toBeNull()
  })

  it('with the map’s smoothing', () => {
    const { tiles, series } = both({ date: '2026-07-08', roll: 14, align: 'centered' }, 'precipitation_sum')
    expect(series.params.roll).toBe(tiles.params.roll)
    expect(series.params.roll_align).toBe(tiles.params.roll_align)
    expect(series.column).toBe('precipitation_sum_14d')
  })

  it('with the map’s degree-day setting, from its January 1 or biofix', () => {
    const { tiles, series } = both(
      { span: 'season', dd: 'sine_48_86', biofix: '04-15', date: '2026-07-08' },
      'degree_days',
    )
    expect(series.params.dd).toBe(tiles.params.dd)
    expect(tiles.time).toBe(`${series.from}..2026-07-08`)
    expect(series).toMatchObject({ path: '/degree-days', column: 'dd_sine_48_86_cum', from: '2026-04-15' })
  })

  it('with the map’s planting tier (mid by default, none as no planting) and options', () => {
    const mold = both({ date: '2026-07-08', opts: ['irrigation:irrigated'], output: 'probability' }, 'white-mold')
    expect(mold.series.params).toMatchObject({ planting_date: 'mid', irrigation: mold.tiles.params.irrigation })
    expect(mold.series.column).toBe('probability')
    const late = both({ date: '2026-07-08', planting: 'late' }, 'tar-spot')
    expect(late.series.params.planting_date).toBe('late')
    expect(late.series.column).toBe('risk_level')
    const none = both({ date: '2026-07-08', planting: 'none' }, 'tar-spot')
    expect(none.series.params.planting_date).toBeUndefined()
    expect(both({ date: '2026-07-08' }, 'apple-scab').series.params.planting_date).toBeUndefined()
  })

  it('hours around an hourly map’s hour', () => {
    const { series } = both({ hour: '2026-07-08T15' }, 'air_temperature_hourly')
    expect(series).toMatchObject({ path: '/weather/hourly', column: 'air_temperature' })
    expect(series.params).toMatchObject({ start: '2026-07-07T03', end: '2026-07-09T03' })
  })

  it('each day of a running total', () => {
    expect(both({}, 'precipitation_total').series).toMatchObject({ column: 'precipitation_sum', daily: true })
    const chill = layer('chill_portions')
    expect(seriesRequest(view(), chill, tileRequest(view(), chill)!, AT)).toBeNull()
  })
})

describe('readSeries', () => {
  it('cuts the answer to the days asked and keeps the kinds, unit and level names', () => {
    const { series } = both({ date: '2026-07-03' }, 'tar-spot')
    const body = {
      meta: { units: { probability: '%' }, warnings: ['A warning.'] },
      data: {
        date: ['2026-06-19', '2026-06-20', '2026-07-03', '2026-07-04'],
        kind: ['observed', 'observed', 'observed', 'forecast'],
        risk_level: [0, 1, 2, 3],
        risk_label: ['Very low', 'Low', 'Moderate', 'High'],
      },
    }
    expect(readSeries(series, body)).toEqual({
      times: ['2026-06-20', '2026-07-03'],
      values: [1, 2],
      kinds: ['observed', 'observed'],
      unit: '',
      labels: ['Low', 'Moderate'],
      warnings: ['A warning.'],
    })
  })
})
