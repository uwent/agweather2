import { describe, expect, it } from 'vitest'

import { tileRequest } from '@/lib/explorer/view'
import { units } from '@/lib/units'
import { fromQuery } from '@/lib/viewState'
import { VIEW_FIELDS } from '@/lib/explorer/view'
import layersFixture from '@/test/fixtures/layers.json'
import type { LayerInfo } from '@/types/api'

import {
  CLIMATE_MAPS,
  climateMapText,
  defaultMap,
  explorerUrl,
  explorerView,
  hotDaysSpan,
  MAP_LAYERS,
  mapPeriod,
  mapShown,
  mapsFor,
} from './maps'

const layers = layersFixture.data as unknown as LayerInfo[]
const layerOf = (id: string) => layers.find((l) => l.id === id)!
const today = '2026-11-25'
const request = (map: (typeof CLIMATE_MAPS)[number], period: 'last30' | 'last10' = 'last30') => {
  const layer = layerOf(MAP_LAYERS[map])
  const view = explorerView({ map, layer, today, period })!
  return tileRequest(view, layer, { today })
}

describe('the climate maps', () => {
  it('offer the chance of a freeze only in spring and fall', () => {
    expect(mapsFor('2026-05-01')).toContain('freeze-chance')
    expect(mapsFor('2026-10-01')).toContain('freeze-chance')
    expect(mapsFor('2026-07-15')).not.toContain('freeze-chance')
    expect(mapsFor('2026-01-15')).not.toContain('freeze-chance')
    expect(mapsFor('2026-01-15')).toHaveLength(CLIMATE_MAPS.length - 1)
  })

  it('start on the season’s degree days from April to October, else the last 30 days’ rain', () => {
    expect(defaultMap('2026-04-01')).toBe('degree-days')
    expect(defaultMap('2026-10-31')).toBe('degree-days')
    expect(defaultMap('2026-11-25')).toBe('rain')
    expect(mapShown(null, '2026-07-01')).toBe('degree-days')
    expect(mapShown('freeze-chance', '2026-07-01')).toBe('degree-days')
    expect(mapShown('freeze-chance', '2026-05-01')).toBe('freeze-chance')
  })

  it('count the hot days of this summer from mid-June, else of last summer', () => {
    expect(hotDaysSpan('2026-11-24')).toEqual({ start: '2026-06-01', end: '2026-09-30' })
    expect(hotDaysSpan('2026-07-10')).toEqual({ start: '2026-06-01', end: '2026-07-10' })
    expect(hotDaysSpan('2026-06-10')).toEqual({ start: '2025-06-01', end: '2025-09-30' })
  })

  it('ask for the tiles the map explorer would', () => {
    expect(request('degree-days')).toEqual({
      layer: 'degree_days',
      time: '2026-01-01..2026-11-24',
      stat: 'sum',
      params: { units: 'us', climate: 'departure', period: null, dd: 'modified_50_86' },
    })
    expect(request('rain', 'last10')).toEqual({
      layer: 'precipitation_sum',
      time: '2026-10-26..2026-11-24',
      stat: 'sum',
      params: { units: 'us', climate: 'departure', period: 'last10' },
    })
    expect(request('highs')).toMatchObject({ time: '2026-11-18..2026-11-24', stat: 'mean' })
    expect(request('freeze-chance')).toEqual({
      layer: 'freeze_chance',
      time: today,
      stat: null,
      params: { units: 'us', threshold: 28, period: null },
    })
    expect(request('last-freeze')).toMatchObject({ layer: 'freeze_dates', params: { output: 'last_spring_p50' } })
    expect(request('first-freeze')).toMatchObject({ layer: 'freeze_dates', params: { output: 'first_fall_p50' } })
    expect(request('hot-days')).toEqual({
      layer: 'air_temperature_max',
      time: '2026-06-01..2026-09-30',
      stat: null,
      params: { units: 'us', climate: 'departure', period: null, count: 'days_above_90' },
    })
  })

  it('wait for a range’s latest day', () => {
    const empty = { range: { first: null, last: null, forecast_through: null } }
    expect(explorerView({ map: 'rain', layer: empty, today, period: 'last30' })).toBeNull()
    expect(explorerView({ map: 'last-freeze', layer: empty, today, period: 'last30' })).not.toBeNull()
  })

  it('open the same map in the map explorer, with the place', () => {
    const layer = layerOf('precipitation_sum')
    const view = explorerView({ map: 'rain', layer, today, period: 'last10', at: { lat: 43.07, lng: -89.4 } })!
    const url = explorerUrl(view)
    expect(url).toBe(
      '/map?layer=precipitation_sum&span=range&date=2026-11-24&start=2026-10-26&stat=sum&at=43.07,-89.4&climate=departure&period=last10',
    )
    // The explorer reads the link back to the same tiles
    const back = { ...view, ...fromQuery(VIEW_FIELDS, url.split('?')[1]) }
    expect(tileRequest(back, layer, { today })).toEqual(tileRequest(view, layer, { today }))
  })

  it('take the climate sections’ periods', () => {
    expect(mapPeriod('last10')).toBe('last10')
    expect(mapPeriod('last20')).toBe('last30')
  })

  it('name temperatures in the reader’s units', () => {
    expect(climateMapText('hot-days', units('imperial')).label).toBe('Days at or above 90 °F, June to September')
    expect(climateMapText('hot-days', units('metric')).label).toBe('Days at or above 32.2 °C, June to September')
    expect(climateMapText('freeze-chance', units('metric')).title).toBe('Chance of a hard freeze (−2.2 °C)')
  })
})
