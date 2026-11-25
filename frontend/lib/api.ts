// The site's one client for the public API, /api/v2 (D117): pages take their content as Inertia props and their
// data (weather, model runs, risk, tiles, climate) from here, so every number on a page is the API's number.
//
// Answers are the API's envelope, `{meta, data}`, typed by the response schemas `bin/types` generates
// (`@/types/api`); a failure is `{meta, errors}`, thrown here as an `ApiError`. `meta.warnings` are public
// sentences, shown as they are. Caching is the browser's: every answer carries an ETag and
// `Cache-Control: public, no-cache`, so a repeated request is revalidated with `If-None-Match` and a 304 comes
// back as the kept answer, without this module doing anything. Nothing is retried on its own: a 429 or 503 says
// when to try again (`ApiError.retryAfter`), and the page offers the reader a retry rather than adding load to a
// server that has just said it's busy.

import type { ErrorItem, ErrorResponse, Meta } from '@/types/api'

export const API_BASE = '/api/v2'

/** A value a query parameter takes: a list is sent comma-separated, as the API reads lists (`vars=a,b`);
 * null and undefined are left out, so a parameter at its default isn't sent */
export type QueryScalar = string | number | boolean
export type QueryValue = QueryScalar | readonly QueryScalar[] | null | undefined
export type QueryParams<P> = { [K in keyof P]: QueryValue }

/** The query string for params, without the `?`: keys sorted, so the same request is always the same URL
 * (and the browser's cache finds it), empty values and empty lists left out */
export function queryString<P extends QueryParams<P>>(params?: P): string {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const key of Object.keys(params).sort()) {
    const value = params[key as keyof P] as QueryValue
    if (value === null || value === undefined) continue
    if (Array.isArray(value)) {
      if (value.length) search.set(key, value.map(String).join(','))
    } else {
      search.set(key, String(value))
    }
  }
  return search.toString()
}

/** The full URL of an endpoint with its query, for a link, a download (CSV, NetCDF, GeoTIFF) or a tile, which
 * the browser fetches itself. `path` starts with a slash, as the API docs give it ('/weather/daily'). */
export function apiUrl<P extends QueryParams<P>>(path: string, params?: P): string {
  const query = queryString(params)
  return `${API_BASE}${path}${query ? `?${query}` : ''}`
}

// What a reader sees when no answer came back at all: written as the API's own messages are (CLAUDE.md)
export const NETWORK_MESSAGE = "We couldn't reach AgWeather. Check your internet connection, then try again."
export const UNREADABLE_MESSAGE =
  'AgWeather sent an answer we couldn’t read. Please try again in a few minutes, and contact us if it continues.'

/** A request the API refused or couldn't answer: the first of its `errors` (each with a public `message`), the
 * HTTP status (0 when nothing came back), and `retryAfter`, seconds, when the API says when to try again
 * (429 `rate_limited` and `too_many_running`; 503 `busy`, `timeout`, `weather_unavailable`; 502 or 504
 * `unavailable`) */
export class ApiError extends Error {
  readonly code: string
  readonly param: string | null
  readonly status: number
  readonly retryAfter: number | null
  readonly errors: ErrorItem[]
  readonly meta: ErrorResponse['meta'] | null

  constructor(options: {
    status: number
    errors: ErrorItem[]
    retryAfter?: number | null
    meta?: ErrorResponse['meta'] | null
  }) {
    const first = options.errors[0] ?? { code: 'error', param: null, message: UNREADABLE_MESSAGE }
    super(first.message)
    this.name = 'ApiError'
    this.code = first.code
    this.param = first.param
    this.status = options.status
    this.retryAfter = options.retryAfter ?? null
    this.errors = options.errors
    this.meta = options.meta ?? null
  }

  /** Whether the same request could succeed later (the network, a limit, a busy or unavailable server), so a
   * page offers "Try again" rather than asking the reader to change something */
  get retryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500
  }
}

/** Whether a thrown value is a request cancelled by its signal (a newer one superseded it), which a page ignores */
export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

/** `Retry-After` in seconds: the API sends seconds; an HTTP date is read too */
export function retryAfterSeconds(header: string | null, now: number = Date.now()): number | null {
  if (!header) return null
  const text = header.trim()
  if (/^\d+$/.test(text)) return Number(text)
  const when = Date.parse(text)
  return Number.isNaN(when) ? null : Math.max(0, Math.ceil((when - now) / 1000))
}

export type RequestOptions = {
  /** Cancels the request; a cancelled request rejects with an AbortError (`isAbort`) */
  signal?: AbortSignal
}

/** A JSON endpoint's answer, as its response type says: the envelope (`{meta, data}`) for most, a plain body for
 * the few that aren't (`/palettes`, a TileJSON). Throws `ApiError` on a refusal or a failure. */
export async function get<R>(path: string, params?: object, options: RequestOptions = {}): Promise<R> {
  return request<R>(apiUrl(path, params as QueryParams<object>), { method: 'GET', signal: options.signal })
}

/** POSTs a JSON body (a model run on your weather, `/models/{id}/evaluate`) and reads the answer as `get` does */
export async function post<R>(path: string, body: unknown, params?: object, options: RequestOptions = {}): Promise<R> {
  return request<R>(apiUrl(path, params as QueryParams<object>), {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    signal: options.signal,
  })
}

async function request<R>(url: string, init: RequestInit): Promise<R> {
  let response: Response
  try {
    // 'default': the browser revalidates the kept answer by its ETag (Cache-Control: no-cache) and a 304
    // comes back here as that answer with status 200
    response = await fetch(url, { ...init, cache: 'default', headers: { Accept: 'application/json', ...init.headers } })
  } catch (error) {
    if (isAbort(error) || init.signal?.aborted) throw abortError(error)
    throw new ApiError({ status: 0, errors: [{ code: 'network', param: null, message: NETWORK_MESSAGE }] })
  }
  const retryAfter = retryAfterSeconds(response.headers.get('Retry-After'))
  let body: unknown
  try {
    body = await response.json()
  } catch (error) {
    if (isAbort(error) || init.signal?.aborted) throw abortError(error)
    // Caddy's own pages, a proxy's, or a cut-off answer
    const code = response.ok ? 'unreadable' : response.status >= 500 ? 'unavailable' : 'error'
    throw new ApiError({
      status: response.status,
      retryAfter,
      errors: [{ code, param: null, message: UNREADABLE_MESSAGE }],
    })
  }
  if (!response.ok) {
    const failure = body as Partial<ErrorResponse> | null
    const errors = Array.isArray(failure?.errors) && failure.errors.length ? failure.errors : []
    throw new ApiError({ status: response.status, retryAfter, errors, meta: failure?.meta ?? null })
  }
  return body as R
}

function abortError(error: unknown): DOMException {
  return isAbort(error) ? (error as DOMException) : new DOMException('The request was cancelled.', 'AbortError')
}

/** `meta.warnings` of an envelope, or none: public sentences to show as they are */
export function warningsOf(body: { meta?: Pick<Meta, 'warnings'> | null } | null | undefined): string[] {
  return body?.meta?.warnings ?? []
}

/** "Latest request wins" by key: each `run(key, …)` aborts the one still running under that key, so a page that
 * refetches as the reader changes a setting never shows an older answer over a newer one.
 *
 *   const latest = latestRequests()
 *   const body = await latest.run('daily', (signal) => get<TableResponse>('/weather/daily', params, { signal }))
 *
 * A superseded call rejects with an AbortError (`isAbort`); `cancel()` aborts everything, as a page unmounts. */
export function latestRequests() {
  const running = new Map<string, AbortController>()
  return {
    run<T>(key: string, start: (signal: AbortSignal) => Promise<T>): Promise<T> {
      running.get(key)?.abort()
      const controller = new AbortController()
      running.set(key, controller)
      return start(controller.signal).finally(() => {
        if (running.get(key) === controller) running.delete(key)
      })
    },
    cancel(key?: string): void {
      for (const [name, controller] of running) {
        if (key === undefined || name === key) {
          controller.abort()
          running.delete(name)
        }
      }
    },
  }
}
