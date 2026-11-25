import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api'
import { addSite, memoryBackend, sites, useSitesBackend } from '@/lib/sites.svelte'
import { setUnitSystem } from '@/lib/unitSystem.svelte'
import type { ModelEntry } from '@/types'

import Index from './Index.svelte'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (original) => ({ ...(await original<typeof import('@/lib/api')>()), get }))

const models: ModelEntry[] = [
  {
    id: 'late-blight-dsv',
    name: 'Late blight',
    group: 'disease',
    crops: ['potato'],
    status: 'beta',
    risk_levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'],
    season: ['05-01', '09-30'],
  },
]

const risk = {
  meta: {},
  data: {
    model: ['late-blight-dsv', 'tar-spot'],
    name: ['Late blight', 'Tar spot'],
    risk_level: [3, 1],
    risk_label: ['High', 'Low'],
  },
}

function weather(points: number) {
  const data: Record<string, unknown[]> = {
    point: [],
    date: [],
    kind: [],
    air_temperature_max: [],
    air_temperature_min: [],
    precipitation_sum: [],
  }
  for (let p = 0; p < points; p++) {
    for (const [date, kind] of [
      ['2026-07-01', 'partial'],
      ['2026-07-02', 'forecast'],
    ]) {
      data.point.push(p)
      data.date.push(date)
      data.kind.push(kind)
      data.air_temperature_max.push(30)
      data.air_temperature_min.push(15)
      data.precipitation_sum.push(25.4)
    }
  }
  return { meta: {}, data }
}

beforeEach(() => {
  get.mockReset()
  get.mockImplementation((path: string, params: { points?: string }) =>
    Promise.resolve(path === '/risk' ? risk : weather(params.points!.split(';').length)),
  )
  useSitesBackend(memoryBackend())
  setUnitSystem('imperial')
})

describe('the sites page', () => {
  it('explains how to add a site when there are none', () => {
    render(Index, { models, crops: [] })
    expect(screen.getByRole('heading', { name: 'No sites yet' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
    expect(get).not.toHaveBeenCalled()
  })

  it('shows each card’s weather and top risks, the weather for several sites in one request', async () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home farm' })
    addSite({ lat: 44.5, lng: -89.5, name: 'Hancock' })
    render(Index, { models, crops: [] })
    const card = (await screen.findByRole('listitem', { name: 'Home farm' })) as HTMLElement
    expect(await within(card).findAllByText('86 °F / 59 °F', {}, { timeout: 2000 })).toHaveLength(2)
    expect(within(card).getAllByText('Precipitation 1.00 in')).toHaveLength(2)
    expect(within(card).getByText('Late blight')).toBeVisible()
    expect(within(card).getByText('High')).toBeVisible()
    const weatherCalls = get.mock.calls.filter(([path]) => path === '/weather/daily')
    expect(weatherCalls).toHaveLength(1)
    expect(weatherCalls[0][1]).toMatchObject({ points: '43.07,-89.4;44.5,-89.5', units: 'metric' })
    const riskCalls = get.mock.calls.filter(([path]) => path === '/risk')
    expect(riskCalls.map((call) => call[1])).toEqual([
      { lat: 43.07, lng: -89.4, start: '2026-06-17', models: undefined },
      { lat: 44.5, lng: -89.5, start: '2026-06-17', models: undefined },
    ])
  })

  it('offers to try again, after the wait the API asked for, when it’s busy', async () => {
    get.mockImplementation((path: string, params: { points?: string }) =>
      path === '/risk'
        ? Promise.reject(
            new ApiError({
              status: 429,
              retryAfter: 20,
              errors: [{ code: 'rate_limited', param: null, message: 'Too many requests. Please wait.' }],
            }),
          )
        : Promise.resolve(weather(params.points!.split(';').length)),
    )
    addSite({ lat: 43.07, lng: -89.4, name: 'Home farm' })
    render(Index, { models, crops: [] })
    expect(await screen.findByText('Too many requests. Please wait.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Try again in 20 s' })).toBeDisabled()
  })

  it('moves a card and keeps the order', async () => {
    addSite({ lat: 43, lng: -89, name: 'A' })
    addSite({ lat: 44, lng: -89, name: 'B' })
    render(Index, { models, crops: [] })
    await fireEvent.click(screen.getByRole('button', { name: 'Move A down' }))
    expect(sites.map((s) => s.name)).toEqual(['B', 'A'])
    expect(screen.getByRole('status', { hidden: true })).toHaveTextContent('A moved to position 2 of 2.')
    expect(screen.getByRole('button', { name: 'Move A down' })).toBeDisabled()
  })

  it('removes a site after asking', async () => {
    addSite({ lat: 43, lng: -89, name: 'A' })
    render(Index, { models, crops: [] })
    await fireEvent.click(screen.getByRole('button', { name: 'Remove A' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Remove A' }))
    expect(sites).toHaveLength(0)
    expect(screen.getByRole('heading', { name: 'No sites yet' })).toBeVisible()
  })
})
