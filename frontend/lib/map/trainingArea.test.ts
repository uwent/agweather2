import { describe, expect, it } from 'vitest'

import { insideOutline, trainingOutline } from './trainingArea'

describe('insideOutline', () => {
  const square: [number, number][] = [
    [0, 0],
    [10, 0],
    [10, 10],
    [0, 10],
    [0, 0],
  ]
  const hole: [number, number][] = [
    [4, 4],
    [6, 4],
    [6, 6],
    [4, 6],
    [4, 4],
  ]

  it('finds a point inside a polygon, and outside it or in its hole', () => {
    const polygon = { type: 'Polygon' as const, coordinates: [square, hole] }
    expect(insideOutline(polygon, 2, 2)).toBe(true)
    expect(insideOutline(polygon, 5, 5)).toBe(false)
    expect(insideOutline(polygon, 12, 5)).toBe(false)
  })

  it('reads every part of a multipolygon', () => {
    const shifted = square.map(([x, y]) => [x + 20, y] as [number, number])
    const multi = { type: 'MultiPolygon' as const, coordinates: [[square], [shifted]] }
    expect(insideOutline(multi, 25, 5)).toBe(true)
    expect(insideOutline(multi, 15, 5)).toBe(false)
  })
})

describe('trainingOutline', () => {
  it('outlines the Central Sands for the Colorado potato beetle, and nothing for a model fitted nowhere', async () => {
    const beetle = await trainingOutline('colorado-potato-beetle')
    expect(beetle?.codes).toContain('55137')
    // Hancock (Waushara County) is inside; Madison (Dane County) is not
    expect(insideOutline(beetle!.geometry, -89.5168, 44.1336)).toBe(true)
    expect(insideOutline(beetle!.geometry, -89.4, 43.07)).toBe(false)
    expect(await trainingOutline('late-blight-dsv')).toBeNull()
  })
})
