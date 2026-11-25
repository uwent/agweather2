import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import daily from '@/test/fixtures/site/daily.json'
import hourly from '@/test/fixtures/site/hourly.json'
import locate from '@/test/fixtures/site/locate.json'
import risk from '@/test/fixtures/site/risk.json'
import totals from '@/test/fixtures/site/totals.json'
import type { SiteProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

// The API, answered from responses recorded from the dev server
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

// The saved-sites store (another part of the app): what the page calls of it
const store = vi.hoisted(() => ({
  saved: null as null | { key: string; lat: number; lng: number; name: string },
  addSite: vi.fn(),
}))
vi.mock('@/lib/sites.svelte', () => ({
  siteAt: () => store.saved ?? undefined,
  isSaved: () => store.saved !== null,
  addSite: store.addSite,
}))

const { default: Show } = await import('./Show.svelte')
const { page } = await import('@/test/page.svelte')

const props: SiteProps = {
  lat: 44.12,
  lng: -89.52,
  name: null,
  crops: [{ id: 'potato', name: 'Potato' }],
  models: [
    {
      id: 'potato-volunteer',
      name: 'Potato volunteer survival',
      group: 'agronomic',
      crops: ['potato'],
      status: 'beta',
      risk_levels: ['Low', 'Moderate', 'High', 'Very high'],
    },
  ],
}

const ANSWERS: Record<string, unknown> = {
  '/locate': locate,
  '/weather/hourly': hourly,
  '/weather/daily': daily,
  '/weather/totals': totals,
  '/risk': risk,
}

beforeEach(() => {
  page.props.today = '2026-11-25'
  sessionStorage.clear()
  window.history.replaceState(null, '', '/sites/44.12,-89.52')
  store.saved = null
  store.addSite.mockReset()
  get.mockReset()
  get.mockImplementation((path: string) => Promise.resolve(ANSWERS[path]))
})

describe('the site page', () => {
  it('says where the site is and whose days it uses', async () => {
    render(Show, props)
    expect(screen.getByRole('heading', { level: 1, name: 'Unsaved location' })).toBeInTheDocument()
    expect(await screen.findByText(/Waushara County, WI · 44.12° N, 89.52° W/)).toBeInTheDocument()
    expect(
      screen.getByText('Days run midnight to midnight Central Standard Time all year, as on our maps.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/2\.5 km grid cell centered at 44\.1107° N, 89\.5174° W/)).toBeInTheDocument()
    expect(await screen.findByText(/^Observed through Nov 2\d, \d+ [ap]\.m\. CST/)).toBeInTheDocument()
  })

  it("asks for the Overview's numbers in metric, and shows them in the reader's units", async () => {
    render(Show, props)
    expect(await screen.findByRole('list', { name: 'Weather for the past 7 days' })).toBeInTheDocument()
    const paths = get.mock.calls.map(([path]) => path)
    expect(paths.toSorted()).toEqual([
      '/locate',
      '/risk',
      '/weather/daily',
      '/weather/hourly',
      '/weather/totals',
      '/weather/totals',
    ])
    for (const [path, params] of get.mock.calls) if (path.startsWith('/weather')) expect(params.units).toBe('metric')
    const [, risks] = get.mock.calls.find(([path]) => path === '/risk')!
    expect(risks).toMatchObject({ lat: 44.12, lng: -89.52, date: '2026-11-25' })
    // The fixture's millimeters since January 1, in inches
    const inches = (totals.data.precipitation_sum[0] / 25.4).toFixed(2)
    await vi.waitFor(() => expect(screen.getByRole('table')).toHaveTextContent(`Since January 1${inches} in`))
  })

  it('gives the risk in words first, highest first', async () => {
    render(Show, props)
    const list = await screen.findByRole('list', { name: 'Risk today by model' })
    const items = within(list).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Very high risk: Potato volunteer survival.')
    expect(items.at(-1)).toHaveTextContent(/^Very low risk: Alfalfa weevil, /)
  })

  it("shows the API's warnings in its own words, once", async () => {
    const note =
      'Precipitation is missing on 1 day. We never estimate precipitation, so the totals count those days as no rain.'
    const noted = { ...totals, meta: { ...totals.meta, warnings: [note] } }
    get.mockImplementation((path: string) => Promise.resolve(path === '/weather/totals' ? noted : ANSWERS[path]))
    render(Show, props)
    expect(await screen.findAllByText(note)).toHaveLength(1)
  })

  it('saves an unsaved site under the name it was shared with', async () => {
    store.addSite.mockImplementation((site) => {
      store.saved = { key: '44.12,-89.52', ...site }
      return { ok: true, value: store.saved }
    })
    render(Show, { ...props, name: 'North field' })
    expect(screen.getByRole('heading', { level: 1, name: 'North field' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Save this site' }))
    expect(store.addSite).toHaveBeenCalledWith({ lat: 44.12, lng: -89.52, name: 'North field' })
    expect(await screen.findByText(/Saved as North field\./)).toBeInTheDocument()
  })

  it("shows a saved site's name, without the Save button", () => {
    store.saved = { key: '44.12,-89.52', lat: 44.12, lng: -89.52, name: 'Home farm' }
    render(Show, { ...props, name: 'Something else' })
    expect(screen.getByRole('heading', { level: 1, name: 'Home farm' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save this site' })).toBeNull()
  })

  it('says what failed, in the API’s words, and offers to try again', async () => {
    const { ApiError } = await import('@/lib/api')
    get.mockImplementation((path: string) =>
      path === '/risk'
        ? Promise.reject(
            new ApiError({
              status: 503,
              retryAfter: 30,
              errors: [{ code: 'busy', param: null, message: 'We are busy.' }],
            }),
          )
        : Promise.resolve(ANSWERS[path]),
    )
    render(Show, props)
    expect(await screen.findByRole('alert')).toHaveTextContent('We are busy. Try again in 30 seconds.')
    get.mockImplementation((path: string) => Promise.resolve(ANSWERS[path]))
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('list', { name: 'Risk today by model' })).toBeInTheDocument()
  })

  it('opens on the tab a shared link names, and asks for the weather it shows', async () => {
    window.history.replaceState(null, '', '/sites/44.12,-89.52?tab=weather&step=hourly&range=week')
    render(Show, props)
    expect(screen.getByRole('tab', { name: 'Weather' })).toHaveAttribute('aria-selected', 'true')
    await vi.waitFor(() => expect(get.mock.calls.filter(([path]) => path === '/weather/hourly')).toHaveLength(2))
    const [, params] = get.mock.calls.find(
      ([path, query]) => path === '/weather/hourly' && query.vars.includes('wind_gust'),
    )!
    expect(params).toMatchObject({ start: '2026-11-18', units: 'metric', forecast: true })
    expect(params.vars).toContain('air_temperature')
    expect(get.mock.calls.some(([path]) => path === '/risk')).toBe(false)
  })
})
