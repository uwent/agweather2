import { describe, expect, it } from 'vitest'

import { placeKey, placeLine, placeOf, placeSitePath, placeTitle, placeView, PLACE_FIELDS } from './place'
import { fromQuery, toQuery } from '../viewState'

const where = { county: 'Dane County', state: 'WI', in_box: true }

describe('a tool’s place', () => {
  it('travels in the view as at and name', () => {
    const view = { ...placeView({ lat: 43.073051, lng: -89.40123, name: 'Madison' }) }
    expect(view).toEqual({ at: { lat: 43.0731, lng: -89.4012 }, name: 'Madison' })
    expect(toQuery(PLACE_FIELDS, view).toString()).toBe('at=43.0731%2C-89.4012&name=Madison')
    expect(placeOf({ at: null, name: '', ...fromQuery(PLACE_FIELDS, 'at=43.0731,-89.4012') })).toEqual({
      lat: 43.0731,
      lng: -89.4012,
      name: null,
    })
    expect(placeOf({ at: null, name: 'Madison' })).toBeNull()
    expect(placeView(null)).toEqual({ at: null, name: '' })
  })

  it('is called by its saved name, its own, where it is, or its coordinates', () => {
    const place = { lat: 43.07, lng: -89.4, name: 'Madison' }
    expect(placeTitle(place, { name: 'Home farm', lat: 43.07, lng: -89.4 })).toBe('Home farm')
    expect(placeTitle(place, undefined)).toBe('Madison')
    expect(placeTitle({ ...place, name: null }, null, where)).toBe('Dane County, WI')
    expect(placeTitle({ ...place, name: null }, null, null)).toBe('43.07° N, 89.4° W')
  })

  it('says where it is, and when we don’t cover it', () => {
    const place = { lat: 43.07, lng: -89.4, name: null }
    expect(placeLine(place, where)).toBe('Dane County, WI · 43.07° N, 89.4° W')
    expect(placeLine(place, null)).toBe('43.07° N, 89.4° W')
    expect(placeLine(place, { county: null, state: null, in_box: false })).toMatch(/Outside the area we cover/)
  })

  it('opens its site page', () => {
    expect(placeSitePath({ lat: 43.07, lng: -89.4, name: 'Madison' })).toBe('/sites/43.07,-89.4?name=Madison')
    expect(placeSitePath({ lat: 43.07, lng: -89.4, name: null })).toBe('/sites/43.07,-89.4')
    expect(placeKey({ lat: 43.070001, lng: -89.4, name: null })).toBe('43.07,-89.4')
  })
})
