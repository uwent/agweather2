// WISP 3: app/frontend/lib/map/radar.test.ts (adapted: tileAt's test is in tiles.test.ts)
import { describe, expect, it } from 'vitest'

import { reflectivityForColor } from './radar'

describe('radar values from the tile colors', () => {
  it("reads IEM's palette: 0.5 dBZ an index from −32", () => {
    expect(reflectivityForColor(0x43, 0xd6, 0x7e, 255)).toBe(20)
    expect(reflectivityForColor(0x35, 0xd6, 0x5b, 255)).toBe(21)
    expect(reflectivityForColor(0xff, 0xe2, 0x00, 255)).toBe(40)
    expect(reflectivityForColor(0xf8, 0x00, 0x00, 255)).toBe(50)
  })

  it('reads transparent pixels and other colors as nothing', () => {
    expect(reflectivityForColor(0x43, 0xd6, 0x7e, 0)).toBeNull()
    expect(reflectivityForColor(1, 2, 3, 255)).toBeNull()
  })
})
