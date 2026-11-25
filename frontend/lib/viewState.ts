// A page's view (the layer, the day, the point clicked, the zoom) as typed state with defaults, kept per tab and
// shared by link (D118, provisional). Readers paste the address bar meaning the page, so the bar stays on the plain
// path (`/map`) as the view changes; the Share button gives the link with the view in its query string
// (`/map?layer=…&time=…&at=43.07,-89.4`, defaults left out). Opening such a link restores that view, and the query
// stays in the bar until the reader changes the view. A reload or Back keeps the tab's view: it's kept in
// sessionStorage by path, in the same query form, so there's one way to write a view whichever way it travels.
//
// Putting the view in the address bar instead is one line: `STATE_IN_ADDRESS_BAR` (or `inAddressBar` per page).
//
// The address bar is changed through Inertia's `router.replace` (a client-side replace: no request, the page kept,
// and Inertia's own record of the URL, in memory and in history.state, kept with it), so Inertia never writes a
// stale URL back on a later `remember` or replace. Without Inertia (a test, a page outside it), it's
// `history.replaceState` keeping whatever state the entry holds.
//
//   const view = viewState({
//     layer: field(codecs.string, 'air_temperature_max'),
//     date: field(codecs.date, null as string | null),
//     at: field(codecs.latLng(), null as LatLng | null),
//     zoom: field(codecs.number({ digits: 2 }), 6, 'z'),
//   })
//   $view.layer; view.patch({ date: '2026-07-08' }); view.shareUrl()

import { router } from '@inertiajs/core'

import { readStored, writeStored } from './storage'

/** D118: false keeps the address bar on the plain path; true writes the view into it as it changes */
export const STATE_IN_ADDRESS_BAR = false

/** How one value is written in a query string, and read back: `parse` returns undefined for text it can't read,
 * and that value falls back to its default */
export type Codec<T> = {
  parse(text: string): T | undefined
  format(value: T): string
}

export type LatLng = { lat: number; lng: number }
export type DateRange = { start: string; end: string }

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

function isDate(text: string): boolean {
  if (!ISO_DATE.test(text)) return false
  const date = new Date(`${text}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(text)
}

/** Shortest text for a number at most `digits` decimals: 43.0700 is "43.07" */
function trimmed(value: number, digits: number | undefined): string {
  return digits === undefined ? String(value) : String(Number(value.toFixed(digits)))
}

function number(options: { digits?: number; min?: number; max?: number; integer?: boolean } = {}): Codec<number> {
  return {
    parse(text) {
      if (text.trim() === '') return undefined
      const value = Number(text)
      if (!Number.isFinite(value)) return undefined
      if (options.integer && !Number.isInteger(value)) return undefined
      if (options.min !== undefined && value < options.min) return undefined
      if (options.max !== undefined && value > options.max) return undefined
      return value
    },
    format: (value) => trimmed(value, options.digits),
  }
}

export const codecs = {
  string: { parse: (text: string) => text, format: (value: string) => value } satisfies Codec<string>,

  number,

  integer: (options: { min?: number; max?: number } = {}) => number({ ...options, integer: true }),

  boolean: {
    parse: (text: string) => (text === 'true' ? true : text === 'false' ? false : undefined),
    format: (value: boolean) => String(value),
  } satisfies Codec<boolean>,

  /** A calendar date, `2026-07-08` */
  date: {
    parse: (text: string) => (isDate(text) ? text : undefined),
    format: (value: string) => value,
  } satisfies Codec<string>,

  /** Two dates, `2026-05-01..2026-07-08`, the end on or after the start */
  dateRange: {
    parse(text: string) {
      const [start, end, ...rest] = text.split('..')
      if (rest.length || !start || !end || !isDate(start) || !isDate(end) || end < start) return undefined
      return { start, end }
    },
    format: (value: DateRange) => `${value.start}..${value.end}`,
  } satisfies Codec<DateRange>,

  /** A point, `at=43.0731,-89.4012`, to `digits` decimals (4 is about 10 m) */
  latLng(digits = 4): Codec<LatLng> {
    const lat = number({ digits, min: -90, max: 90 })
    const lng = number({ digits, min: -180, max: 180 })
    return {
      parse(text) {
        const parts = text.split(',')
        if (parts.length !== 2) return undefined
        const [a, b] = [lat.parse(parts[0]), lng.parse(parts[1])]
        return a === undefined || b === undefined ? undefined : { lat: a, lng: b }
      },
      format: (value) => `${lat.format(value.lat)},${lng.format(value.lng)}`,
    }
  },

  /** A list, comma-separated: an item that can't be read drops the whole list back to its default */
  list<T>(item: Codec<T>, separator = ','): Codec<T[]> {
    return {
      parse(text) {
        if (text === '') return []
        const values = text.split(separator).map((part) => item.parse(part))
        return values.some((value) => value === undefined) ? undefined : (values as T[])
      },
      format: (values) => values.map((value) => item.format(value)).join(separator),
    }
  },

  /** One of a fixed set of values, such as a layer group or `stat` */
  oneOf<const V extends string>(values: readonly V[]): Codec<V> {
    return {
      parse: (text) => (values.includes(text as V) ? (text as V) : undefined),
      format: (value) => value,
    }
  },
}

/** One setting of a view: how it's written, its default (null for "none", which is left out of the query like
 * any default) and the query parameter's name if not the setting's own (`zoom` as `z`) */
export type Field<T> = { codec: Codec<NonNullable<T>>; default: T; param?: string }
export type Fields<S> = { [K in keyof S]: Field<S[K]> }

export function field<T>(codec: Codec<NonNullable<T>>, defaultValue: T, param?: string): Field<T> {
  return { codec, default: defaultValue, param }
}

function entries<S>(fields: Fields<S>): [keyof S & string, Field<S[keyof S]>][] {
  return Object.entries(fields) as [keyof S & string, Field<S[keyof S]>][]
}

const paramOf = (key: string, spec: Field<unknown>) => spec.param ?? key

function formatted<T>(spec: Field<T>, value: T): string | null {
  return value === null || value === undefined ? null : spec.codec.format(value as NonNullable<T>)
}

/** Every setting at its default */
export function defaults<S>(fields: Fields<S>): S {
  return Object.fromEntries(entries(fields).map(([key, spec]) => [key, spec.default])) as S
}

/** The settings that differ from their defaults, as query parameters, in the order the fields are declared */
export function toQuery<S>(fields: Fields<S>, state: S): URLSearchParams {
  const query = new URLSearchParams()
  for (const [key, spec] of entries(fields)) {
    const text = formatted(spec, state[key])
    if (text !== null && text !== formatted(spec, spec.default)) query.set(paramOf(key, spec), text)
  }
  return query
}

/** The settings a query string gives; one it doesn't name, or names with a value that can't be read, is left out */
export function fromQuery<S>(fields: Fields<S>, query: string | URLSearchParams): Partial<S> {
  const search = typeof query === 'string' ? new URLSearchParams(query) : query
  const found: Partial<S> = {}
  for (const [key, spec] of entries(fields)) {
    const text = search.get(paramOf(key, spec))
    if (text === null) continue
    const value = spec.codec.parse(text)
    if (value !== undefined) found[key] = value as S[keyof S & string]
  }
  return found
}

/** The full link to a view: `path` (the current page's by default) with every setting not at its default */
export function shareUrl<S>(fields: Fields<S>, state: S, options: { path?: string; origin?: string } = {}): string {
  const path = options.path ?? window.location.pathname
  const origin = options.origin ?? window.location.origin
  const query = toQuery(fields, state).toString()
  return `${origin}${path}${query ? `?${query}` : ''}`
}

/** Replaces the address bar's URL (path, query and hash) without a request or a new history entry */
export function replaceAddress(url: string): void {
  if (window.history.state?.page) {
    router.replace({ url, preserveState: true, preserveScroll: true })
  } else {
    window.history.replaceState(window.history.state, '', url)
  }
}

export type ViewState<S> = {
  /** The view now */
  readonly value: S
  /** Whether the view came from the link the page was opened with */
  readonly fromLink: boolean
  /** Svelte's store contract, so a component reads `$view.layer` */
  subscribe(run: (value: S) => void): () => void
  set(value: S): void
  patch(changes: Partial<S>): void
  /** Every setting back to its default */
  reset(): void
  /** The link that opens this view (the Share button's) */
  shareUrl(): string
  /** Writes a change still waiting for the address bar now, and stops listening (as the page unmounts) */
  destroy(): void
}

export type ViewOptions = {
  /** What the tab's view is kept under: the page's path by default */
  key?: string
  /** The view in the address bar as it changes (D118's alternative); `STATE_IN_ADDRESS_BAR` by default */
  inAddressBar?: boolean
  /** How the address bar is changed: `replaceAddress` by default */
  writeAddress?: (url: string) => void
  /** Milliseconds to wait for changes to settle before the address bar is written (a dragged map moves often) */
  addressDelay?: number
}

/** A page's view: from the link it was opened with if that names any setting, else the tab's last view of this
 * path, else the defaults. Each change is kept for the tab at once; the address bar follows (`inAddressBar`) or,
 * after a shared link, returns to the plain path. */
export function viewState<S>(fields: Fields<S>, options: ViewOptions = {}): ViewState<S> {
  const inAddressBar = options.inAddressBar ?? STATE_IN_ADDRESS_BAR
  const writeAddress = options.writeAddress ?? replaceAddress
  const delay = options.addressDelay ?? 200
  const storageKey = `view:${options.key ?? window.location.pathname}`
  const params = new Set(entries(fields).map(([key, spec]) => paramOf(key, spec)))

  const linked = new URLSearchParams(window.location.search)
  const fromLink = [...linked.keys()].some((name) => params.has(name))
  const stored = readStored(storageKey, 'session')
  const source = fromLink ? linked : typeof stored === 'string' ? stored : ''
  let value: S = { ...defaults(fields), ...fromQuery(fields, source) }
  let written = toQuery(fields, value).toString()
  writeStored(storageKey, written, 'session')

  const listeners = new Set<(value: S) => void>()
  let timer: ReturnType<typeof setTimeout> | undefined

  // The URL with this view's parameters replaced (or removed), anything else in the query and the hash kept
  function address(): string {
    const search = new URLSearchParams(window.location.search)
    for (const name of params) search.delete(name)
    if (inAddressBar) for (const [name, text] of toQuery(fields, value)) search.set(name, text)
    const query = search.toString()
    return `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`
  }

  function flush() {
    clearTimeout(timer)
    timer = undefined
    const url = address()
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`
    if (url !== current) writeAddress(url)
  }

  function schedule() {
    clearTimeout(timer)
    timer = setTimeout(flush, delay)
  }

  // Restored from the tab with the view in the address bar: show it there
  if (inAddressBar && !fromLink && written) schedule()

  function set(next: S) {
    const query = toQuery(fields, next).toString()
    value = next
    for (const run of listeners) run(value)
    if (query === written) return
    written = query
    writeStored(storageKey, query, 'session')
    schedule()
  }

  return {
    get value() {
      return value
    },
    fromLink,
    subscribe(run) {
      listeners.add(run)
      run(value)
      return () => listeners.delete(run)
    },
    set,
    patch: (changes) => set({ ...value, ...changes }),
    reset: () => set(defaults(fields)),
    shareUrl: () => shareUrl(fields, value),
    destroy() {
      if (timer !== undefined) flush()
      listeners.clear()
    },
  }
}
