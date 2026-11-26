import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import degreeDays from '@/test/fixtures/site/degree-days.json'
import locate from '@/test/fixtures/site/locate.json'
import presets from '@/test/fixtures/site/presets.json'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

// The API, answered from responses recorded from the dev server
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const ANSWERS: Record<string, unknown> = {
  '/locate': locate,
  '/degree-days': degreeDays,
  '/degree-days/presets': presets,
}

const { default: Index } = await import('./Index.svelte')
const { default: Calendar } = await import('./Calendar.svelte')
const { default: DegreeDays } = await import('./DegreeDays.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

beforeEach(() => {
  page.props.today = '2026-11-25'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string) => Promise.resolve(ANSWERS[path]))
})

describe('the tools index', () => {
  it('lists each tool built with the question it answers', () => {
    window.history.replaceState(null, '', '/tools')
    render(Index)
    expect(screen.getByRole('link', { name: 'Degree-day calculator' })).toHaveAttribute('href', '/tools/degree-days')
    expect(screen.getByRole('link', { name: 'Day-of-year calendar' })).toHaveAttribute('href', '/calendar')
    expect(screen.getByText(/What day of the year is a date/)).toBeInTheDocument()
  })
})

describe('the day-of-year calendar', () => {
  beforeEach(() => window.history.replaceState(null, '', '/calendar'))

  it('shows the year with today ringed and named, not by colour alone', () => {
    render(Calendar)
    const table = screen.getByRole('table', { name: 'Day of the year, 2026' })
    const today = within(table).getByTitle('Today')
    expect(today).toHaveTextContent('329 (today)')
    expect(screen.getByText(/Today, November 25, 2026, is day 329/)).toBeInTheDocument()
    expect(screen.getByText(/2026 is not a leap year/)).toBeInTheDocument()
    // A phone's two halves
    expect(screen.getByRole('table', { name: 'Day of the year, January to June 2026' })).toBeInTheDocument()
  })

  it('converts both ways and moves between years', async () => {
    render(Calendar)
    await fireEvent.input(screen.getByLabelText('Date to day of year'), { target: { value: '2028-03-01' } })
    expect(screen.getByText('March 1, 2028 is day 61 of 2028.')).toBeInTheDocument()
    await fireEvent.input(screen.getByLabelText('Day of year to date, in 2026'), { target: { value: '60' } })
    expect(screen.getByText('Day 60 of 2026 is March 1, 2026.')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Next year' }))
    expect(screen.getByRole('table', { name: 'Day of the year, 2027' })).toBeInTheDocument()
    expect(screen.getByText('Day 60 of 2027 is March 1, 2027.')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Back to 2026' }))
    expect(screen.getByRole('table', { name: 'Day of the year, 2026' })).toBeInTheDocument()
  })

  it('stops at 1900 and 2100', () => {
    window.history.replaceState(null, '', '/calendar?year=2100')
    render(Calendar)
    expect(screen.getByRole('button', { name: 'Next year' })).toBeDisabled()
    expect(screen.getByText(/2100 is not a leap year/)).toBeInTheDocument()
  })
})

describe('the degree-day calculator', () => {
  it('asks for a place first', () => {
    window.history.replaceState(null, '', '/tools/degree-days')
    render(DegreeDays)
    expect(screen.getByLabelText('Choose a place')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Setting 1' })).not.toBeInTheDocument()
    expect(get).not.toHaveBeenCalledWith('/degree-days', expect.anything(), expect.anything())
  })

  it('answers for a linked place, through a chosen end, with a link to the map', async () => {
    window.history.replaceState(
      null,
      '',
      '/tools/degree-days?at=44.12,-89.52&name=Hancock&dd=corn&season=2025&end=2025-09-30',
    )
    render(DegreeDays)
    expect(screen.getByText('Hancock')).toBeInTheDocument()
    expect(await screen.findByText(/Waushara County, WI · 44.12° N, 89.52° W/)).toBeInTheDocument()
    expect(await screen.findByRole('combobox', { name: 'Setting 1' })).toHaveValue('corn')
    expect(get).toHaveBeenCalledWith(
      '/degree-days',
      expect.objectContaining({ lat: 44.12, lng: -89.52, end: '2025-09-30', projection: null }),
      expect.anything(),
    )
    expect(screen.getByLabelText('Through')).toHaveValue('2025-09-30')
    expect(screen.getByRole('link', { name: 'See on the map' })).toHaveAttribute(
      'href',
      '/map?layer=degree_days&span=season&dd=modified_50_86&date=2025-09-30&at=44.12,-89.52',
    )
    expect(screen.getByRole('link', { name: 'Open the site page' })).toHaveAttribute(
      'href',
      '/sites/44.12,-89.52?name=Hancock',
    )
  })

  it('saves the place as a site, and picks a saved site', async () => {
    window.history.replaceState(null, '', '/tools/degree-days?at=44.12,-89.52&name=Hancock')
    render(DegreeDays)
    await fireEvent.click(screen.getByRole('button', { name: 'Save this site' }))
    expect(screen.getByText('Saved as Hancock.')).toBeInTheDocument()
    expect(store.siteAt(44.12, -89.52)?.name).toBe('Hancock')
    expect(screen.queryByRole('button', { name: 'Save this site' })).not.toBeInTheDocument()
    const chips = screen.getByRole('list', { name: 'Your sites' })
    expect(within(chips).getByRole('button', { name: 'Hancock' })).toHaveAttribute('aria-pressed', 'true')
    await fireEvent.click(screen.getByRole('button', { name: 'Change place' }))
    expect(screen.getByLabelText('Choose a place')).toBeInTheDocument()
  })
})
