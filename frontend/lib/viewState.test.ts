import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const replace = vi.fn()
vi.mock('@inertiajs/core', () => ({ router: { replace: (...args: unknown[]) => replace(...args) } }))

import { codecs, defaults, field, fromQuery, replaceAddress, shareUrl, toQuery, viewState } from './viewState'

const fields = {
  layer: field(codecs.string, 'air_temperature_max'),
  stat: field(codecs.oneOf(['sum', 'mean', 'max'] as const), 'mean'),
  date: field(codecs.date, null),
  range: field(codecs.dateRange, null),
  at: field(codecs.latLng(), null),
  zoom: field(codecs.number({ digits: 2, min: 0, max: 22 }), 6, 'z'),
  roll: field(codecs.list(codecs.integer({ min: 1 })), [] as number[]),
  forecast: field(codecs.boolean, true),
}

function go(url: string, state: unknown = null) {
  window.history.replaceState(state, '', url)
}

beforeEach(() => {
  sessionStorage.clear()
  replace.mockReset()
  go('/map')
})
afterEach(() => vi.useRealTimers())

describe('codecs', () => {
  it('read what they write and refuse what they cannot read', () => {
    expect(codecs.date.parse('2026-02-30')).toBeUndefined()
    expect(codecs.date.parse('2026-07-08')).toBe('2026-07-08')
    expect(codecs.dateRange.parse('2026-05-01..2026-07-08')).toEqual({ start: '2026-05-01', end: '2026-07-08' })
    expect(codecs.dateRange.parse('2026-07-08..2026-05-01')).toBeUndefined()
    expect(codecs.latLng().format({ lat: 43.073051, lng: -89.40123 })).toBe('43.0731,-89.4012')
    expect(codecs.latLng().parse('43.07,-89.4')).toEqual({ lat: 43.07, lng: -89.4 })
    expect(codecs.latLng().parse('95,-89.4')).toBeUndefined()
    expect(codecs.number().parse('')).toBeUndefined()
    expect(codecs.integer().parse('2.5')).toBeUndefined()
    expect(codecs.list(codecs.integer()).parse('7,14')).toEqual([7, 14])
    expect(codecs.list(codecs.integer()).parse('7,x')).toBeUndefined()
    expect(codecs.boolean.parse('yes')).toBeUndefined()
    expect(codecs.oneOf(['a', 'b']).parse('c')).toBeUndefined()
  })
})

describe('the query form', () => {
  it('leaves defaults out and keeps the fields’ order and parameter names', () => {
    const state = {
      ...defaults(fields),
      date: '2026-07-08',
      at: { lat: 43.07, lng: -89.4 },
      zoom: 7.5,
      roll: [7, 14],
      forecast: false,
    }
    expect(toQuery(fields, state).toString()).toBe('date=2026-07-08&at=43.07%2C-89.4&z=7.5&roll=7%2C14&forecast=false')
    expect(fromQuery(fields, toQuery(fields, state))).toEqual({
      date: '2026-07-08',
      at: { lat: 43.07, lng: -89.4 },
      zoom: 7.5,
      roll: [7, 14],
      forecast: false,
    })
    expect(toQuery(fields, defaults(fields)).toString()).toBe('')
  })

  it('drops a value it cannot read', () => {
    expect(fromQuery(fields, 'stat=median&z=40&date=2026-07-08&other=1')).toEqual({ date: '2026-07-08' })
  })

  it('builds a share link with only what differs from the defaults', () => {
    const state = { ...defaults(fields), layer: 'precipitation_sum' }
    expect(shareUrl(fields, state, { origin: 'https://agweather.cals.wisc.edu' })).toBe(
      'https://agweather.cals.wisc.edu/map?layer=precipitation_sum',
    )
    expect(shareUrl(fields, defaults(fields), { path: '/sites/43.07,-89.4', origin: '' })).toBe('/sites/43.07,-89.4')
  })
})

describe('viewState', () => {
  it('starts at the defaults, keeps the tab’s view and leaves the address bar alone', () => {
    vi.useFakeTimers()
    const write = vi.fn()
    const view = viewState(fields, { writeAddress: write })
    expect(view.value).toEqual(defaults(fields))
    expect(view.fromLink).toBe(false)
    view.patch({ layer: 'precipitation_sum', zoom: 8 })
    vi.runAllTimers()
    expect(write).not.toHaveBeenCalled()
    expect(window.location.search).toBe('')
    expect(sessionStorage.getItem('view:/map')).toBe('"layer=precipitation_sum&z=8"')

    // A reload (or Back to this page) restores it
    const again = viewState(fields, { writeAddress: write })
    expect(again.value.layer).toBe('precipitation_sum')
    expect(again.value.zoom).toBe(8)
    expect(again.fromLink).toBe(false)
  })

  it('keeps one view per path', () => {
    viewState(fields).patch({ layer: 'precipitation_sum' })
    go('/sites/43.07,-89.4')
    expect(viewState(fields).value.layer).toBe('air_temperature_max')
  })

  it('opens a shared link’s view, which stays in the bar until the view changes', () => {
    vi.useFakeTimers()
    sessionStorage.setItem('view:/map', '"layer=snow_depth"')
    go('/map?layer=precipitation_sum&z=9&utm_source=email#legend')
    const write = vi.fn((url: string) => go(url))
    const view = viewState(fields, { writeAddress: write })
    expect(view.fromLink).toBe(true)
    expect(view.value).toMatchObject({ layer: 'precipitation_sum', zoom: 9 })
    view.patch({ layer: 'precipitation_sum' }) // no change
    vi.runAllTimers()
    expect(write).not.toHaveBeenCalled()

    view.patch({ zoom: 10 })
    view.patch({ zoom: 11 })
    vi.runAllTimers()
    // Once, after the changes settle; parameters that aren't the view's, and the hash, are kept
    expect(write).toHaveBeenCalledTimes(1)
    expect(write).toHaveBeenCalledWith('/map?utm_source=email#legend')
    expect(sessionStorage.getItem('view:/map')).toBe('"layer=precipitation_sum&z=11"')

    view.patch({ zoom: 12 })
    vi.runAllTimers()
    expect(write).toHaveBeenCalledTimes(1)
  })

  it('writes the view into the address bar when asked to (the one-line switch)', () => {
    vi.useFakeTimers()
    const write = vi.fn((url: string) => go(url))
    const view = viewState(fields, { writeAddress: write, inAddressBar: true })
    view.patch({ date: '2026-07-08' })
    vi.runAllTimers()
    expect(write).toHaveBeenLastCalledWith('/map?date=2026-07-08')
    view.reset()
    vi.runAllTimers()
    expect(write).toHaveBeenLastCalledWith('/map')

    // A reload restores the tab's view into the bar
    view.patch({ zoom: 3 })
    view.destroy()
    go('/map')
    viewState(fields, { writeAddress: write, inAddressBar: true })
    vi.runAllTimers()
    expect(write).toHaveBeenLastCalledWith('/map?z=3')
  })

  it('works as a Svelte store', () => {
    const view = viewState(fields)
    const seen: string[] = []
    const stop = view.subscribe((value) => seen.push(value.layer))
    view.patch({ layer: 'b' })
    stop()
    view.patch({ layer: 'c' })
    expect(seen).toEqual(['air_temperature_max', 'b'])
  })

  it('reads a stored view it cannot parse as the defaults', () => {
    sessionStorage.setItem('view:/map', '{not json')
    expect(viewState(fields).value).toEqual(defaults(fields))
  })
})

describe('replaceAddress', () => {
  it('goes through Inertia when Inertia keeps the page in history', () => {
    go('/map?layer=x', { page: { component: 'Map/Show', url: '/map?layer=x' } })
    replaceAddress('/map')
    expect(replace).toHaveBeenCalledWith({ url: '/map', preserveState: true, preserveScroll: true })
  })

  it('keeps the history entry’s state otherwise', () => {
    go('/map?layer=x', { scrollRegions: [] })
    replaceAddress('/map')
    expect(replace).not.toHaveBeenCalled()
    expect(window.location.pathname + window.location.search).toBe('/map')
    expect(window.history.state).toEqual({ scrollRegions: [] })
  })
})
