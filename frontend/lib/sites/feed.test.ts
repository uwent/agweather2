// The feed's parts, over a late blight run at three sites recorded from the dev server (July 27 to August 20, 2025)
import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'
import feedAnswer from '@/test/fixtures/site/feed-late-blight.json'
import modelProps from '@/test/fixtures/site/model-props-late-blight.json'
import type { SiteModelProps } from '@/types'
import type { TableResponse } from '@/types/api'

import type { EffectivePrefs, Site } from '../sitesDoc'
import { feedRequests, feedRows, feedWarnings, pointsParam, sortRows, splitPoints } from './feed'

const model = (modelProps as unknown as SiteModelProps).model
const body = feedAnswer as unknown as TableResponse
const at = '2025-01-01T00:00:00Z'
const site = (lat: number, lng: number, name: string): Site => ({
  key: `${lat},${lng}`,
  lat,
  lng,
  name,
  addedAt: at,
  updatedAt: at,
})
const SITES = [site(43.07, -89.4, 'Madison'), site(44.1336, -89.5168, 'Hancock'), site(45.65, -89.38, 'Rhinelander')]
const none: EffectivePrefs = {
  crops: undefined,
  models: undefined,
  hiddenModels: [],
  options: {},
  planting: undefined,
  biofix: undefined,
}

describe('the requests', () => {
  it('runs every site in one request from two weeks back, unless their settings differ', () => {
    const one = feedRequests({ sites: SITES, model, prefsOf: () => none, today: '2026-07-20' })
    expect(one).toHaveLength(1)
    expect(one[0].params).toEqual({ start: '2026-07-06' })
    expect(pointsParam(one[0].sites)).toBe('43.07,-89.4;44.1336,-89.5168;45.65,-89.38')
    const own = (key: string): EffectivePrefs =>
      key === SITES[1].key ? { ...none, options: { 'late-blight-dsv': { biofix: '2026-06-01' } } } : none
    const two = feedRequests({ sites: SITES, model, prefsOf: own, today: '2026-07-20' })
    expect(two.map((r) => r.sites.map((s) => s.name))).toEqual([['Madison', 'Rhinelander'], ['Hancock']])
    expect(two[1].params).toEqual({ biofix: '2026-06-01', start: '2026-07-06' })
  })
})

describe('the rows', () => {
  const requests = [{ params: {}, sites: SITES }]
  const today = '2025-08-10'

  it('splits a several-point answer into one per point, with what was resolved there', () => {
    const parts = splitPoints(body, 3)
    expect(parts.map((p) => (p.data as { date: string[] }).date.length)).toEqual([25, 25, 25])
    expect((parts[1].meta.request as { biofix: string }).biofix).toBe('2025-05-15')
    expect((parts[2].meta.location as { lat: number }).lat).toBe(45.65)
  })

  it("gives each site today's answer, the next milestone and its risk by day", () => {
    const rows = feedRows({ requests, bodies: [body], order: SITES, model, units: unitsFor('imperial'), today })
    expect(rows.map((r) => r.site.name)).toEqual(['Madison', 'Hancock', 'Rhinelander'])
    expect(rows[0].answer.headline).toBe('Moderate risk today, Aug 10.')
    expect(rows[0].level).toBe(2)
    expect(rows[0].days).toHaveLength(25)
    expect(rows[0].days.find((d) => d.date === today)).toMatchObject({ label: 'Moderate', inSeason: true })
    expect(rows.every((r) => r.next === null || /^(Next|Last reached): /.test(r.next))).toBe(true)
  })

  it('sorts by risk, highest first, ties in your order', () => {
    const rows = feedRows({ requests, bodies: [body], order: SITES, model, units: unitsFor('imperial'), today })
    rows[2].level = 4
    rows[0].level = null
    expect(sortRows(rows, 'risk', 5).map((r) => r.site.name)).toEqual(['Rhinelander', 'Hancock', 'Madison'])
    expect(sortRows(rows, 'order', 5).map((r) => r.site.name)).toEqual(['Madison', 'Hancock', 'Rhinelander'])
  })

  it("names the sites in the API's warnings about some of the points", () => {
    const noted = { meta: { ...body.meta, warnings: ['For points 0 and 2: the weather has gaps.', 'All of them.'] } }
    expect(feedWarnings(requests, [noted as TableResponse])).toEqual([
      'At Madison and Rhinelander: the weather has gaps.',
      'All of them.',
    ])
  })
})
