// The climate explorer (/climate, track 6 step 6.4): a climate map from a short list, and a location's climate below
// it, over answers recorded from the dev server (the map itself a stand-in: jsdom has no WebGL)
import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import compare from '@/test/fixtures/climate/compare.json'
import counts from '@/test/fixtures/climate/counts.json'
import countsMonths from '@/test/fixtures/climate/counts-months.json'
import chances from '@/test/fixtures/climate/chances.json'
import freeze from '@/test/fixtures/climate/freeze.json'
import frost from '@/test/fixtures/climate/frost.json'
import months from '@/test/fixtures/climate/months.json'
import normalSpan from '@/test/fixtures/climate/normal-span.json'
import normalYear from '@/test/fixtures/climate/normal-year.json'
import recent from '@/test/fixtures/climate/recent.json'
import layers from '@/test/fixtures/layers.json'
import locate from '@/test/fixtures/site/locate.json'
import presets from '@/test/fixtures/site/presets.json'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})
vi.mock('@/lib/map/DataMap.svelte', () => import('@/test/FakeDataMap.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

type Params = Record<string, unknown>
function answer(path: string, params: Params = {}): unknown {
  switch (path) {
    case '/layers':
      return layers
    case '/locate':
      return locate
    case '/degree-days/presets':
      return presets
    case '/climate/compare':
      return params.count ? counts : compare
    case '/weather/daily':
      return recent
    case '/climate/normals':
      if (params.count) return countsMonths
      if (params.interval === 'month') return months
      return params.start ? normalSpan : normalYear
    case '/climate/frost':
      return frost
    case '/climate/frost/chances':
      return chances
    case '/freeze':
      return freeze
  }
  throw new Error(`no answer for ${path}`)
}

const { default: Climate } = await import('./Index.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

beforeEach(() => {
  page.props.today = '2026-07-01'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string, params: Params) => Promise.resolve(answer(path, params)))
})

const open = (query = '') => {
  window.history.replaceState(null, '', `/climate${query}`)
  return render(Climate, {})
}
const theMap = () => screen.findByTestId('data-map')

describe('the climate explorer', () => {
  it('shows the season’s degree days against normal in summer, and asks for a place', async () => {
    open()
    expect(screen.getByRole('heading', { level: 1, name: 'Climate' })).toBeVisible()
    const map = await theMap()
    expect(map.dataset.layer).toBe('degree_days')
    expect(map.dataset.time).toBe('2026-01-01..2026-11-24')
    expect(JSON.parse(map.dataset.params!)).toMatchObject({ climate: 'departure', dd: 'modified_50_86' })
    expect(screen.getByRole('radio', { name: 'Degree days since January 1' })).toBeChecked()
    // No freeze chance in July
    expect(screen.queryByRole('radio', { name: /Chance of a hard freeze/ })).toBeNull()
    expect(screen.getByRole('link', { name: 'Open in the map explorer' })).toHaveAttribute(
      'href',
      '/map?layer=degree_days&span=season&dd=modified_50_86&climate=departure',
    )
    expect(screen.queryByRole('heading', { name: /^Climate at / })).toBeNull()
    expect(screen.getByRole('link', { name: 'How normals are made' })).toHaveAttribute('href', '/methods#normals')
  })

  it('changes the map and its period, and the explorer link follows', async () => {
    open()
    await theMap()
    await fireEvent.click(screen.getByRole('radio', { name: 'Last spring frost, typical date' }))
    await fireEvent.click(screen.getByRole('radio', { name: /^10 years/ }))
    const map = await theMap()
    expect(map.dataset.layer).toBe('freeze_dates')
    expect(JSON.parse(map.dataset.params!)).toMatchObject({ output: 'last_spring_p50', period: 'last10' })
    expect(screen.getByRole('link', { name: 'Open in the map explorer' })).toHaveAttribute(
      'href',
      '/map?layer=freeze_dates&output=last_spring_p50&period=last10',
    )
  })

  it('brings up a clicked location’s value and its climate', async () => {
    open()
    await fireEvent.click(within(await theMap()).getByRole('button', { name: 'Click the map' }))
    expect(await screen.findByText('+121 °F·d')).toBeVisible()
    expect(screen.getByText(/above normal \(1996–2025\)\.$|above normal\.$/)).toBeVisible()
    expect(await screen.findByRole('heading', { level: 2, name: /^Climate at / })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'This season so far' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Open the site page' })).toHaveAttribute(
      'href',
      '/sites/44.12,-89.52?tab=climate',
    )
    expect(get).toHaveBeenCalledWith('/locate', { lat: 44.12, lng: -89.52 }, expect.anything())
  })

  it('opens a shared link on its place, map and the Climate tab’s settings', async () => {
    open('?layer=hot-days&at=43.07,-89.4&name=Madison&cperiod=last5&cvar=precipitation_sum')
    const map = await theMap()
    expect(map.dataset.layer).toBe('air_temperature_max')
    expect(JSON.parse(map.dataset.params!)).toMatchObject({ count: 'days_above_90', period: 'last5' })
    expect(await screen.findByRole('heading', { level: 2, name: 'Climate at Madison' })).toBeVisible()
    // The period's switch beside the map and the one over the sections agree
    for (const radio of screen.getAllByRole('radio', { name: /^5 years/ })) expect(radio).toBeChecked()
    expect(screen.getByRole('link', { name: 'Open the site page' })).toHaveAttribute(
      'href',
      '/sites/43.07,-89.4?tab=climate&cperiod=last5&name=Madison',
    )
  })
})
