import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import chances from '@/test/fixtures/climate/chances.json'
import freeze from '@/test/fixtures/climate/freeze.json'
import frost from '@/test/fixtures/climate/frost.json'
import locate from '@/test/fixtures/site/locate.json'
import presets from '@/test/fixtures/site/presets.json'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

// The API, answered from responses recorded from the dev server at Madison
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const daily = {
  meta: { warnings: [], sources: ['nbm'] },
  data: {
    date: ['2026-11-25', '2026-11-26', '2026-11-27'],
    kind: ['partial', 'forecast', 'forecast'],
    air_temperature_min: [28.9, 37.0, 36.0],
  },
}
const pastYear = {
  ...freeze,
  meta: { ...freeze.meta, sources: ['openmeteo'] },
  data: {
    ...freeze.data,
    last_spring: ['2010-04-09', '2010-03-29', '2010-03-26'],
    first_fall: ['2010-10-29', '2010-11-05', '2010-11-23'],
  },
}

const ANSWERS: Record<string, unknown> = {
  '/locate': locate,
  '/degree-days/presets': presets,
  '/freeze': freeze,
  '/climate/frost': frost,
  '/climate/frost/chances': chances,
  '/weather/daily': daily,
}

const { default: Freeze } = await import('./Freeze.svelte')
const { default: Index } = await import('./Index.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

const years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]

beforeEach(() => {
  page.props.today = '2026-11-25'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string, params?: { start?: string }) =>
    Promise.resolve(path === '/freeze' && params?.start === '2010-01-01' ? pastYear : ANSWERS[path]),
  )
})

const asked = (path: string) => get.mock.calls.filter(([p]) => p === path).map(([, params]) => params)

describe('the freeze tool', () => {
  it('is on the tools index', () => {
    window.history.replaceState(null, '', '/tools')
    render(Index)
    expect(screen.getByRole('link', { name: 'Freeze dates and odds' })).toHaveAttribute('href', '/tools/freeze')
  })

  it('asks for a place first', () => {
    window.history.replaceState(null, '', '/tools/freeze')
    render(Freeze, { years })
    expect(screen.getByRole('heading', { name: 'Freeze dates and odds', level: 1 })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Look up a date' })).toBeNull()
    expect(get).not.toHaveBeenCalledWith('/freeze', expect.anything(), expect.anything())
  })

  it('answers this fall’s first freeze against the typical date, a row per threshold, each asked once', async () => {
    window.history.replaceState(null, '', '/tools/freeze?at=43.07,-89.4')
    render(Freeze, { years })
    expect(
      await screen.findByText(
        'This fall’s first frost (32 °F) came on November 14, 24 days later than typical (October 21).',
      ),
    ).toBeVisible()
    const rows = screen.getAllByRole('listitem').filter((li) => within(li).queryByRole('heading', { level: 3 }))
    expect(rows.map((li) => within(li).getByRole('heading').textContent)).toEqual([
      'Frost (32 °F)',
      'Hard freeze (28 °F)',
      'Killing freeze (24 °F)',
    ])
    const frostRow = within(rows[0])
    expect(frostRow.getByText('2026: Apr 7')).toBeVisible()
    expect(frostRow.getByText('2026: Nov 14')).toBeVisible()
    expect(frostRow.getByText('Typical Oct 21; 1 year in 10 before Oct 3, 1 year in 10 after Nov 9')).toBeVisible()
    expect(frostRow.getByText('2026: 221 days')).toBeVisible()
    expect(frostRow.getByText('Typical 186 days; 161 to 216 in 8 years of 10')).toBeVisible()
    // Each answer asked once: the page and the odds chart share the period's
    expect(asked('/freeze')).toEqual([
      expect.objectContaining({ start: '2026-01-01', thresholds: [32, 28, 24], units: 'us' }),
    ])
    expect(asked('/climate/frost')).toHaveLength(1)
    expect(asked('/climate/frost/chances')).toHaveLength(1)
    expect(await screen.findByRole('heading', { name: 'Chance of a freeze by date' })).toBeVisible()
    // Look up a date: today, in fall
    expect(screen.getByText(/first frost \(32 °F\) by November 25/)).toBeVisible()
    // The map, at the place
    expect(screen.getByRole('link', { name: /typical first fall frost/ })).toHaveAttribute(
      'href',
      '/map?layer=freeze_dates&output=first_fall_p50&threshold=32&at=43.07,-89.4',
    )
  })

  it('takes a crop’s killing freeze and the period', async () => {
    window.history.replaceState(null, '', '/tools/freeze?at=43.07,-89.4&temps=crop&crop=alfalfa&period=last10')
    render(Freeze, { years })
    expect(await screen.findByText(/Alfalfa: 24 °F or colder\./)).toBeVisible()
    await vi.waitFor(() => expect(asked('/freeze').at(-1)).toMatchObject({ thresholds: [24] }))
    await vi.waitFor(() => expect(asked('/climate/frost').at(-1)).toMatchObject({ thresholds: [24], period: 'last10' }))
  })

  it('names a year before our records as Open-Meteo’s', async () => {
    window.history.replaceState(null, '', '/tools/freeze?at=43.07,-89.4&year=2010')
    render(Freeze, { years })
    expect(await screen.findByText(/^In 2010, the last frost \(32 °F\) of spring came on April 9/)).toBeVisible()
    expect(screen.getByText(/Our own records begin in 2016, so 2010’s dates come from Open-Meteo/)).toBeVisible()
    expect(asked('/freeze')).toEqual([expect.objectContaining({ start: '2010-01-01', end: '2010-12-31' })])
    // No forecast for a past year
    expect(asked('/weather/daily')).toEqual([])
    expect(screen.getByRole('option', { name: '2010 (Open-Meteo)' })).toBeInTheDocument()
  })

  it('says what’s wrong with a temperature of the reader’s own', async () => {
    window.history.replaceState(null, '', '/tools/freeze?at=43.07,-89.4&temps=custom')
    render(Freeze, { years })
    expect(await screen.findByText('Choose a crop or a temperature below to see its freeze dates.')).toBeVisible()
    const box = screen.getByRole('textbox', { name: 'Temperature' })
    await fireEvent.change(box, { target: { value: '55' } })
    expect(screen.getByText('Choose a temperature from −20 °F to 40 °F.')).toBeVisible()
    await fireEvent.change(box, { target: { value: '30' } })
    await vi.waitFor(() => expect(asked('/freeze').at(-1)).toMatchObject({ thresholds: [30] }))
  })
})
