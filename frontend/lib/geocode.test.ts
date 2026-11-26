// WISP 3: app/frontend/lib/geocode.test.ts (copied)
import { describe, expect, it } from 'vitest'

import { parsePlaces } from './geocode'

describe('parsePlaces', () => {
  it('turns Nominatim results into labels, centers and bounds', () => {
    const [place] = parsePlaces([
      {
        display_name: 'Hancock, Waushara County, Wisconsin, United States',
        lat: '44.1335840',
        lon: '-89.5231770',
        boundingbox: ['44.1228300', '44.1409970', '-89.5321490', '-89.4943120'],
      },
    ])
    expect(place).toEqual({
      label: 'Hancock, Waushara County, Wisconsin',
      center: [-89.523177, 44.133584],
      bounds: [-89.532149, 44.12283, -89.494312, 44.140997],
    })
  })
})
