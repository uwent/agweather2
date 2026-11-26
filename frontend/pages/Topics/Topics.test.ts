import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import methods from '@/test/fixtures/methods.json'
import lateBlight from '@/test/fixtures/topics/late-blight.json'
import type { MethodsProps, TopicPageProps, TopicsIndexProps } from '@/types'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

const { default: Index } = await import('./Index.svelte')
const { default: Show } = await import('./Show.svelte')
const { default: Methods } = await import('../Methods.svelte')

const index: TopicsIndexProps = {
  topics: [
    { id: 'corn', title: 'Corn', kind: 'crop', scientific_name: 'Zea mays', crops: ['corn'] },
    { id: 'tar-spot', title: 'Tar Spot', kind: 'disease', scientific_name: 'Phyllachora maydis', crops: ['corn'] },
    { id: 'codling-moth', title: 'Codling Moth', kind: 'insect', scientific_name: 'Cydia pomonella', crops: ['apple'] },
  ],
  crops: [
    { id: 'corn', name: 'Corn' },
    { id: 'apple', name: 'Apple' },
  ],
  kinds: [
    { id: 'crop', name: 'The crop' },
    { id: 'disease', name: 'Diseases' },
    { id: 'insect', name: 'Insects' },
  ],
}

describe('the topics index', () => {
  it('lists topics by crop and kind, with links to their pages', async () => {
    render(Index, index)
    const corn = screen.getByRole('region', { name: 'Corn' })
    expect(within(corn).getByRole('link', { name: 'Tar Spot' })).toHaveAttribute('href', '/topics/tar-spot')
    expect(within(corn).getByRole('region', { name: 'Diseases' })).toBeInTheDocument()
    expect(screen.getByText('3 topics.')).toBeInTheDocument()
    await fireEvent.change(screen.getByLabelText('Crop'), { target: { value: 'apple' } })
    expect(screen.queryByRole('region', { name: 'Corn' })).toBeNull()
    expect(screen.getByText('1 topic match.')).toBeInTheDocument()
  })
})

describe('a topic page', () => {
  it('shows its text, photo, draft note, models and numbered sources', () => {
    const props = lateBlight as TopicPageProps
    render(Show, props)
    expect(screen.getByRole('heading', { level: 1, name: props.title })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Late blight spots on potato leaves' })).toHaveAttribute(
      'src',
      '/static/content/images/late-blight.jpg',
    )
    expect(screen.getByText('Draft.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Identification' })).toBeInTheDocument()
    const models = screen.getByRole('list', { name: `Models for ${props.title}` })
    expect(
      within(models).getByRole('link', { name: 'See the map of Late blight disease severity values' }),
    ).toHaveAttribute('href', '/map?layer=late-blight-dsv')
    // A footnote marker is a numbered link to its source in the list
    const first = props.sources[0]
    expect(screen.getAllByRole('link', { name: 'Source 1' })[0]).toHaveAttribute('href', `#source-${first.key}`)
    expect(document.getElementById(`source-${first.key}`)?.textContent).toContain(first.text)
  })
})

describe('the methods page', () => {
  it('lists the sources by use, the corrections with scores, and every variable with its anchor', () => {
    render(Methods, methods as MethodsProps)
    expect(screen.getByRole('heading', { level: 1, name: 'Methods' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'The forecast' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Solar radiation in the archive' })).toBeInTheDocument()
    expect(screen.getByText(/2\.8 MJ\/m² before the correction, 1\.66 MJ\/m² after/)).toBeInTheDocument()
    expect(document.getElementById('variable-air_temperature_min')).not.toBeNull()
    expect(document.getElementById('variable-hourly-precipitation')).not.toBeNull()
    expect(document.getElementById('variable-total-precipitation')).not.toBeNull()
    expect(screen.getByText(/midnight to midnight Central Standard Time \(CST\) all year, 06:00 to 06:00 UTC/))
  })
})
