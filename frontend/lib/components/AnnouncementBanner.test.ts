import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DISMISSED_KEY, dismiss, dismissedIds, shown } from '@/lib/announcements'
import { page } from '@/test/page.svelte'
import type { AnnouncementProps } from '@/types'
vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

import AnnouncementBanner from './AnnouncementBanner.svelte'

const entry = (id: number, overrides: Partial<AnnouncementProps> = {}): AnnouncementProps => ({
  id,
  kind: 'announcement',
  title: `Notice ${id}`,
  body_html: `<p>About notice ${id}.</p>`,
  until: '2999-01-01T00:00:00Z',
  ...overrides,
})

describe('announcements', () => {
  beforeEach(() => {
    localStorage.clear()
    page.props.announcements = []
  })

  it('keeps dismissed ids for the entries still shown', () => {
    expect(dismissedIds()).toEqual([])
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([1, 'x', 2]))
    expect(dismissedIds()).toEqual([1, 2])
    expect(dismiss(3, [2, 3])).toEqual([2, 3]) // 1 is no longer shown, so it's forgotten
    expect(JSON.parse(localStorage.getItem(DISMISSED_KEY)!)).toEqual([2, 3])
  })

  it('shows an entry until it is dismissed or its time has passed', () => {
    const now = new Date('2026-11-26T12:00:00Z')
    const past = entry(2, { until: '2026-11-26T11:00:00Z' })
    expect(shown([entry(1), past, entry(3)], [3], now).map((a) => a.id)).toEqual([1])
  })

  it('draws each banner with a link to its entry and closes it for good', async () => {
    page.props.announcements = [entry(1), entry(2, { kind: 'outage', title: 'Delayed data' })]
    const { unmount } = render(AnnouncementBanner)
    expect(screen.getByRole('link', { name: 'Notice 1' })).toHaveAttribute('href', '/changelog#entry-1')
    expect(screen.getByRole('region', { name: 'Outage notice' })).toHaveTextContent('Delayed data')
    await fireEvent.click(screen.getByRole('button', { name: 'Dismiss “Notice 1”' }))
    expect(screen.queryByText('Notice 1')).not.toBeInTheDocument()
    unmount()
    render(AnnouncementBanner) // the next page
    expect(screen.queryByText('Notice 1')).not.toBeInTheDocument()
    expect(screen.getByText('Delayed data')).toBeInTheDocument()
  })
})
