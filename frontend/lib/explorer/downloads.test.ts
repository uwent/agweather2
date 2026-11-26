import { describe, expect, it } from 'vitest'

import { downloadLinks, gridParams, viewBbox } from './downloads'
import type { TileRequest } from './view'

const day: TileRequest = { layer: 'air_temperature_max', time: '2026-11-20', stat: null, params: { units: 'us' } }
const query = (url: string) => Object.fromEntries(new URL(url, 'https://example.org').searchParams)

describe('gridParams', () => {
  it('gives /grids the time as the tiles give it to the server', () => {
    expect(gridParams(day)).toEqual({ units: 'us', stat: null, date: '2026-11-20' })
    expect(gridParams({ ...day, time: 'latest' })).toEqual({ units: 'us', stat: null })
    expect(gridParams({ ...day, time: '2026-11-20T15' })).toMatchObject({ time: '2026-11-20T15' })
    expect(gridParams({ ...day, time: '2026-07-01..2026-07-14', stat: 'sum' })).toMatchObject({
      start: '2026-07-01',
      end: '2026-07-14',
      stat: 'sum',
    })
    expect(gridParams({ ...day, time: '2025-26' })).toMatchObject({ season: '2025-26' })
  })
})

describe('viewBbox', () => {
  it('is the view within the coverage, rounded outward, as south,west,north,east', () => {
    expect(viewBbox([-91.234, 42.111, -88.555, 44.999])).toBe('42.11,-91.24,45,-88.55')
  })

  it('is the whole coverage when the view holds it all or is off it', () => {
    expect(viewBbox([-130, 20, -60, 60])).toBeNull()
    expect(viewBbox([-125, 30, -120, 32])).toBeNull()
    expect(viewBbox(null)).toBeNull()
  })
})

describe('downloadLinks', () => {
  it('asks for the map on screen in the reader’s units, over the area in view', () => {
    const links = downloadLinks(day, {
      bounds: [-91, 42, -88, 45],
      system: 'metric',
      palette: 'viridis',
      scale: '0,10',
    })
    expect(links.geotiff.startsWith('/api/v2/grids/air_temperature_max?')).toBe(true)
    expect(query(links.geotiff)).toEqual({
      bbox: '42,-91,45,-88',
      date: '2026-11-20',
      format: 'geotiff',
      units: 'metric',
    })
    expect(query(links.netcdf).format).toBe('netcdf')
    expect(links.inView).toBe(true)
    expect(links.tilejson.startsWith('/api/v2/tiles/air_temperature_max.json?')).toBe(true)
    expect(query(links.tilejson)).toEqual({
      palette: 'viridis',
      scale: '0,10',
      style: 'default',
      time: '2026-11-20',
      units: 'metric',
    })
  })

  it('keeps degree days in US units, as their setting is in °F, and drops a range in other units', () => {
    const links = downloadLinks(
      {
        layer: 'degree_days',
        time: '2026-01-01..2026-11-20',
        stat: 'sum',
        params: { units: 'us', dd: 'modified_50_86' },
      },
      { bounds: null, system: 'metric', palette: null, scale: '100,2000' },
    )
    expect(query(links.geotiff)).toMatchObject({ units: 'us', dd: 'modified_50_86', stat: 'sum', start: '2026-01-01' })
    expect(links.inView).toBe(false)
    expect(links.system).toBe('us')
    expect(query(links.tilejson).scale).toBeUndefined()
  })
})
