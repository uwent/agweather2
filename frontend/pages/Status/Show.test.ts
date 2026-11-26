import { render, screen } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { report, SOURCES } from '@/test/fixtures/status'
import type { StatusPageProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

const { default: Show } = await import('./Show.svelte')

const props = (overrides: Partial<StatusPageProps> = {}): StatusPageProps => ({
  report: report(),
  sources: SOURCES,
  outages: [],
  refresh_seconds: 60,
  ...overrides,
})

describe('the data status page', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    vi.setSystemTime(new Date('2026-11-26T04:30:00Z'))
    get.mockReset()
  })
  afterEach(() => vi.useRealTimers())

  it('says what is current, source by source', () => {
    render(Show, { props: props() })
    expect(screen.getAllByRole('status')[0]).toHaveTextContent('All data are up to date')
    expect(screen.getByText('Checked at 10:30 p.m. CST. This page checks again every minute while it is open.'))
    const table = screen.getByRole('table')
    expect(table).toHaveTextContent('URMA (Unrestricted Mesoscale Analysis), NOAA')
    expect(table).toHaveTextContent('3 p.m. CST, Nov 25')
    expect(screen.getByText('No hours are missing from the archive since Oct 27.')).toBeInTheDocument()
    expect(screen.getByText('We haven’t reported any outages in the last 90 days.')).toBeInTheDocument()
  })

  it('asks the API again every minute and shows the new answer', async () => {
    const later = report({
      forecast: { cycle: '2026-11-25T01:00Z', last_hour: null, in_use: false, reason: 'stale', fallback: 'openmeteo' },
    })
    get.mockResolvedValue({ meta: {}, data: later })
    render(Show, { props: props() })
    expect(get).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(60_000)
    expect(get).toHaveBeenCalledWith('/status', undefined, expect.objectContaining({ signal: expect.anything() }))
    await vi.waitFor(() =>
      expect(screen.getAllByRole('status')[0]).toHaveTextContent('forecasts for locations inside our area come from'),
    )
  })

  it('keeps the last answer and says so when a check fails', async () => {
    get.mockRejectedValue(new TypeError('Failed to fetch'))
    render(Show, { props: props() })
    await vi.advanceTimersByTimeAsync(60_000)
    await vi.waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('We couldn’t check the status just now.'),
    )
    expect(screen.getAllByRole('status')[0]).toHaveTextContent('All data are up to date')
  })

  it('lists days with missing hours and recent outages', () => {
    const r = report()
    r.gaps.variables[0].days = [{ date: '2026-11-03', missing_hours: 5 }]
    render(Show, {
      props: props({
        report: r,
        outages: [
          {
            id: 7,
            date: '2026-11-20',
            kind: 'outage',
            kind_label: 'Outage or delay',
            title: 'Precipitation delayed',
            body_html: '<p>NOAA’s files were late.</p>',
            model: null,
            endpoint: null,
          },
        ],
      }),
    })
    expect(screen.getByText('Nov 3 (5 hours)')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Precipitation delayed' })).toHaveAttribute('href', '/changelog#entry-7')
  })
})
