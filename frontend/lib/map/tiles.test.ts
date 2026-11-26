// tileAt's test from WISP 3: app/frontend/lib/map/radar.test.ts (copied)
import { describe, expect, it } from 'vitest'

import { tileAt } from './tiles'

describe('tileAt', () => {
  it('finds the tile and pixel under a point', () => {
    expect(tileAt([0, 0], 1)).toEqual({ z: 1, x: 1, y: 1, px: 0, py: 0 })
    // North 160 at zoom 9
    const tile = tileAt([-89.5213, 44.1335], 9)
    expect([tile.x, tile.y]).toEqual([128, 185])
    expect(tile.px).toBeGreaterThanOrEqual(0)
    expect(tile.px).toBeLessThan(256)
  })
})
