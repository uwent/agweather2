import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import feedAnswer from '@/test/fixtures/site/feed-late-blight.json'
import modelProps from '@/test/fixtures/site/model-props-late-blight.json'
import type { SiteModelFeedProps, SiteModelProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))

// The API, answered from a late blight run at three sites recorded from the dev server (July 27 to August 20, 2025)
const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

// The saved sites
const store = vi.hoisted(() => {
  const at = '2025-01-01T00:00:00Z'
  const site = (lat: number, lng: number, name: string) => ({
    key: `${lat},${lng}`,
    lat,
    lng,
    name,
    addedAt: at,
    updatedAt: at,
  })
  return {
    sites: [site(43.07, -89.4, 'Madison'), site(44.1336, -89.5168, 'Hancock'), site(45.65, -89.38, 'Rhinelander')],
  }
})
vi.mock('@/lib/sites.svelte', async () => ({
  sites: store.sites,
  sitesState: { persistent: true, readOnly: false, unreadable: false },
  siteLabel: (s: { name: string }) => s.name,
  effectivePrefs: () => ({ crops: undefined, models: undefined, hiddenModels: [], options: {}, planting: undefined }),
}))

const { default: Feed } = await import('./Feed.svelte')
const { page } = await import('@/test/page.svelte')

const props: SiteModelFeedProps = { model: (modelProps as unknown as SiteModelProps).model }

// Rhinelander's risk raised to Very high on the day, so sorting by risk puts it first
function answer() {
  const body = structuredClone(feedAnswer) as typeof feedAnswer
  const data = body.data as unknown as Record<string, unknown[]>
  data.date.forEach((date, i) => {
    if (date === '2025-08-10' && data.point[i] === 2) {
      data.risk_level[i] = 4
      data.risk_label[i] = 'Very high'
    }
  })
  return body
}

beforeEach(() => {
  page.props.today = '2025-08-10'
  sessionStorage.clear()
  window.history.replaceState(null, '', '/sites/models/late-blight-dsv')
  get.mockReset()
  get.mockImplementation(() => Promise.resolve(answer()))
})

describe('one model across your sites', () => {
  it('runs the model over every site in one request', async () => {
    render(Feed, props)
    expect(screen.getByRole('heading', { level: 1, name: 'Late blight disease severity values at your sites' }))
    await screen.findByRole('list', { name: 'Your sites' })
    expect(get).toHaveBeenCalledTimes(1)
    expect(get).toHaveBeenCalledWith(
      '/models/late-blight-dsv/run',
      { start: '2025-07-27', points: '43.07,-89.4;44.1336,-89.5168;45.65,-89.38', units: 'metric' },
      expect.anything(),
    )
  })

  it("shows each site's risk in words with its strip, highest first, and links to the model there", async () => {
    render(Feed, props)
    const list = await screen.findByRole('list', { name: 'Your sites' })
    const rows = within(list).getAllByRole('listitem')
    expect(rows[0]).toHaveTextContent('Rhinelander')
    expect(rows[0]).toHaveTextContent('Very high risk today, Aug 10.')
    expect(within(rows[0]).getByRole('link', { name: 'Rhinelander' })).toHaveAttribute(
      'href',
      '/sites/45.65,-89.38/models/late-blight-dsv',
    )
    expect(
      within(rows[0]).getByRole('img', { name: /^Late blight disease severity values at Rhinelander: / }),
    ).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('radio', { name: 'Your order' }))
    expect(within(list).getAllByRole('listitem')[0]).toHaveTextContent('Madison')
  })
})
