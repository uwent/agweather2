import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ModelsResponse, PointsQuery, SeriesQuery } from '@/types/api'
import {
  ApiError,
  NETWORK_MESSAGE,
  UNREADABLE_MESSAGE,
  apiUrl,
  get,
  isAbort,
  latestRequests,
  post,
  queryString,
  retryAfterSeconds,
  warningsOf,
} from './api'

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

function json(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

const meta = { request: {}, units: {}, summary: {}, sources: [], warnings: [], attribution: '', api_version: '2.0' }

describe('queryString', () => {
  it('sorts keys, joins lists with commas and leaves out empty values', () => {
    const params: PointsQuery & SeriesQuery & { vars: string[]; roll?: number[] } = {
      lng: -89.4,
      lat: 43.07,
      points: null,
      forecast: false,
      vars: ['air_temperature_max', 'precipitation_sum'],
      roll: [],
    }
    expect(queryString(params)).toBe('forecast=false&lat=43.07&lng=-89.4&vars=air_temperature_max%2Cprecipitation_sum')
  })

  it('is empty without params', () => {
    expect(queryString()).toBe('')
    expect(queryString({ a: undefined })).toBe('')
  })
})

describe('apiUrl', () => {
  it('builds a link for a download or a tile without fetching it', () => {
    expect(apiUrl('/weather/daily', { lat: 43, lng: -89, format: 'csv' })).toBe(
      '/api/v2/weather/daily?format=csv&lat=43&lng=-89',
    )
    expect(apiUrl('/models')).toBe('/api/v2/models')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('get', () => {
  it('returns the envelope, typed, and lets the browser revalidate by ETag', async () => {
    fetchMock.mockResolvedValue(
      json({ meta: { ...meta, warnings: ['Precipitation is missing on 2 days.'] }, data: [] }),
    )
    const body = await get<ModelsResponse>('/models', { group: 'disease' })
    expect(body.data).toEqual([])
    expect(warningsOf(body)).toEqual(['Precipitation is missing on 2 days.'])
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v2/models?group=disease')
    expect(init?.cache).toBe('default')
    expect(init?.method).toBe('GET')
  })

  it('throws the first error with its code, parameter and message', async () => {
    const errors = [
      { code: 'out_of_order', param: 'end', message: 'The end date is before the start date.' },
      { code: 'unknown_parameter', param: 'start_date', message: "Use 'start'." },
    ]
    fetchMock.mockResolvedValue(json({ meta: { request: {}, api_version: '2.0' }, errors }, 422))
    const error = await get('/weather/daily').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 422,
      code: 'out_of_order',
      param: 'end',
      message: 'The end date is before the start date.',
      retryAfter: null,
      retryable: false,
    })
    expect((error as ApiError).errors).toHaveLength(2)
  })

  it('reads Retry-After on a limit or a busy server, and does not retry by itself', async () => {
    const busy = [{ code: 'busy', param: null, message: 'The server is busy. Try again in a minute.' }]
    fetchMock.mockResolvedValue(json({ meta: {}, errors: busy }, 503, { 'Retry-After': '60' }))
    const error = (await get('/grids/x').catch((e: unknown) => e)) as ApiError
    expect(error).toMatchObject({ status: 503, code: 'busy', retryAfter: 60, retryable: true })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('says in plain words when AgWeather could not be reached', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    const error = (await get('/status').catch((e: unknown) => e)) as ApiError
    expect(error).toMatchObject({ status: 0, code: 'network', message: NETWORK_MESSAGE, retryable: true })
  })

  it('reads an answer that is not JSON (a proxy page) as unavailable', async () => {
    fetchMock.mockResolvedValue(new Response('<html>Bad gateway</html>', { status: 502 }))
    const error = (await get('/status').catch((e: unknown) => e)) as ApiError
    expect(error).toMatchObject({ status: 502, code: 'unavailable', message: UNREADABLE_MESSAGE, retryable: true })
  })

  it('rejects with an AbortError when its signal aborts', async () => {
    const controller = new AbortController()
    fetchMock.mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) =>
        init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
      )
    })
    const pending = get('/status', undefined, { signal: controller.signal })
    controller.abort()
    const error = await pending.catch((e: unknown) => e)
    expect(isAbort(error)).toBe(true)
  })
})

describe('post', () => {
  it('sends a JSON body', async () => {
    fetchMock.mockResolvedValue(json({ meta, data: {} }))
    await post('/models/late-blight-dsv/evaluate', { inputs: { temperature: [10, 20] } }, { units: 'metric' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v2/models/late-blight-dsv/evaluate?units=metric')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe('{"inputs":{"temperature":[10,20]}}')
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
  })
})

describe('retryAfterSeconds', () => {
  it('reads seconds or an HTTP date', () => {
    expect(retryAfterSeconds('120')).toBe(120)
    expect(retryAfterSeconds(null)).toBeNull()
    expect(retryAfterSeconds('soon')).toBeNull()
    const now = Date.parse('2026-11-25T12:00:00Z')
    expect(retryAfterSeconds('Wed, 25 Nov 2026 12:01:30 GMT', now)).toBe(90)
  })
})

describe('latestRequests', () => {
  it('aborts the request a newer one under the same key supersedes', async () => {
    const latest = latestRequests()
    const signals: AbortSignal[] = []
    const never = (signal: AbortSignal) => {
      signals.push(signal)
      return new Promise<string>((_resolve, reject) =>
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
      )
    }
    const first = latest.run('daily', never)
    const other = latest.run('hourly', never)
    const second = latest.run('daily', async () => 'newest')
    expect(isAbort(await first.catch((e: unknown) => e))).toBe(true)
    await expect(second).resolves.toBe('newest')
    expect(signals[1].aborted).toBe(false)
    latest.cancel()
    expect(isAbort(await other.catch((e: unknown) => e))).toBe(true)
  })
})
