import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChangelogEntryProps, ChangelogProps } from '@/types'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

const { default: Changelog } = await import('./Changelog.svelte')

const entry = (id: number, kind: string, kind_label: string, title: string): ChangelogEntryProps => ({
  id,
  date: `2026-11-${String(10 + id).padStart(2, '0')}`,
  kind,
  kind_label,
  title,
  body_html: `<p>About ${title}.</p>`,
  model: kind === 'model' ? 'late-blight-dsv' : null,
  endpoint: null,
})

const props: ChangelogProps = {
  entries: [
    entry(3, 'outage', 'Outage or delay', 'Precipitation delayed'),
    entry(2, 'model', 'Models', 'Late blight updated'),
    entry(1, 'outage', 'Outage or delay', 'Forecast late'),
  ],
  kinds: [
    { value: 'api', label: 'API change' },
    { value: 'model', label: 'Models' },
    { value: 'outage', label: 'Outage or delay' },
  ],
}

describe('the changelog', () => {
  beforeEach(() => {
    sessionStorage.clear()
    window.history.replaceState(null, '', '/changelog')
  })

  it('filters by kind, offering only the kinds it has', async () => {
    render(Changelog, { props })
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(3)
    expect(screen.queryByLabelText(/API change/)).not.toBeInTheDocument()
    await fireEvent.click(screen.getByLabelText('Outage or delay (2)'))
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual([
      'Precipitation delayed',
      'Forecast late',
    ])
  })

  it('opens on the kind a link names', () => {
    window.history.replaceState(null, '', '/changelog?kind=model')
    render(Changelog, { props })
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual(['Late blight updated'])
    expect(screen.getByRole('link', { name: 'late-blight-dsv' })).toHaveAttribute('href', '/models/late-blight-dsv')
  })

  it('gives each entry an anchor and copies its link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    render(Changelog, { props })
    expect(document.getElementById('entry-2')).toHaveTextContent('Late blight updated')
    await fireEvent.click(screen.getByRole('button', { name: 'Copy the link to “Late blight updated”' }))
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/changelog#entry-2`)
    await vi.waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Copied the link to this entry.'))
  })
})
