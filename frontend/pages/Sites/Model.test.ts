import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import lateBlightRun from '@/test/fixtures/site/model-late-blight.json'
import props from '@/test/fixtures/site/model-props-late-blight.json'
import type { SiteModelProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

// The API, answered from a run recorded from the dev server
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

// The saved-sites store: what the page calls of it
const store = vi.hoisted(() => ({
  saved: null as null | { key: string; lat: number; lng: number; name: string },
  options: {} as Record<string, Record<string, string>>,
  setPrefs: vi.fn(),
}))
vi.mock('@/lib/sites.svelte', () => ({
  siteAt: () => store.saved ?? undefined,
  effectivePrefs: () => ({
    crops: undefined,
    models: undefined,
    hiddenModels: [],
    options: store.options,
    planting: undefined,
  }),
  prefsAt: () => ({ options: store.options }),
  setPrefs: store.setPrefs,
}))

const { default: Model } = await import('./Model.svelte')
const { page } = await import('@/test/page.svelte')

const model = props as unknown as SiteModelProps

beforeEach(() => {
  page.props.today = '2026-11-25'
  sessionStorage.clear()
  window.history.replaceState(null, '', '/sites/44.12,-89.52/models/late-blight-dsv')
  store.saved = null
  store.options = {}
  store.setPrefs.mockReset()
  get.mockReset()
  get.mockImplementation(() => Promise.resolve(lateBlightRun))
})

describe('a model at a site', () => {
  it('leads with the answer, from a run in metric', async () => {
    render(Model, model)
    expect(screen.getByRole('heading', { level: 1, name: 'Late blight disease severity values' })).toBeInTheDocument()
    expect(
      await screen.findByText('Out of season today, Nov 25. The model runs from May 1 to Sep 30.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Last reached: High risk on Aug 19.')).toBeInTheDocument()
    expect(get).toHaveBeenCalledWith(
      '/models/late-blight-dsv/run',
      { lat: 44.12, lng: -89.52, units: 'metric' },
      expect.anything(),
    )
  })

  it('links back to the site and to the model, and tables the past week and the forecast', async () => {
    render(Model, model)
    const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' })
    expect(within(crumbs).getByRole('link', { name: 'Unsaved location' })).toHaveAttribute(
      'href',
      '/sites/44.12,-89.52',
    )
    expect(screen.getAllByRole('link', { name: /About/ })[0]).toHaveAttribute('href', '/models/late-blight-dsv')
    const table = await screen.findByRole('table', { name: /the past 7 days and the forecast/ })
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent?.trim()),
    ).toEqual([
      'Date',
      'Hours with RH ≥ 90% (h)',
      'Mean temperature during RH ≥ 90% (°F)',
      'Disease severity values',
      '2-day total',
      '7-day total',
      '14-day total',
      'Season total',
      'Risk',
    ])
    expect(within(table).getAllByRole('row')).toHaveLength(1 + 17)
    const csv = screen.getByRole('link', { name: 'Download the season as CSV' })
    expect(csv.getAttribute('href')).toMatch(
      /^\/api\/v2\/models\/late-blight-dsv\/run\?format=csv&lat=44.12&lng=-89.52&units=us$/,
    )
  })

  it('asks again for a past season, and for the extended forecast', async () => {
    render(Model, model)
    await screen.findByRole('table')
    await fireEvent.change(screen.getByRole('combobox', { name: 'Season' }), { target: { value: '2025' } })
    await vi.waitFor(() =>
      expect(get).toHaveBeenLastCalledWith(
        '/models/late-blight-dsv/run',
        expect.objectContaining({ end: '2025-09-30' }),
        expect.anything(),
      ),
    )
    await fireEvent.change(screen.getByRole('combobox', { name: 'Season' }), { target: { value: '2026' } })
    await fireEvent.click(screen.getByRole('checkbox', { name: 'Extended forecast' }))
    await vi.waitFor(() =>
      expect(get).toHaveBeenLastCalledWith(
        '/models/late-blight-dsv/run',
        expect.objectContaining({ projection: true }),
        expect.anything(),
      ),
    )
  })

  it("runs from the start date you give, kept in the page's view until the site is saved", async () => {
    render(Model, model)
    await screen.findByRole('table')
    await fireEvent.input(screen.getByLabelText(/Count from/), { target: { value: '2026-06-30' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await vi.waitFor(() =>
      expect(get).toHaveBeenLastCalledWith(
        '/models/late-blight-dsv/run',
        expect.objectContaining({ biofix: '2026-06-30' }),
        expect.anything(),
      ),
    )
    expect(store.setPrefs).not.toHaveBeenCalled()
  })

  it("keeps a saved site's settings with it", async () => {
    store.saved = { key: '44.12,-89.52', lat: 44.12, lng: -89.52, name: 'Hancock' }
    store.options = { 'late-blight-dsv': { biofix: '2026-07-04' } }
    render(Model, model)
    expect(get).toHaveBeenCalledWith(
      '/models/late-blight-dsv/run',
      expect.objectContaining({ biofix: '2026-07-04' }),
      expect.anything(),
    )
    await screen.findByRole('table')
    await fireEvent.change(screen.getByRole('combobox', { name: 'Planting date' }), { target: { value: 'early' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save settings' }))
    expect(store.setPrefs).toHaveBeenCalledWith(
      { kind: 'site', key: '44.12,-89.52' },
      { options: { 'late-blight-dsv': { biofix: '2026-07-04', planting_date: 'early' } } },
    )
  })

  it('shows how to read it, from the model’s page', () => {
    render(Model, model)
    expect(screen.getByRole('heading', { name: 'How to read it' })).toBeInTheDocument()
    expect(screen.getByText(/threshold for a first protective fungicide spray/)).toBeInTheDocument()
    expect(screen.getByText('It runs each year from May 1 to Sep 30.')).toBeInTheDocument()
  })
})
