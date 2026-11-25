import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import StaleBanner from '@/lib/components/StaleBanner.svelte'
import { addSite, groups, memoryBackend, sites, useSitesBackend } from '@/lib/sites.svelte'
import { page } from '@/test/page.svelte'

import AddSiteDialog from './AddSiteDialog.svelte'
import ImportDialog from './ImportDialog.svelte'
import StorageNotice from './StorageNotice.svelte'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

beforeEach(() => useSitesBackend(memoryBackend()))

describe('AddSiteDialog', () => {
  it('saves typed coordinates with a name', async () => {
    const onadded = vi.fn()
    render(AddSiteDialog, { open: true, onadded })
    await fireEvent.input(screen.getByLabelText(/^Name/), { target: { value: 'North field' } })
    await fireEvent.input(screen.getByLabelText(/^Latitude/), { target: { value: '43.07' } })
    await fireEvent.input(screen.getByLabelText(/^Longitude/), { target: { value: '-89.40' } })
    expect(screen.getByText('43.07° N, 89.40° W')).toBeVisible()
    await fireEvent.click(screen.getByRole('button', { name: 'Save site' }))
    expect(sites.map((s) => [s.key, s.name])).toEqual([['43.07,-89.4', 'North field']])
    expect(onadded).toHaveBeenCalled()
  })

  it('fills the coordinates from typed coordinates in the search box', async () => {
    render(AddSiteDialog, { open: true })
    await fireEvent.input(screen.getByRole('searchbox'), { target: { value: '44.1336, -89.5168' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(screen.getByLabelText(/^Latitude/)).toHaveValue('44.1336')
    expect(screen.getByLabelText(/^Longitude/)).toHaveValue('-89.5168')
  })

  it('says what to fix, and refuses a place already saved', async () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home farm' })
    render(AddSiteDialog, { open: true })
    await fireEvent.input(screen.getByLabelText(/^Latitude/), { target: { value: '95' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save site' }))
    expect(screen.getByText(/Enter a latitude from -90 to 90/)).toBeVisible()
    await fireEvent.input(screen.getByLabelText(/^Latitude/), { target: { value: '43.07' } })
    await fireEvent.input(screen.getByLabelText(/^Longitude/), { target: { value: '-89.4' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save site' }))
    expect(screen.getByRole('alert')).toHaveTextContent('You’ve already saved this location as Home farm.')
    expect(sites).toHaveLength(1)
  })
})

describe('ImportDialog', () => {
  it('adds the file’s sites and lists the rows it left out', async () => {
    render(ImportDialog, { open: true })
    const file = new File(['name,lat,lng,groups\nA,43,-89,Farm\nB,x,-89,\n'], 'sites.csv', { type: 'text/csv' })
    await fireEvent.change(screen.getByLabelText('CSV file'), { target: { files: [file] } })
    const result = await screen.findByText('Added 1 site.')
    expect(result.parentElement).toHaveTextContent(
      "Row 3 was skipped: its latitude 'x' isn’t a number in decimal degrees.",
    )
    expect(sites.map((s) => s.name)).toEqual(['A'])
    expect(groups.map((g) => g.name)).toEqual(['Farm'])
  })
})

describe('notices', () => {
  it('say when sites can’t be kept in this browser', () => {
    useSitesBackend(memoryBackend(undefined, { fail: true }))
    addSite({ lat: 43, lng: -89 })
    render(StorageNotice)
    expect(screen.getByRole('status')).toHaveTextContent(/isn’t letting AgWeather save your sites/)
  })

  it('show the stale-data banner only while data are late', () => {
    page.props.status = {
      observed_through: '2026-11-25T08:00:00Z',
      daily_through: '2026-11-24',
      forecast_cycle: '2026-11-25T06:00:00Z',
      forecast_through: '2026-12-07T06:00:00Z',
      forecast_fallback: null,
      behind: ['observed'],
      stale_sources: ['rtma'],
    }
    const { unmount } = render(StaleBanner)
    expect(screen.getByRole('status')).toHaveTextContent('the newest we have is from 2 a.m. CST, Nov 25')
    unmount()
    page.props.status = { ...page.props.status, behind: [] }
    render(StaleBanner)
    expect(screen.queryByRole('status')).toBeNull()
    page.props.status = null
  })
})
