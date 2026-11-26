import { describe, expect, it } from 'vitest'

import { addLocation, addLocations } from './locations'

describe('the locations', () => {
  it('adds a place once, to four decimals', () => {
    const first = addLocation([], { lat: 43.070012, lng: -89.400049, name: 'Madison' })
    expect(first).toEqual({ list: [{ key: '43.07,-89.4', lat: 43.07, lng: -89.4, name: 'Madison' }], message: null })
    const again = addLocation(first.list, { lat: 43.07, lng: -89.4, name: '' })
    expect(again.message).toBe('43.07° N, 89.40° W is already in the list.')
    expect(again.list).toHaveLength(1)
  })

  it('stops at the API’s 50, saying how many didn’t fit', () => {
    const places = Array.from({ length: 53 }, (_, k) => ({ lat: 43 + k / 100, lng: -89, name: `Site ${k}` }))
    const added = addLocations([], places)
    expect(added.list).toHaveLength(50)
    expect(added.message).toBe('A download can include up to 50 locations, so 3 sites weren’t added.')
    expect(addLocation(added.list, { lat: 40, lng: -90, name: 'One more' }).message).toBe(
      'A download can include up to 50 locations. Remove one to add One more.',
    )
  })
})
