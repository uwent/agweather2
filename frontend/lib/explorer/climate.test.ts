import { describe, expect, it } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import { units as unitsFor } from '@/lib/units'
import { defaults, fromQuery, toQuery } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import { readSeries, seriesRequest } from './cellSeries'
import { climateKinds, climateValueWords, countLabel, countsFor, ddHasNormals, monthDayText, storedDd } from './climate'
import { siteClimatePath } from './links'
import { noYearTimeline, stepNoYear } from './timeline'
import { climateOf, type ExplorerView, spansFor, tileRequest, VIEW_FIELDS } from './view'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })
const US = unitsFor('imperial')
const METRIC = unitsFor('metric')
const STORED = storedDd(LAYERS)
const context = { today: '2026-11-25', stored: STORED }

describe('what Compare with normal offers', () => {
  const kinds = (changes: Partial<ExplorerView>, id: string) => {
    const v = view(changes)
    const l = layer(id)
    return climateKinds({
      layer: l,
      span: spansFor(l).includes(v.span) ? v.span : spansFor(l)[0],
      dd: l.group === 'degree_days' ? (v.dd ?? 'modified_50_86') : null,
      biofix: v.biofix,
      count: v.count,
      period: v.period,
      stored: STORED,
    })
  }

  it('offers a normal and a departure where the layer lists them, a percentile only where it ranks a total', () => {
    expect(kinds({}, 'air_temperature_min')).toEqual(['normal', 'departure'])
    expect(kinds({}, 'precipitation_total')).toEqual(['normal', 'departure', 'percentile'])
    expect(kinds({ period: 'last5' }, 'precipitation_total')).toEqual(['normal', 'departure'])
    expect(kinds({}, 'air_temperature_hourly')).toEqual([])
    expect(kinds({}, 'tar-spot')).toEqual([])
    expect(kinds({}, 'freeze_chance')).toEqual([])
  })

  it('ranks degree days only from January 1, for the two settings with percentile maps', () => {
    expect(kinds({ span: 'season', dd: 'modified_50_86' }, 'degree_days')).toContain('percentile')
    expect(kinds({ span: 'season', dd: 'sine_41_86' }, 'degree_days')).toContain('percentile')
    expect(kinds({ span: 'season', dd: 'sine_50_86' }, 'degree_days')).toEqual(['normal', 'departure'])
    expect(kinds({ span: 'season', biofix: '04-15' }, 'degree_days')).toEqual(['normal', 'departure'])
    expect(kinds({ span: 'day' }, 'degree_days')).toEqual(['normal', 'departure'])
  })

  it('compares degree days only for settings with kept running totals, or a single sine pair of them', () => {
    expect(STORED).toContain('modified_50_86')
    expect(ddHasNormals('sine_50_86', STORED)).toBe(true)
    expect(ddHasNormals('sine_50', STORED)).toBe(true)
    expect(ddHasNormals('sine_47_86', STORED)).toBe(false)
    expect(ddHasNormals('average_50', STORED)).toBe(false)
    expect(kinds({ span: 'season', dd: 'average_50' }, 'degree_days')).toEqual([])
  })

  it('compares a count of days only where its normal is kept, never as a percentile', () => {
    expect(countsFor(layer('air_temperature_min'))).toEqual(['days_below_32', 'days_below_28', 'days_above_70'])
    expect(countsFor(layer('relative_humidity_min'))).toEqual([])
    expect(kinds({ span: 'range', count: 'days_above_90' }, 'air_temperature_max')).toEqual(['normal', 'departure'])
    expect(kinds({ span: 'range', count: 'days_above_95' }, 'air_temperature_max')).toEqual([])
  })
})

describe('the tiles of a climate map', () => {
  it('ask for the comparison and its period, leaving out the defaults', () => {
    const departure = tileRequest(
      view({ climate: 'departure', period: 'last10', date: '2026-11-20' }),
      layer('air_temperature_min'),
      context,
    )
    expect(departure).toEqual({
      layer: 'air_temperature_min',
      time: '2026-11-20',
      stat: null,
      params: { units: 'us', climate: 'departure', period: 'last10' },
    })
    const normal = tileRequest(view({ climate: 'normal' }), layer('precipitation_total'), context)
    expect(normal?.params).toEqual({ units: 'us', climate: 'normal', period: null })
  })

  it('drop a comparison the map can’t show, and combine a compared range only by its total or mean', () => {
    const dd = layer('degree_days')
    const average = tileRequest(view({ climate: 'normal', span: 'season', dd: 'average_50' }), dd, context)
    expect(average?.params.climate).toBeUndefined()
    const ranked = tileRequest(view({ climate: 'percentile', period: 'last5' }), layer('precipitation_total'), context)
    expect(ranked?.params.climate).toBeUndefined()
    const highest = tileRequest(
      view({ climate: 'normal', span: 'range', stat: 'max', date: '2026-07-14' }),
      layer('air_temperature_max'),
      context,
    )
    expect(highest).toMatchObject({ stat: 'mean', params: { climate: 'normal' } })
    expect(climateOf(view({ climate: 'normal' }), layer('air_temperature_hourly'))).toBeNull()
  })

  it('count days on a range in place of a statistic, with or without a comparison', () => {
    const counted = tileRequest(
      view({ span: 'range', date: '2026-07-14', count: 'days_above_86', climate: 'departure' }),
      layer('air_temperature_max'),
      context,
    )
    expect(counted).toEqual({
      layer: 'air_temperature_max',
      time: '2026-07-01..2026-07-14',
      stat: null,
      params: { units: 'us', climate: 'departure', period: null, count: 'days_above_86' },
    })
    // Not on a day, nor a count the layer doesn't keep
    expect(tileRequest(view({ count: 'days_above_86' }), layer('air_temperature_max'))?.params.count).toBeUndefined()
    const other = tileRequest(view({ span: 'range', count: 'days_above_86' }), layer('air_temperature_min'))
    expect(other).toMatchObject({ stat: 'mean' })
    expect(other?.params.count).toBeUndefined()
  })

  it('give a freeze-chance map a day of the year (today without one) and its threshold and period', () => {
    const chance = layer('freeze_chance')
    expect(spansFor(chance)).toEqual(['day'])
    expect(tileRequest(view({ date: '2026-05-01', threshold: 28, period: 'last10' }), chance, context)).toEqual({
      layer: 'freeze_chance',
      time: '2026-05-01',
      stat: null,
      params: { units: 'us', threshold: 28, period: 'last10' },
    })
    expect(tileRequest(view({ threshold: 32 }), chance, context)?.time).toBe('2026-11-25')
    expect(tileRequest(view(), chance)?.time).toBe('latest')
  })

  it('give the freeze dates an output and no time; elevation an output alone', () => {
    const dates = tileRequest(
      view({ output: 'first_fall_p50', threshold: 24, date: '2026-05-01', climate: 'normal' }),
      layer('freeze_dates'),
    )
    expect(dates).toEqual({
      layer: 'freeze_dates',
      time: 'latest',
      stat: null,
      params: { units: 'us', output: 'first_fall_p50', threshold: 24, period: null },
    })
    expect(spansFor(layer('freeze_dates'))).toEqual([])
    expect(tileRequest(view({ output: 'spread', date: '2026-05-01' }), layer('elevation'))).toEqual({
      layer: 'elevation',
      time: 'latest',
      stat: null,
      params: { units: 'us', output: 'spread' },
    })
  })
})

describe('the Share link', () => {
  it('carries the comparison, period, threshold and count, and drops what it can’t read', () => {
    const shown = view({
      layer: 'air_temperature_max',
      span: 'range',
      climate: 'departure',
      period: 'last10',
      count: 'days_above_93p2',
    })
    const query = toQuery(VIEW_FIELDS, shown).toString()
    expect(query).toBe('layer=air_temperature_max&span=range&climate=departure&period=last10&count=days_above_93p2')
    expect({ ...defaults(VIEW_FIELDS), ...fromQuery(VIEW_FIELDS, query) }).toEqual(shown)
    expect(fromQuery(VIEW_FIELDS, 'threshold=28').threshold).toBe(28)
    expect(fromQuery(VIEW_FIELDS, 'climate=median&period=last20&threshold=30&count=hot')).toEqual({})
  })
})

describe('the cell panel agrees with the tiles', () => {
  const AT = { lat: 43.0731, lng: -89.4012 }

  it('charts the same days, setting and smoothing the compared map shows', () => {
    for (const changes of [
      { climate: 'departure', roll: 7, date: '2026-07-08' },
      { climate: 'normal', span: 'range', date: '2026-07-14', start: '2026-07-01' },
      { span: 'range', date: '2026-07-14', count: 'days_above_86', climate: 'departure' },
    ] as Partial<ExplorerView>[]) {
      const v = view(changes)
      const l = layer('air_temperature_max')
      const tiles = tileRequest(v, l, context)!
      const series = seriesRequest(v, l, tiles, AT)!
      expect(series.params.units).toBe(tiles.params.units)
      if (tiles.time.includes('..')) expect(`${series.from}..${series.to}`).toBe(tiles.time)
      if (tiles.params.roll) expect(series.params.roll).toBe(tiles.params.roll)
    }
    const dd = view({ climate: 'percentile', span: 'season', dd: 'sine_41_86', date: '2026-07-08' })
    const tiles = tileRequest(dd, layer('degree_days'), context)!
    expect(tiles.params).toMatchObject({ climate: 'percentile', dd: 'sine_41_86' })
    const series = seriesRequest(dd, layer('degree_days'), tiles, AT)!
    expect(series.params).toMatchObject({ dd: 'sine_41_86', start: '2026-01-01', end: '2026-07-08' })
    expect(readSeries(series, { meta: {}, data: { date: [] } }).values).toEqual([])
  })

  it('says the value in words with the tiles’ own comparison, threshold and output', () => {
    const words = (id: string, changes: Partial<ExplorerView>, value: number, unit: string, units = US) => {
      const tiles = tileRequest(view(changes), layer(id), context)!
      return climateValueWords({
        layer: layer(id),
        time: tiles.time,
        params: tiles.params,
        value,
        unit,
        units,
        years: '1996–2025',
      })
    }
    expect(words('air_temperature_min', { climate: 'departure' }, 2, 'delta_degC')).toBe(
      '3.6 °F above normal (1996–2025).',
    )
    expect(words('air_temperature_min', { climate: 'departure' }, -2, 'delta_degC', METRIC)).toBe(
      '2.0 °C below normal (1996–2025).',
    )
    expect(words('air_temperature_min', { climate: 'departure' }, 0.01, 'delta_degC')).toBe('Normal (1996–2025).')
    expect(words('precipitation_total', { climate: 'percentile' }, 92, 'percent')).toBe(
      'The 92nd percentile, among the highest of the period (1996–2025).',
    )
    expect(words('air_temperature_min', { climate: 'normal' }, 1, 'degC')).toBe('The average over 1996–2025.')
    expect(
      words('air_temperature_max', { span: 'range', count: 'days_above_86', climate: 'departure' }, -3, 'day'),
    ).toBe('3 days fewer than normal (1996–2025).')
    expect(words('freeze_chance', { date: '2026-05-01', threshold: 28 }, 30, 'percent')).toBe(
      'Hard freeze (28 °F) came after May 1 in 30% of years (1996–2025).',
    )
    expect(words('freeze_chance', { date: '2026-10-01' }, 100, 'percent')).toBe(
      'Frost (32 °F) came on or before Oct 1 in every year (1996–2025).',
    )
    const april25 = (Date.UTC(2026, 3, 25) / 86_400_000) as number
    expect(words('freeze_dates', { output: 'last_spring_p90' }, april25, 'date')).toBe(
      'The last spring frost (32 °F) came by Apr 25 in 9 years in 10 (1996–2025).',
    )
    expect(words('freeze_dates', { output: 'season_days_p50', threshold: 24 }, 171.4, 'day')).toBe(
      'Killing freeze (24 °F): the frost-free season lasts 171 days in a typical year (1996–2025).',
    )
    expect(words('air_temperature_min', {}, 1, 'degC')).toBeNull()
  })

  it('links the Climate tab with the tiles’ period', () => {
    const tiles = tileRequest(view({ climate: 'departure', period: 'last10' }), layer('air_temperature_min'), context)!
    expect(siteClimatePath(43.0731, -89.4012, 'Madison', tiles.params.period as string)).toBe(
      '/sites/43.0731,-89.4012?tab=climate&cperiod=last10&name=Madison',
    )
    expect(siteClimatePath(43.0731, -89.4012, null, null)).toBe('/sites/43.0731,-89.4012?tab=climate')
  })
})

describe('a count in words', () => {
  it('names the bound in the reader’s units, with the name growers know', () => {
    const label = (id: string, count: string, units = US) =>
      countLabel(
        layer(id).counts!.find((c) => c.count === count)!,
        units,
      )
    expect(label('air_temperature_max', 'days_above_93p2')).toBe('Days at or above 93 °F (heat days)')
    expect(label('air_temperature_max', 'days_above_90')).toBe('Days at or above 90 °F')
    expect(label('air_temperature_min', 'days_below_32', METRIC)).toBe('Days at or below 0.0 °C (frost)')
    expect(label('precipitation_sum', 'days_below_0p01')).toBe('Days at or below 0.01 in (dry days)')
    expect(label('shortwave_radiation_sum', 'days_above_20')).toBe('Days at or above 20 MJ/m² (sunny days)')
  })
})

describe('a day of the year', () => {
  it('runs a year’s timeline with nothing observed or forecast', () => {
    const t = noYearTimeline('2026-05-01')
    expect(t).toMatchObject({ start: '2026-01-01', count: 365, min: 0, max: 364 })
    expect(t.ticks).toHaveLength(12)
  })

  it('steps round the year and shows without one', () => {
    expect(stepNoYear('2026-12-31', 1)).toBe('2026-01-01')
    expect(stepNoYear('2026-01-03', -7)).toBe('2026-12-27')
    expect(stepNoYear('2024-02-28', 1)).toBe('2024-02-29')
    expect(monthDayText('2026-05-01')).toBe('May 1')
  })
})
