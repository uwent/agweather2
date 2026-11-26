import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import chances from '@/test/fixtures/climate/chances.json'
import locate from '@/test/fixtures/site/locate.json'
import presets from '@/test/fixtures/site/presets.json'
import compare from '@/test/fixtures/tools/compare-corn.json'
import cornRun from '@/test/fixtures/tools/corn-run.json'
import soybean from '@/test/fixtures/tools/degree-days-soybean.json'
import model from '@/test/fixtures/tools/props-corn-stages.json'
import year2012 from '@/test/fixtures/tools/year-2012.json'
import type { SiteModelInfo } from '@/types'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

// The API, answered from responses recorded from the dev server at Madison (November 25, 2026)
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const ANSWERS: Record<string, unknown> = {
  '/locate': locate,
  '/degree-days/presets': presets,
  '/models/corn-stages/run': cornRun,
  '/climate/compare': compare,
  '/climate/frost/chances': chances,
}

const { default: CropGdd } = await import('./CropGdd.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

const years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]
const props = { model: model as unknown as SiteModelInfo, years }

beforeEach(() => {
  page.props.today = '2026-11-25'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string, params?: { biofix?: string }) => {
    if (path === '/degree-days') return Promise.resolve(params?.biofix?.startsWith('2012') ? year2012 : soybean)
    return Promise.resolve(ANSWERS[path])
  })
})

const calls = (path: string) => get.mock.calls.filter(([p]) => p === path).map(([, params]) => params)

describe('the crop GDD outlook', () => {
  it('asks for a place first', () => {
    window.history.replaceState(null, '', '/tools/crop-gdd')
    render(CropGdd, props)
    expect(screen.getByRole('heading', { level: 1, name: 'Crop GDD outlook' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Settings' })).not.toBeInTheDocument()
  })

  it('runs the corn stage model through December 31 and answers with black layer’s date', async () => {
    window.history.replaceState(null, '', '/tools/crop-gdd?at=43.07,-89.4&hybrid=2700&planting=2026-05-08')
    render(CropGdd, props)
    expect(
      await screen.findByText('A 2700 GDD hybrid planted May 8 reached black layer on Sep 27.'),
    ).toBeInTheDocument()
    expect(calls('/models/corn-stages/run')[0]).toMatchObject({
      planting_date: '2026-05-08',
      black_layer_gdd: '2700',
      projection: true,
      end: '2026-12-31',
      units: 'us',
    })
    expect(calls('/climate/compare')[0]).toMatchObject({ dd: 'modified_50_86', start: '2026-05-08', vars: '' })
    expect(calls('/climate/frost/chances')[0]).toMatchObject({ thresholds: 28 })
    // The stages' table: this year, and the normal year once the normal loads
    const table = await screen.findByRole('table')
    const r6 = within(table).getByRole('row', { name: /R6 Black layer/ })
    expect(r6).toHaveTextContent('Sep 27')
    expect(await within(table).findByRole('columnheader', { name: 'Normal year' })).toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /R6 Black layer/ })).toHaveTextContent('Nov 13')
    // Corn needs no degree-day request of its own
    expect(calls('/degree-days')).toHaveLength(0)
  })

  it('plants on the typical date for the county by default', async () => {
    window.history.replaceState(null, '', '/tools/crop-gdd?at=43.07,-89.4')
    render(CropGdd, props)
    const planting = (await screen.findByLabelText('Planting date')) as HTMLInputElement
    const typical = locate.data.planting?.find((p) => p.crop === 'corn')?.typical
    await vi.waitFor(() => expect(planting.value).toBe(`2026-${typical}`))
    expect(screen.getByText(/The typical date for corn \(field\) in this county/)).toBeInTheDocument()
  })

  it('adds a past year, before our records from Open-Meteo, planted on the same day', async () => {
    window.history.replaceState(null, '', '/tools/crop-gdd?at=43.07,-89.4&hybrid=2700&planting=2026-05-08')
    render(CropGdd, props)
    await screen.findByText(/reached black layer on Sep 27/)
    const choose = screen.getByLabelText('Year to add')
    expect(within(choose).getByRole('option', { name: '2012 (Open-Meteo)' })).toBeInTheDocument()
    await fireEvent.change(choose, { target: { value: '2012' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    await vi.waitFor(() =>
      expect(calls('/degree-days')[0]).toMatchObject({ dd: 'modified_50_86', biofix: '2012-05-08', end: '2012-12-31' }),
    )
    const table = screen.getByRole('table')
    expect(await within(table).findByRole('columnheader', { name: '2012' })).toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /R6 Black layer/ })).toHaveTextContent('Sep 13')
    expect(screen.getByRole('button', { name: 'Remove 2012' })).toBeInTheDocument()
  })

  it('asks another crop for its maturity, then answers from degree days with that target', async () => {
    window.history.replaceState(null, '', '/tools/crop-gdd?at=43.07,-89.4&crop=soybean&planting=2026-05-17')
    render(CropGdd, props)
    expect(await screen.findByText(/Type the growing degree days your variety needs/)).toBeInTheDocument()
    const target = screen.getByLabelText('Maturity')
    await fireEvent.change(target, { target: { value: '2400' } })
    expect(await screen.findByText('Soybean planted May 17 reached 2,400 °F·d on Sep 10.')).toBeInTheDocument()
    expect(calls('/degree-days').at(-1)).toMatchObject({
      dd: 'modified_50_86',
      biofix: '2026-05-17',
      projection: true,
      end: '2026-12-31',
      targets: [2400],
    })
    expect(calls('/models/corn-stages/run')).toHaveLength(0)
  })

  it('refuses a freeze temperature out of range', async () => {
    window.history.replaceState(null, '', '/tools/crop-gdd?at=43.07,-89.4')
    render(CropGdd, props)
    const freeze = (await screen.findByLabelText('Fall freeze')) as HTMLInputElement
    expect(freeze.value).toBe('28')
    await fireEvent.change(freeze, { target: { value: '60' } })
    expect(screen.getByText('Choose a temperature from −20 °F to 40 °F.')).toBeInTheDocument()
  })
})
