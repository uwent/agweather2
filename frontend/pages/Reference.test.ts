// The reference pages (track 7 step 7.4): a page of text from content/pages (Content.svelte) and the glossary
import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import { GLOSSARY } from '@/lib/glossary'
import type { ContentPageProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

const { default: Content } = await import('./Content.svelte')
const { default: Glossary } = await import('./Glossary.svelte')

const about: ContentPageProps = {
  id: 'about',
  title: 'About AgWeather',
  summary: 'A free weather service.',
  draft: true,
  updated: '2026-11-26',
  sections: [
    { id: 'introduction', title: '', html: '<p>AgWeather is a free weather service.</p>' },
    { id: 'who-runs-it', title: 'Who runs it', html: '<p>The Department of Entomology.</p>' },
    { id: 'privacy', title: 'Privacy', html: '<p>Your sites stay in <a href="/sites">your browser</a>.</p>' },
  ],
}

describe('a page of text', () => {
  it('shows its title, draft note, sections, contents and date', () => {
    render(Content, about)
    expect(screen.getByRole('heading', { level: 1, name: 'About AgWeather' })).toBeInTheDocument()
    expect(screen.getByText('Draft.')).toBeInTheDocument()
    expect(screen.getByText('AgWeather is a free weather service.')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Privacy' })).toHaveAttribute('id', 'privacy')
    const contents = screen.getByRole('navigation', { name: 'On this page' })
    expect(within(contents).getByRole('link', { name: 'Who runs it' })).toHaveAttribute('href', '#who-runs-it')
    expect(screen.getByText('This page’s text was last changed on November 26, 2026.')).toBeInTheDocument()
  })

  it('has no draft note once reviewed, and no contents for one section', () => {
    render(Content, { ...about, draft: false, sections: about.sections.slice(0, 2) })
    expect(screen.queryByText('Draft.')).toBeNull()
    expect(screen.queryByRole('navigation', { name: 'On this page' })).toBeNull()
  })
})

describe('the glossary page', () => {
  it('lists every term A–Z under its letter, each at its own anchor', () => {
    const { container } = render(Glossary)
    expect(screen.getByText(`${GLOSSARY.length} terms.`)).toBeInTheDocument()
    const terms = [...container.querySelectorAll('dt')].map((dt) => dt.textContent ?? '')
    expect(terms).toEqual([...terms].sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' })))
    expect(container.querySelector('#biofix dt')).toHaveTextContent('Biofix')
    expect(within(screen.getByRole('region', { name: 'B' })).getByText('Biofix')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Letters' })).toBeInTheDocument()
    // The climate terms link to how normals are made
    const normal = container.querySelector('#normal dd') as HTMLElement
    expect(within(normal).getByRole('link', { name: 'How we make normals' })).toHaveAttribute(
      'href',
      '/methods#normals',
    )
    expect(within(container.querySelector('#biofix dd') as HTMLElement).queryByRole('link')).toBeNull()
  })

  it('filters by words in a term or its definition, and shows all again', async () => {
    render(Glossary)
    const search = screen.getByRole('searchbox', { name: 'Search the glossary' })
    await fireEvent.input(search, { target: { value: 'fruit trees' } })
    expect(screen.getByText('Chill hours')).toBeInTheDocument()
    expect(screen.queryByText('Biofix')).toBeNull()
    expect(screen.getByText(/terms? match\./)).toBeInTheDocument()
    await fireEvent.input(search, { target: { value: 'zzzz' } })
    expect(screen.getByText('No terms match. Try fewer or other words.')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Show all terms' }))
    expect(screen.getByText(`${GLOSSARY.length} terms.`)).toBeInTheDocument()
  })
})
