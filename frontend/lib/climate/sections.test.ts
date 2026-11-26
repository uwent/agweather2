// The Climate tab's sections (track 6.2), each given only a location and its settings, over answers recorded from
// the dev server at Madison (frontend/test/fixtures/climate, 2026-11-25)
import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import compare from '@/test/fixtures/climate/compare.json'
import counts from '@/test/fixtures/climate/counts.json'
import countsMonths from '@/test/fixtures/climate/counts-months.json'
import months from '@/test/fixtures/climate/months.json'
import normalSpan from '@/test/fixtures/climate/normal-span.json'
import normalYear from '@/test/fixtures/climate/normal-year.json'
import recent from '@/test/fixtures/climate/recent.json'
import presets from '@/test/fixtures/site/presets.json'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const { default: ThisSeason } = await import('./ThisSeason.svelte')
const { default: TemperatureNormal } = await import('./TemperatureNormal.svelte')
const { default: MonthCounts } = await import('./MonthCounts.svelte')
const { default: Normals } = await import('./Normals.svelte')
const { default: WaterNote } = await import('./WaterNote.svelte')
const { slots } = await import('./slots')

type Params = Record<string, unknown>
function answer(path: string, params: Params = {}): unknown {
  if (path === '/degree-days/presets') return presets
  if (path === '/climate/compare') return params.count ? counts : compare
  if (path === '/weather/daily') return recent
  if (path === '/climate/normals') {
    if (params.count) return countsMonths
    if (params.interval === 'month') return months
    return params.start ? normalSpan : normalYear
  }
  throw new Error(`no answer for ${path}`)
}

beforeEach(() => {
  get.mockReset()
  get.mockImplementation((path: string, params: Params) => Promise.resolve(answer(path, params)))
})

const today = '2026-11-25'
const place = { lat: 43.07, lng: -89.4, today }
const calls = (path: string) => get.mock.calls.filter(([p]) => p === path).map(([, params]) => params as Params)

describe('ThisSeason', () => {
  it('compares degree days and precipitation with the normal in one request', async () => {
    render(ThisSeason, place)
    expect(await screen.findByText(/^Degree days from Jan 1 through Nov 24: 3,323 °F·d\./)).toBeVisible()
    expect(screen.getByText(/^Precipitation from Jan 1 through Nov 24:/)).toBeVisible()
    expect(calls('/climate/compare')).toEqual([
      expect.objectContaining({
        dd: ['modified_50_86'],
        vars: ['precipitation_sum'],
        start: '2026-01-01',
        period: 'last30',
        units: 'us',
      }),
    ])
  })

  it('asks for a preset’s setting, a past season to its end, and the period chosen', async () => {
    render(ThisSeason, { ...place, dd: 'corn', year: 2024, start: '2024-05-01', period: 'last10' })
    await screen.findByRole('heading', { name: 'Degree days: Corn (field)' })
    expect(calls('/climate/compare').at(-1)).toMatchObject({
      dd: ['modified_50_86'],
      start: '2024-05-01',
      end: '2024-12-31',
      period: 'last10',
    })
  })

  it('reports a changed setting to its page, leaving defaults out', async () => {
    const onchange = vi.fn()
    render(ThisSeason, { ...place, onchange })
    await screen.findByText(/^Degree days from Jan 1/)
    await fireEvent.change(screen.getByRole('combobox', { name: 'Season' }), { target: { value: '2023' } })
    expect(onchange).toHaveBeenLastCalledWith({ year: 2023, start: null })
    await fireEvent.change(screen.getByRole('combobox', { name: 'Degree days' }), { target: { value: 'corn' } })
    expect(onchange).toHaveBeenLastCalledWith({ dd: 'corn' })
    await fireEvent.change(screen.getByRole('combobox', { name: 'Degree days' }), {
      target: { value: 'modified_50_86' },
    })
    expect(onchange).toHaveBeenLastCalledWith({ dd: '' })
  })
})

describe('TemperatureNormal', () => {
  it('sets the last 60 days and the forecast against their normals', async () => {
    render(TemperatureNormal, place)
    expect(
      await screen.findByText(/^Over the last 7 days \(Nov 18 to Nov 24\), highs averaged 9 °F above normal/),
    ).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Highs and lows against normal' })).toBeVisible()
    expect(calls('/weather/daily')[0]).toMatchObject({ start: '2026-09-26', units: 'us' })
    expect(calls('/climate/normals')[0]).toMatchObject({
      start: '2026-09-26',
      end: '2026-12-11',
      percentiles: [10, 90],
    })
  })

  it('asks each year’s normals apart across January 1', async () => {
    render(TemperatureNormal, { ...place, today: '2027-01-10' })
    await screen.findByRole('heading', { name: 'Highs and lows against normal' })
    expect(calls('/climate/normals').map((p) => [p.start, p.end])).toEqual([
      ['2026-11-11', '2026-12-31'],
      ['2027-01-01', '2027-01-26'],
    ])
  })
})

describe('MonthCounts', () => {
  it('counts this month’s days against normal, and a typical year by month', async () => {
    render(MonthCounts, place)
    const table = await screen.findByRole('table', { name: 'Days counted in November 2026, against normal' })
    const row = within(table).getByRole('row', { name: /^Lows of 32 °F or less/ })
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(['3', '10.4', '4–14', '4', 'Among the fewest'])
    expect(screen.getByText(/^Days in November 2026 through Nov 24, against the normal count/)).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'A typical year by month' })).toBeVisible()
    expect(calls('/climate/compare')[0]).toMatchObject({ vars: '', start: '2026-11-01', end: '2026-11-30' })
    expect(calls('/climate/normals')[0]).toMatchObject({ interval: 'month' })
  })

  it('offers this year’s months so far', async () => {
    const onchange = vi.fn()
    render(MonthCounts, { ...place, month: 7, onchange })
    await screen.findByRole('table', { name: /July 2026/ })
    expect(calls('/climate/compare')[0]).toMatchObject({ start: '2026-07-01', end: '2026-07-31' })
    const choice = screen.getByRole('combobox', { name: 'Month' })
    expect(within(choice).getAllByRole('option')).toHaveLength(11)
    await fireEvent.change(choice, { target: { value: '11' } })
    expect(onchange).toHaveBeenLastCalledWith({ month: null })
  })
})

describe('Normals', () => {
  it('tables the normals by month with the year’s, and draws one through the year', async () => {
    render(Normals, place)
    const table = await screen.findByRole('table')
    const precipitation = within(table).getByRole('row', { name: /^Precipitation \(in\)/ })
    const cells = within(precipitation)
      .getAllByRole('cell')
      .map((cell) => cell.textContent?.trim())
    expect(cells[0]).toBe('1.52')
    expect(cells.at(-1)).toBe('38.85')
    expect(await screen.findByRole('heading', { name: 'Average high: normal through the year' })).toBeVisible()
    expect(calls('/climate/normals')).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ interval: 'month' }),
        expect.objectContaining({ vars: ['air_temperature_max'], percentiles: [10, 90] }),
      ]),
    )
  })
})

describe('the sections’ requests', () => {
  it('wait for the slots they share', async () => {
    const queue = slots(1)
    let release!: () => void
    get.mockImplementationOnce(
      (path: string, params: Params) =>
        new Promise((resolve) => {
          release = () => resolve(answer(path, params))
        }),
    )
    render(Normals, { ...place, queue })
    await vi.waitFor(() => expect(get).toHaveBeenCalledTimes(1))
    expect(queue.waiting).toBe(1)
    release()
    await vi.waitFor(() => expect(get).toHaveBeenCalledTimes(2))
  })
})

describe('WaterNote', () => {
  it('notes a cell that is partly water, and nothing for one mostly land', () => {
    const { unmount } = render(WaterNote, { percent: 24 })
    expect(screen.getByRole('note')).toHaveTextContent(
      /^About 24% of this location’s 2\.5 km grid cell is open water\./,
    )
    unmount()
    render(WaterNote, { percent: 5 })
    expect(screen.queryByRole('note')).toBeNull()
  })
})
