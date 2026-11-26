import { describe, expect, it } from 'vitest'

import { formatCoords, parseSiteKey, roundCoord, siteKey, siteUrl, validCoords } from './siteKey'

describe('site keys', () => {
  it('round to 4 decimals and leave out trailing zeros, so one place has one key', () => {
    expect(siteKey(43.07, -89.4)).toBe('43.07,-89.4')
    expect(siteKey(43.070001, -89.40004)).toBe('43.07,-89.4')
    expect(siteKey(43.12346, -89.98765)).toBe('43.1235,-89.9877')
    expect(siteKey(-0.00001, 0)).toBe('0,0')
    expect(roundCoord(-0.00004)).toBe(0)
  })

  it('read typed coordinates in several forms, and refuse what isn’t a place', () => {
    expect(parseSiteKey('43.07,-89.4')).toEqual({ lat: 43.07, lng: -89.4 })
    expect(parseSiteKey(' 43.07, -89.40 ')).toEqual({ lat: 43.07, lng: -89.4 })
    expect(parseSiteKey('43.07 -89.40')).toEqual({ lat: 43.07, lng: -89.4 })
    expect(parseSiteKey('43.07;-89.40')).toEqual({ lat: 43.07, lng: -89.4 })
    expect(parseSiteKey('95,-89')).toBeNull()
    expect(parseSiteKey('Madison, WI')).toBeNull()
    expect(validCoords(90, 180)).toBe(true)
    expect(validCoords(NaN, 0)).toBe(false)
  })

  it('build the site page’s address in one place', () => {
    expect(siteUrl('43.07,-89.4')).toBe('/sites/43.07,-89.4')
    expect(siteUrl('43.07,-89.4', 'Home farm')).toBe('/sites/43.07,-89.4?name=Home+farm')
  })

  it('format coordinates with hemispheres', () => {
    expect(formatCoords(43.07, -89.4)).toBe('43.07° N, 89.40° W')
    expect(formatCoords(-33.9, 151.2, 1)).toBe('33.9° S, 151.2° E')
  })
})
