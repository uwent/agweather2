import { describe, expect, it } from 'vitest'

import { MAX_TILES, tileUrl, visibleTiles } from './prefetch'

describe('the next day’s tiles', () => {
  it('covers the map’s bounds at the zoom below, within the API’s zooms', () => {
    const tiles = visibleTiles([-93, 42, -87, 47], 6.7)
    expect(new Set(tiles.map((t) => t.z))).toEqual(new Set([6]))
    expect(tiles).toContainEqual({ z: 6, x: 15, y: 23 }) // Madison
    expect(visibleTiles([-93, 42, -87, 47], 11)[0].z).toBe(8)
    expect(visibleTiles([-130, 20, -60, 55], 1)[0].z).toBe(3)
  })

  it('stops at a limit', () => {
    expect(visibleTiles([-104, 35, -78, 50], 8)).toHaveLength(MAX_TILES)
  })

  it('asks for the same address DataMap does', () => {
    const request = {
      layer: 'degree_days',
      time: '2026-01-01..2026-07-08',
      stat: 'sum' as const,
      params: { units: 'us', dd: 'sine_50_86', output: null },
    }
    expect(tileUrl(request, { z: 6, x: 15, y: 23 }, 'https://example.org')).toBe(
      'https://example.org/api/v2/tiles/degree_days/2026-01-01..2026-07-08/6/15/23.png?dd=sine_50_86&stat=sum&units=us',
    )
  })
})
