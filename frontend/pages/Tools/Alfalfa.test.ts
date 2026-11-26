import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import planCuts from '@/test/fixtures/alfalfa/plan-cuts.json'
import plan from '@/test/fixtures/alfalfa/plan.json'
import runCut from '@/test/fixtures/alfalfa/run-cut.json'
import locate from '@/test/fixtures/site/locate.json'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

// The API, answered from responses recorded from the dev server at Madison on November 26, 2026
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const { default: Alfalfa } = await import('./Alfalfa.svelte')
const { default: Index } = await import('./Index.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

const years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]

beforeEach(() => {
  page.props.today = '2026-11-26'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string, params?: { cuts?: string[] }) => {
    if (path === '/locate') return Promise.resolve(locate)
    if (path === '/models/alfalfa-growth/run') return Promise.resolve(runCut)
    if (path === '/models/alfalfa-growth/plan') return Promise.resolve(params?.cuts ? planCuts : plan)
    return Promise.reject(new Error(`unexpected ${path}`))
  })
})

const asked = (path: string) => get.mock.calls.filter(([p]) => p === path).map(([, params]) => params)

describe('the alfalfa planner', () => {
  it('is on the tools index', () => {
    window.history.replaceState(null, '', '/tools')
    render(Index)
    expect(screen.getByRole('link', { name: 'Alfalfa cutting planner' })).toHaveAttribute('href', '/tools/alfalfa')
  })

  it('asks for a place first', () => {
    window.history.replaceState(null, '', '/tools/alfalfa')
    render(Alfalfa, { years })
    expect(screen.getByRole('heading', { name: 'Alfalfa growth and cutting planner', level: 1 })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Season plan' })).toBeNull()
    expect(asked('/models/alfalfa-growth/plan')).toEqual([])
  })

  it('answers growth since the cut and lays out the plan', async () => {
    window.history.replaceState(null, '', '/tools/alfalfa?at=43.07,-89.4&cut=2026-08-15')
    render(Alfalfa, { years })
    expect(await screen.findByText(/^Alfalfa here has had 2,047 GDD since the cut on August 15/)).toBeVisible()
    expect(screen.getByText(/reached the cutting window \(900 GDD\) on September 12/)).toBeVisible()
    expect(asked('/models/alfalfa-growth/run')).toEqual([
      expect.objectContaining({ biofix: '2026-08-15', projection: true, end: '2026-12-31', units: 'us' }),
    ])

    const cards = await screen.findAllByRole('heading', { level: 3, name: /^Cut \d$/ })
    expect(cards.map((h) => h.textContent)).toEqual(['Cut 1', 'Cut 2', 'Cut 3', 'Cut 4', 'Cut 5'])
    expect(
      screen.getByText('Cut 1, June 7: 987 GDD in 61 days since the season began, in the cutting window.'),
    ).toBeVisible()
    expect(screen.getByText(/the date by which 1 year in 10 has had its first fall killing freeze/)).toBeVisible()
    expect(screen.getByText(/^With the last cut on November 1/)).toBeVisible()
    expect(asked('/models/alfalfa-growth/plan')).toEqual([
      expect.objectContaining({ lat: 43.07, lng: -89.4, interval: 1000, units: 'us' }),
    ])
    expect(screen.getByRole('link', { name: 'Alfalfa growth on the map' })).toHaveAttribute(
      'href',
      '/map?layer=alfalfa-growth&at=43.07,-89.4',
    )
  })

  it('holds a cut and checks the plan’s own dates', async () => {
    window.history.replaceState(null, '', '/tools/alfalfa?at=43.07,-89.4')
    render(Alfalfa, { years })
    const hold = await screen.findByRole('button', { name: 'Hold cut 2 in place' })
    expect(hold).toHaveAttribute('aria-pressed', 'false')
    await fireEvent.click(hold)
    await vi.waitFor(() =>
      expect(asked('/models/alfalfa-growth/plan').at(-1)).toMatchObject({
        cuts: ['2026-06-07', '2026-07-11', '2026-08-10', '2026-09-11', '2026-11-01'],
        held: ['2026-07-11'],
      }),
    )
    // The checked plan comes back with July 10 held
    expect(await screen.findByText(/^Cut 2, July 10: 1,118 GDD .* Held in place\.$/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Hold cut 2 in place' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('moves a date and removes a cut', async () => {
    window.history.replaceState(null, '', '/tools/alfalfa?at=43.07,-89.4')
    render(Alfalfa, { years })
    const date = await screen.findByLabelText('Cut 1 date')
    await fireEvent.change(date, { target: { value: '2026-06-01' } })
    await vi.waitFor(() =>
      expect(asked('/models/alfalfa-growth/plan').at(-1)).toMatchObject({
        cuts: ['2026-06-01', '2026-07-11', '2026-08-10', '2026-09-11', '2026-11-01'],
      }),
    )
    await screen.findByText(/^Cut 1, June 1:/)
    await fireEvent.click(screen.getByRole('button', { name: 'Remove cut 3' }))
    await vi.waitFor(() =>
      expect(asked('/models/alfalfa-growth/plan').at(-1)).toMatchObject({
        cuts: ['2026-06-01', '2026-07-10', '2026-10-01'],
        held: ['2026-07-10'],
      }),
    )
  })

  it('schedules again by a number of cuts, keeping held cuts', async () => {
    window.history.replaceState(null, '', '/tools/alfalfa?at=43.07,-89.4&held=2026-07-11')
    render(Alfalfa, { years })
    await screen.findAllByRole('heading', { level: 3, name: /^Cut \d$/ })
    const settings = screen.getByRole('group', { name: 'Schedule by' })
    await fireEvent.click(within(settings).getByRole('radio', { name: 'Number of cuts' }))
    await fireEvent.change(within(settings).getByRole('combobox', { name: 'Number of cuts' }), {
      target: { value: '3' },
    })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await vi.waitFor(() =>
      expect(asked('/models/alfalfa-growth/plan').at(-1)).toMatchObject({ count: 3, held: ['2026-07-11'] }),
    )
    expect(asked('/models/alfalfa-growth/plan').at(-1)).not.toHaveProperty('interval')
  })
})
