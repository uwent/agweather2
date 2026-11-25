// WISP 3: app/frontend/lib/map/prefs.test.ts (adapted: keyed by page, without WISP's older formats)
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DEFAULT_PREFS, loadPrefs, savePrefs } from './prefs'

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('map prefs', () => {
  it('remembers settings per page', () => {
    savePrefs('map', { ...DEFAULT_PREFS, basemap: 'imagery', overlay: 'drought' })
    expect(loadPrefs('map')).toMatchObject({ basemap: 'imagery', overlay: 'drought' })
    expect(loadPrefs('site')).toEqual(DEFAULT_PREFS)
  })

  it('fills in settings saved before they existed, and drops layers and basemaps the map no longer has', () => {
    localStorage.setItem('agweather-map:map', JSON.stringify({ basemap: 'imagery', overlay: 'gone' }))
    expect(loadPrefs('map')).toEqual({ ...DEFAULT_PREFS, basemap: 'imagery' })
    localStorage.setItem('agweather-map:map', JSON.stringify({ basemap: 'topo' }))
    expect(loadPrefs('map')).toEqual(DEFAULT_PREFS)
  })

  it('starts from the defaults when what was saved is unreadable', () => {
    localStorage.setItem('agweather-map:map', '{not json')
    expect(loadPrefs('map')).toEqual(DEFAULT_PREFS)
    localStorage.setItem('agweather-map:map', '7')
    expect(loadPrefs('map')).toEqual(DEFAULT_PREFS)
  })

  it('works without storage (private mode, blocked site data)', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })
    expect(() => savePrefs('map', DEFAULT_PREFS)).not.toThrow()
    expect(loadPrefs('map')).toEqual(DEFAULT_PREFS)
  })

  it('hands out a copy of the defaults, never the defaults themselves', () => {
    loadPrefs('map').opacity.radar = 0.2
    expect(DEFAULT_PREFS).toMatchObject({ opacity: {} })
  })
})
