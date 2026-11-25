import { describe, expect, it } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import { defaults, fromQuery, toQuery } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import {
  biofixDate,
  type ExplorerView,
  firstView,
  isForecast,
  timeIsForecast,
  spansFor,
  stepDay,
  stepHour,
  stepperWhen,
  stepTo,
  tileRequest,
  VIEW_FIELDS,
} from './view'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })

describe('the first visit', () => {
  it('shows degree days since January 1 in the growing season, the daily low otherwise', () => {
    expect(firstView('2026-04-01')).toEqual({ layer: 'degree_days', dd: 'modified_50_86', span: 'season' })
    expect(firstView('2026-10-31').layer).toBe('degree_days')
    expect(firstView('2026-11-25')).toEqual({ layer: 'air_temperature_min', span: 'day' })
    expect(firstView('2027-03-31').layer).toBe('air_temperature_min')
  })
})

describe('the Share link', () => {
  it('leaves defaults out and reads back what it wrote', () => {
    const shown = view({
      layer: 'late-blight-dsv',
      date: '2026-07-08',
      planting: 'early',
      opts: ['irrigation:irrigated'],
      at: { lat: 43.0731, lng: -89.4012 },
    })
    const query = toQuery(VIEW_FIELDS, shown).toString()
    expect(query).toBe(
      'layer=late-blight-dsv&date=2026-07-08&planting=early&opts=irrigation%3Airrigated&at=43.0731%2C-89.4012',
    )
    expect({ ...defaults(VIEW_FIELDS), ...fromQuery(VIEW_FIELDS, query) }).toEqual(shown)
  })

  it('drops settings it can’t read', () => {
    expect(fromQuery(VIEW_FIELDS, 'span=week&dd=hot&hour=noon&layer=x')).toEqual({ layer: 'x' })
  })
})

describe('tileRequest', () => {
  it('shows a day, or the latest', () => {
    expect(tileRequest(view(), layer('air_temperature_min'))).toEqual({
      layer: 'air_temperature_min',
      time: 'latest',
      stat: null,
      params: { units: 'us' },
    })
    expect(tileRequest(view({ date: '2026-07-08' }), layer('air_temperature_min'))?.time).toBe('2026-07-08')
  })

  it('smooths a day over a window, only for daily layers that take one', () => {
    const smoothed = tileRequest(view({ roll: 7, align: 'centered' }), layer('precipitation_sum'))
    expect(smoothed?.params).toEqual({ units: 'us', roll: 7, roll_align: 'centered' })
    expect(tileRequest(view({ roll: 7 }), layer('precipitation_total'))?.params).toEqual({ units: 'us' })
    expect(tileRequest(view({ roll: 7, span: 'range' }), layer('precipitation_sum'))?.params.roll).toBeUndefined()
  })

  it('combines a range by its statistic, 14 days by default, a sum where values add', () => {
    const rain = tileRequest(view({ span: 'range', date: '2026-07-14' }), layer('precipitation_sum'))
    expect(rain).toMatchObject({ time: '2026-07-01..2026-07-14', stat: 'sum' })
    const highs = tileRequest(
      view({ span: 'range', date: '2026-07-14', start: '2026-07-10', stat: 'sum' }),
      layer('air_temperature_max'),
    )
    expect(highs).toMatchObject({ time: '2026-07-10..2026-07-14', stat: 'mean' })
  })

  it('ends a range on the latest observed day when no date is given', () => {
    const latest = layer('precipitation_sum').range.last
    expect(tileRequest(view({ span: 'range' }), layer('precipitation_sum'))?.time.endsWith(`..${latest}`)).toBe(true)
  })

  it('sums degree days since January 1 or the biofix, written in °F', () => {
    const dd = layer('degree_days')
    expect(tileRequest(view({ span: 'season', dd: 'sine_50_86', date: '2026-07-08' }), dd)).toEqual({
      layer: 'degree_days',
      time: '2026-01-01..2026-07-08',
      stat: 'sum',
      params: { units: 'us', dd: 'sine_50_86' },
    })
    const fromBiofix = tileRequest(view({ span: 'season', biofix: '04-15', date: '2026-03-01' }), dd)
    expect(fromBiofix?.time).toBe('2025-04-15..2026-03-01')
    expect(fromBiofix?.params.dd).toBe('modified_50_86')
  })

  it('gives a model its output, planting tier and options, and nothing it doesn’t take', () => {
    const mold = tileRequest(
      view({ output: 'probability', planting: 'late', opts: ['irrigation:irrigated', 'clock:calendar'] }),
      layer('white-mold'),
    )
    expect(mold?.params).toEqual({ units: 'us', output: 'probability', planting: 'late', irrigation: 'irrigated' })
    const scab = tileRequest(view({ output: 'nonsense', planting: 'late' }), layer('apple-scab'))
    expect(scab?.params).toEqual({ units: 'us', output: null })
  })

  it('shows an hour of an hourly layer', () => {
    const hourly = layer('air_temperature_hourly')
    expect(spansFor(hourly)).toEqual(['hour'])
    expect(tileRequest(view({ span: 'range', hour: '2026-07-08T15' }), hourly)?.time).toBe('2026-07-08T15')
  })
})

describe('time', () => {
  const daily = layer('air_temperature_min')

  it('offers each layer the spans it can show', () => {
    expect(spansFor(daily)).toEqual(['day', 'range'])
    expect(spansFor(layer('precipitation_sum'))).toEqual(['day', 'range', 'season'])
    expect(spansFor(layer('dd_modified_50_86'))).toEqual(['day'])
    expect(spansFor(layer('tar-spot'))).toEqual(['day', 'range'])
  })

  it('steps days within the archive and the forecast', () => {
    const { first, forecast_through } = daily.range
    expect(stepDay('2026-07-08', 7, daily)).toBe('2026-07-15')
    expect(stepDay(first!, -1, daily)).toBe(first)
    expect(stepDay(forecast_through!, 7, daily)).toBe(forecast_through)
  })

  it('steps hours in UTC across days', () => {
    const hourly = layer('air_temperature_hourly')
    expect(stepHour('2026-07-08T22', 6, hourly)).toBe('2026-07-09T04')
    expect(stepHour('2016-01-01T00', -1, hourly)).toBe('2016-01-01T00')
  })

  it('knows a forecast day from an observed one', () => {
    const last = daily.range.last!
    expect(isForecast(last, daily)).toBe(false)
    expect(isForecast(stepDay(last, 1, daily), daily)).toBe(true)
    expect(timeIsForecast('latest', daily)).toBe(false)
    expect(timeIsForecast(`2026-11-01..${stepDay(last, 2, daily)}`, daily)).toBe(true)
    expect(timeIsForecast(`2026-11-01..${last}`, daily)).toBe(false)
  })

  it('places a biofix on or before the end', () => {
    expect(biofixDate('04-15', '2026-07-08')).toBe('2026-04-15')
    expect(biofixDate('11-01', '2026-02-01')).toBe('2025-11-01')
    expect(biofixDate('2026-05-02', '2026-07-08')).toBe('2026-05-02')
  })
})

describe('the phone’s stepper', () => {
  it('steps the day, keeping a range’s length, or the hour', () => {
    const daily = layer('air_temperature_min')
    const ranged = view({ layer: daily.id, span: 'range', date: '2026-07-14', start: '2026-07-08' })
    expect(stepperWhen(ranged, daily, '2026-11-25')).toBe('2026-07-14')
    expect(stepTo(ranged, daily, '2026-07-15')).toEqual({ date: '2026-07-15', start: '2026-07-09' })
    expect(stepTo(view({ layer: daily.id }), daily, '2026-07-15')).toEqual({ date: '2026-07-15' })
    const hourly = layer('air_temperature_hourly')
    const hour = view({ layer: hourly.id, span: 'hour', hour: '2026-07-08T15' })
    expect(stepperWhen(hour, hourly, '2026-11-25')).toBe('2026-07-08T15')
    expect(stepTo(hour, hourly, '2026-07-08T16')).toEqual({ hour: '2026-07-08T16' })
  })
})

describe('the overlay in a Share link', () => {
  it('reads only the overlays the map has', () => {
    expect(fromQuery(VIEW_FIELDS, 'overlay=radar').overlay).toBe('radar')
    expect(fromQuery(VIEW_FIELDS, 'overlay=nothing').overlay).toBeUndefined()
    expect(toQuery(VIEW_FIELDS, view({ overlay: 'drought' })).get('overlay')).toBe('drought')
  })
})
