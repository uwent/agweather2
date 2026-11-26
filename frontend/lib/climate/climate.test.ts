// The shared climate components (track 6.1), over answers recorded from the dev server at Madison
// (frontend/test/fixtures/climate): no page shows them yet, so these tests stand in for one.
import { render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { compareTable } from '@/lib/charts/climateCharts'
import chances from '@/test/fixtures/climate/chances.json'
import compare from '@/test/fixtures/climate/compare.json'
import freeze from '@/test/fixtures/climate/freeze.json'
import frost from '@/test/fixtures/climate/frost.json'
import type { TableResponse } from '@/types/api'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const { default: FreezeOdds } = await import('./FreezeOdds.svelte')
const { default: CompareChart } = await import('./CompareChart.svelte')

const ANSWERS: Record<string, unknown> = {
  '/climate/frost': frost,
  '/climate/frost/chances': chances,
  '/freeze': freeze,
}

beforeEach(() => {
  get.mockReset()
  get.mockImplementation((path: string) => Promise.resolve(ANSWERS[path]))
})

const today = '2026-11-25'

describe('FreezeOdds', () => {
  it('tables each threshold’s early, typical and late dates beside this year’s', async () => {
    render(FreezeOdds, { lat: 43.07, lng: -89.4, today })
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Freeze dates over the 30 years from 1996 to 2025, and 2026’s own.')).toBeVisible()
    const frostRow = within(table).getByRole('row', { name: /^Frost \(32 °F\)/ })
    const cells = within(frostRow)
      .getAllByRole('cell')
      .map((cell) => cell.textContent?.trim())
    // Spring: early, typical, late, 2026; fall: the same; then the season's typical length and its range
    expect(cells).toEqual(['Apr 6', 'Apr 17', 'May 3', 'Apr 7', 'Oct 3', 'Oct 21', 'Nov 9', 'Nov 14', '186 161–216'])
    expect(within(table).getByRole('rowheader', { name: 'Killing freeze (24 °F)' })).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'Chance of a freeze by date' })).toBeVisible()
  })

  it('asks in °F for the period and thresholds given, and the year’s dates from January 1', async () => {
    render(FreezeOdds, { lat: 43.07, lng: -89.4, today, period: 'last10', thresholds: [32, 26], show: 'fall' })
    await screen.findByRole('table')
    const asked = Object.fromEntries(get.mock.calls.map(([path, params]) => [path, params]))
    expect(asked['/climate/frost']).toMatchObject({ period: 'last10', thresholds: [32, 26], units: 'us' })
    expect(asked['/climate/frost/chances']).toMatchObject({ period: 'last10', units: 'us' })
    expect(asked['/freeze']).toMatchObject({ start: '2026-01-01', end: undefined, units: 'us' })
    // Fall only: no spring columns
    expect(screen.queryByText('Last freeze in spring')).toBeNull()
    expect(screen.getByText('First freeze in fall')).toBeVisible()
  })

  it('shows a past year’s dates in full, and none without a year', async () => {
    render(FreezeOdds, { lat: 43.07, lng: -89.4, today, thisYear: 2024 })
    await screen.findByRole('table')
    const freezeCall = get.mock.calls.find(([path]) => path === '/freeze')!
    expect(freezeCall[1]).toMatchObject({ start: '2024-01-01', end: '2024-12-31' })
    get.mockClear()
    render(FreezeOdds, { lat: 43.07, lng: -89.4, today, thisYear: null })
    await screen.findAllByRole('table')
    expect(get.mock.calls.some(([path]) => path === '/freeze')).toBe(false)
  })

  it('says what went wrong when the API refuses', async () => {
    const { ApiError } = await import('@/lib/api')
    get.mockImplementation((path: string) =>
      path === '/climate/frost'
        ? Promise.reject(
            new ApiError({
              status: 503,
              errors: [{ code: 'busy', param: null, message: 'The server is busy. Try again in a minute.' }],
            }),
          )
        : Promise.resolve(ANSWERS[path]),
    )
    render(FreezeOdds, { lat: 43.07, lng: -89.4, today })
    expect(await screen.findByRole('alert')).toHaveTextContent('The server is busy.')
  })
})

describe('CompareChart', () => {
  it('leads with the comparison in words over its chart', () => {
    const table = compareTable(compare as unknown as TableResponse)
    render(CompareChart, {
      table,
      column: 'dd_modified_50_86',
      label: 'Degree days',
      today,
      title: 'Degree days against normal',
    })
    expect(screen.getByText(/^Degree days from Jan 1 through Nov 24: 3,323 °F·d\./)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Degree days against normal' })).toBeVisible()
  })
})
