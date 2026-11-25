// WISP 3: app/frontend/lib/geo.test.ts (only pointInPolygon's case)
import { describe, expect, it } from 'vitest'

import { type LngLat, pointInPolygon } from './geo'

describe('pointInPolygon', () => {
  it('finds a point inside a polygon but not in its hole', () => {
    const square = (min: number, max: number): LngLat[] => [
      [min, min],
      [max, min],
      [max, max],
      [min, max],
      [min, min],
    ]
    expect(pointInPolygon([5, 5], [square(0, 10)])).toBe(true)
    expect(pointInPolygon([11, 5], [square(0, 10)])).toBe(false)
    expect(pointInPolygon([5, 5], [square(0, 10), square(4, 6)])).toBe(false)
    expect(pointInPolygon([2, 2], [square(0, 10), square(4, 6)])).toBe(true)
  })
})
