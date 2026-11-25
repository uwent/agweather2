import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import beetle from '@/test/fixtures/models/colorado-potato-beetle.json'
import tarSpot from '@/test/fixtures/models/tar-spot.json'
import type { ModelPageProps, ModelsIndexProps } from '@/types'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})
vi.mock('@/lib/sites.svelte', () => ({ sites: [], siteLabel: () => '' }))

const { default: Index } = await import('./Index.svelte')
const { default: Show } = await import('./Show.svelte')

const catalog: ModelsIndexProps = {
  models: [
    {
      id: 'tar-spot',
      name: 'Tar spot risk',
      group: 'disease',
      crops: ['corn'],
      summary: 'Tar spot from a month of weather.',
      status: 'beta',
    },
    {
      id: 'corn-stages',
      name: 'Corn growth stages',
      group: 'crop',
      crops: ['corn'],
      summary: 'Stages.',
      status: 'beta',
    },
    { id: 'codling-moth', name: 'Codling moth', group: 'insect', crops: ['apple'], summary: 'Moths.', status: 'beta' },
  ],
  crops: [
    { id: 'corn', name: 'Corn' },
    { id: 'apple', name: 'Apple' },
  ],
  groups: [
    { id: 'disease', name: 'Diseases' },
    { id: 'insect', name: 'Insects' },
    { id: 'crop', name: 'Crop growth stages' },
  ],
}

describe('the model catalog page', () => {
  it('lists models by crop with links to their pages and a beta label', () => {
    render(Index, catalog)
    const corn = screen.getByRole('region', { name: 'Corn' })
    expect(within(corn).getByRole('link', { name: 'Tar spot risk' })).toHaveAttribute('href', '/models/tar-spot')
    expect(within(corn).getAllByText('Beta')).toHaveLength(2)
    expect(screen.getByText('3 models.')).toBeInTheDocument()
  })

  it('filters by crop and words', async () => {
    render(Index, catalog)
    await fireEvent.change(screen.getByLabelText('Crop'), { target: { value: 'apple' } })
    expect(screen.queryByRole('region', { name: 'Corn' })).toBeNull()
    expect(screen.getByRole('link', { name: 'Codling moth' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Show all models' }))
    await fireEvent.input(screen.getByLabelText('Search the models'), { target: { value: 'month' } })
    expect(screen.getByText('1 model match.')).toBeInTheDocument()
  })
})

describe('a model page', () => {
  it('shows a disease’s risk levels, season, stages, checks and sources', () => {
    render(Show, tarSpot as ModelPageProps)
    expect(screen.getByRole('heading', { level: 1, name: 'Tar spot risk' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See the map' })).toHaveAttribute('href', '/map?layer=tar-spot')
    const levels = screen.getByRole('list', { name: 'Risk levels, lowest first' })
    expect(
      within(levels)
        .getAllByRole('listitem')
        .map((li) => li.textContent?.trim()),
    ).toEqual(['Very low', 'Low', 'Moderate', 'High'])
    expect(screen.getByText('From July 1 to August 15 each year.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Corn growth stages' })).toHaveAttribute('href', '/models/corn-stages')
    expect(screen.getByRole('link', { name: 'doi:10.1038/s41598-023-44338-6' })).toHaveAttribute(
      'href',
      'https://doi.org/10.1038/s41598-023-44338-6',
    )
    expect(screen.getByRole('link', { name: 'Read the full validation report' })).toHaveAttribute(
      'href',
      expect.stringContaining('docs/validation/models/tar-spot.md'),
    )
    // The Markdown's sections, rendered on the server
    expect(screen.getByRole('heading', { level: 2, name: 'How it works' })).toBeInTheDocument()
  })

  it('shows an insect’s training area', () => {
    render(Show, beetle as ModelPageProps)
    expect(screen.getByText(/was fitted to scouting counts in commercial potato fields/)).toBeInTheDocument()
    expect(screen.getByText(/Adams County, WI/)).toBeInTheDocument()
    expect(screen.getByText(/outside that area its timing is less certain/)).toBeInTheDocument()
  })
})
