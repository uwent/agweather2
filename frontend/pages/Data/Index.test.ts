import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import downloads from '@/test/fixtures/downloads.json'
import layers from '@/test/fixtures/layers.json'
import variables from '@/test/fixtures/site/variables.json'
import type { DataPageProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

// The API, answered from responses recorded from the dev server
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

// Two saved sites
vi.mock('@/lib/sites.svelte', () => ({
  sites: [
    { key: '44.12,-89.52', lat: 44.12, lng: -89.52, name: 'Hancock', addedAt: '', updatedAt: '' },
    { key: '43.07,-89.4', lat: 43.07, lng: -89.4, name: '', addedAt: '', updatedAt: '' },
  ],
  siteLabel: (s: { name: string; lat: number; lng: number }) => s.name || `${s.lat}, ${s.lng}`,
}))

const { default: Index } = await import('./Index.svelte')

const ANSWERS: Record<string, unknown> = { '/variables': variables, '/layers': layers, '/downloads': downloads }

// web.datapage's props over the development archive (Wisconsin)
const props: DataPageProps = {
  limits: { text_values: 2_000_000, file_values: 22_000_000, map_days: 366, map_hours: 744, stride: 50, res: 0.025 },
  projection: { lon0: -95, lat1: 25, radius: 6371200, x0: -3271147.2882942683, y0: -263797.50271268317, dx: 2539.703 },
  models: [
    {
      id: 'late-blight-dsv',
      name: 'Late blight',
      group: 'disease',
      crops: ['potato'],
      status: 'stable',
      risk_levels: [],
    },
  ],
  areas: {
    window: [878, 1123, 1352, 1588],
    states: [{ id: 'WI', name: 'Wisconsin', state: 'WI', j0: 886, j1: 1105, i0: 1358, i1: 1562, cells: 27218 }],
    counties: [{ id: '55025', name: 'Dane County', state: 'WI', j0: 903, j1: 924, i0: 1462, i1: 1491, cells: 547 }],
  },
}

beforeEach(() => {
  get.mockReset()
  get.mockImplementation(async (path: string) => ANSWERS[path])
  sessionStorage.clear()
  window.history.replaceState(null, '', '/data')
})

describe('the data page', () => {
  it('builds a download for the saved sites chosen, as points', async () => {
    render(Index, props)
    expect(screen.getByText('No locations chosen yet.')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Choose all' }))
    expect(screen.getByText('2 locations chosen, of up to 50.')).toBeInTheDocument()
    const address = await screen.findByRole('textbox', { name: 'The request’s address, for a script' })
    expect((address as HTMLTextAreaElement).value).toContain(
      '/api/v2/weather/daily?format=csv&points=44.12%2C-89.52%3B43.07%2C-89.4&start=',
    )
    expect(screen.getByTestId('download-size')).toHaveTextContent(/^About [\d,]+ rows, about \d+ KB\.$/)
    await fireEvent.click(screen.getByRole('checkbox', { name: /Hancock/ }))
    expect((address as HTMLTextAreaElement).value).toContain('lat=43.07&lng=-89.4')
  })

  it('sizes a map file before it’s asked for, and says when the API would refuse it', async () => {
    render(Index, props)
    const maps = document.getElementById('maps')!
    await vi.waitFor(() => expect(within(maps).getByRole('combobox', { name: 'Map' })).toBeEnabled())
    expect(within(maps).getByTestId('file-size')).toHaveTextContent('About 57,820 values, about 78 KB.')
    expect(within(maps).getByRole('link', { name: 'Download NetCDF' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/api\/v2\/grids\/air_temperature_max\?date=\d{4}-\d{2}-\d{2}&format=netcdf&units=(us|metric)$/),
    )
    await fireEvent.click(within(maps).getByRole('radio', { name: 'A state' }))
    await fireEvent.click(within(maps).getByRole('radio', { name: 'CSV' }))
    await fireEvent.click(within(maps).getByRole('radio', { name: 'A range of days' }))
    await fireEvent.input(within(maps).getByLabelText('Start date'), { target: { value: '2025-06-01' } })
    await fireEvent.input(within(maps).getByLabelText('End date'), { target: { value: '2025-07-30' } })
    // The API refuses it: "This request has 2,680,560 values (60 steps × 44,676 cells); JSON and CSV hold up to 2,000,000."
    expect(within(maps).getByRole('alert')).toHaveTextContent(
      /^This request has about 2,680,560 values \(60 maps × 44,676 cells\); JSON and CSV hold up to 2,000,000\./,
    )
    expect(within(maps).queryByRole('link', { name: 'Download CSV' })).toBeNull()
    await fireEvent.click(within(maps).getByRole('checkbox', { name: /Only the cells in the area/ }))
    expect(within(maps).getByTestId('file-size')).toHaveTextContent('About 1,633,080 rows')
  })

  it('lists the yearly files by variable and year, with the current year’s last day', async () => {
    render(Index, props)
    const yearly = document.getElementById('yearly')!
    const table = await within(yearly).findByRole('table')
    expect(within(table).getByRole('columnheader', { name: /^2026/ })).toHaveTextContent('to Nov 4')
    const tmax = within(table).getByRole('row', { name: /Air temperature at 2 m, daily max/ })
    expect(within(tmax).getAllByRole('link')).toHaveLength(3)
    expect(within(tmax).getByRole('link', { name: /2025: 13 MB NetCDF/ })).toHaveAttribute(
      'href',
      'http://localhost:8000/downloads/daily/2025/air_temperature_max_2025.nc',
    )
    expect(screen.getByRole('link', { name: 'grid.nc' })).toHaveAttribute(
      'href',
      'http://localhost:8000/downloads/daily/grid.nc',
    )
    expect(screen.getByText(/library\(terra\)/)).toBeInTheDocument()
  })
})
