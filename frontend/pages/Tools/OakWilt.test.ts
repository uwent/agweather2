// The oak wilt tool (/tools/oak-wilt): its run at a place, and the extended forecast's run while degree days fall
// short of 231, over answers recorded from the dev server (the map a stand-in: jsdom has no WebGL)
import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import locate from '@/test/fixtures/site/locate.json'
import run from '@/test/fixtures/site/model-oak-wilt.json'
import props from '@/test/fixtures/tools/oak-wilt-props.json'
import type { OakWiltToolProps } from '@/types'

vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))
vi.mock('@/lib/map/DataMap.svelte', () => import('@/test/FakeDataMap.svelte'))

const get = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (actual) => ({ ...(await actual<typeof import('@/lib/api')>()), get }))

/** The recorded run (Madison, 2026, reaching 231 °F·d on April 16) cut off at `last`, as a run seen early in April */
function runThrough(last: string) {
  const columns = run.data as Record<string, unknown[]>
  const n = (columns.date as string[]).filter((date) => date <= last).length
  return { ...run, data: Object.fromEntries(Object.entries(columns).map(([key, values]) => [key, values.slice(0, n)])) }
}

type Params = Record<string, unknown>
function answer(path: string, params: Params = {}): unknown {
  if (path === '/locate') return locate
  if (path === '/models/oak-wilt-vectors/run') return params.projection ? run : runThrough('2026-04-11')
  throw new Error(`no answer for ${path}`)
}

const { default: OakWilt } = await import('./OakWilt.svelte')
const { page } = await import('@/test/page.svelte')
const store = await import('@/lib/sites.svelte')

beforeEach(() => {
  page.props.today = '2026-04-05'
  sessionStorage.clear()
  store.useSitesBackend(store.memoryBackend())
  get.mockReset()
  get.mockImplementation((path: string, params: Params) => Promise.resolve(answer(path, params)))
})

const runsAsked = (projection: boolean) =>
  get.mock.calls
    .filter(([path, params]) => path === '/models/oak-wilt-vectors/run' && !!params.projection === projection)
    .map(([, params]) => `${params.lat},${params.lng}`)

describe('the oak wilt tool', () => {
  it('asks for the extended forecast again for each place still short of 231 degree days', async () => {
    window.history.replaceState(null, '', '/tools/oak-wilt?at=43.07,-89.4')
    render(OakWilt, props as unknown as OakWiltToolProps)
    expect(await screen.findByText(/are expected to reach 231 °F·d on April 16/)).toBeVisible()
    expect(runsAsked(true)).toEqual(['43.07,-89.4'])

    await fireEvent.click(screen.getByRole('button', { name: 'Click the map' }))
    await vi.waitFor(() => expect(runsAsked(false)).toEqual(['43.07,-89.4', '44.12,-89.52']))
    await vi.waitFor(() => expect(runsAsked(true)).toEqual(['43.07,-89.4', '44.12,-89.52']))
  })
})
