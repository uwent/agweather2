// WISP 3: app/frontend/lib/map/overlays.test.ts (adapted: the drought area without points is our coverage)
import { describe, expect, it, vi } from 'vitest'

import type { LngLat } from '@/lib/geo'

import { COVERAGE_BOUNDS } from './coverage'

import {
  type DroughtData,
  droughtAt,
  droughtBounds,
  droughtDate,
  droughtUrl,
  OVERLAY_ORDER,
  OVERLAYS,
  parseWpcTime,
  RAIN_OVERLAYS,
  qpfValue,
  describeReflectivity,
} from './overlays'

const square = (west: number, south: number, east: number, north: number): LngLat[] => [
  [west, south],
  [east, south],
  [east, north],
  [west, north],
  [west, south],
]

describe('overlays', () => {
  it('has a place in the drawing order for every overlay', () => {
    expect(OVERLAYS.map((o) => o.id).toSorted()).toEqual(OVERLAY_ORDER.toSorted())
  })

  it("builds tile URLs with the refresh stamp, and the forecast's layer and box", () => {
    const radar = RAIN_OVERLAYS.find((o) => o.id === 'radar')!
    expect(radar.tiles(42)).toEqual([
      'https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png?t=42',
    ])
    const week = RAIN_OVERLAYS.find((o) => o.id === 'qpf7')!
    const [url] = week.tiles(1)
    expect(url).toContain('/wpc_qpf/MapServer/export?bbox={bbox-epsg-3857}')
    expect(url).toContain('layers=show:11')
  })

  it("asks NOAA's MRMS service for the period's estimate, drawn with NOAA's classes", () => {
    const day = RAIN_OVERLAYS.find((o) => o.id === 'rain24')!
    const url = new URL(day.tiles(1)[0].replace('{bbox-epsg-3857}', '0,0,1,1'))
    expect(url.pathname).toContain('/obs/mrms_qpe/ImageServer/exportImage')
    expect(JSON.parse(url.searchParams.get('mosaicRule')!).where).toBe("name='conus_QPE_24H'")
    expect(JSON.parse(url.searchParams.get('renderingRule')!).rasterFunction).toBe('rft_24hr')
  })

  it('reads the MRMS value at a point as millimeters, below 0.01 in as none, and NoData as missing', async () => {
    const day = RAIN_OVERLAYS.find((o) => o.id === 'rain72')!
    const answer = (value: string) =>
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ value })))
    answer('18.9')
    expect(await day.valueAt([-89.5, 44.1])).toEqual({ kind: 'depth', inches: 18.9 / 25.4 })
    answer('0.1')
    expect(await day.valueAt([-89.5, 44.1])).toEqual({ kind: 'none' })
    answer('0')
    expect(await day.valueAt([-89.5, 44.1])).toEqual({ kind: 'none' })
    answer('NoData')
    expect(await day.valueAt([-89.5, 44.1])).toEqual({ kind: 'text', text: 'No data here' })
    vi.restoreAllMocks()
  })

  it("gives the forecast's class at a point, up to the next one", () => {
    expect(qpfValue([])).toEqual({ kind: 'none' })
    expect(qpfValue([0.25])).toEqual({ kind: 'depth', inches: 0.25, upTo: 0.5 })
    expect(qpfValue([20])).toEqual({ kind: 'depth', inches: 20, upTo: null })
  })

  it('says what a reflectivity means for rain', () => {
    expect(describeReflectivity(15)).toMatch(/light/i)
    expect(describeReflectivity(35)).toBe('Moderate rain')
    expect(describeReflectivity(55)).toMatch(/hail/)
  })

  it("reads WPC's issue time as UTC", () => {
    expect(parseWpcTime('2026-10-17 22:03:02').toISOString()).toBe('2026-10-17T22:03:02.000Z')
  })
})

describe('drought', () => {
  const data: DroughtData = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { DM: 0, ValidStart: Date.UTC(2026, 9, 13) },
        geometry: { type: 'Polygon', coordinates: [square(-91, 43, -88, 46)] },
      },
      {
        type: 'Feature',
        properties: { DM: 1 },
        geometry: { type: 'MultiPolygon', coordinates: [[square(-90, 44, -89, 45)]] },
      },
      { type: 'Feature', properties: { DM: 2 }, geometry: null },
    ],
  }

  it('finds the highest category at a point, or none', () => {
    expect(droughtAt(data, [-89.5, 44.5])?.label).toBe('D1 Moderate drought')
    expect(droughtAt(data, [-90.5, 43.5])?.label).toBe('D0 Abnormally dry')
    expect(droughtAt(data, [-80, 40])).toBeNull()
  })

  it("gives the map's week", () => {
    expect(droughtDate(data)?.toISOString()).toBe('2026-10-13T00:00:00.000Z')
  })

  it('loads the area around the points, or the coverage without any', () => {
    expect(droughtBounds([[-89.5, 44.1]], 2)).toEqual([-91.5, 42.1, -87.5, 46.1])
    expect(droughtBounds([])).toEqual(COVERAGE_BOUNDS)
    const url = new URL(droughtUrl([-91.5, 42.1, -87.5, 46.1]))
    expect(url.searchParams.get('geometry')).toBe('-91.500,42.100,-87.500,46.100')
    expect(url.searchParams.get('f')).toBe('geojson')
  })
})
