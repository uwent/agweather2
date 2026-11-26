import { describe, expect, it } from 'vitest'

import type { TableResponse } from '@/types/api'

import { units } from '../units'
import { dayStart, radarUrl, rainSoFarByPoint, rainSoFarShort, rainSoFarText, sumSoFar } from './rainSoFar'

const iso = (ms: number) => new Date(ms).toISOString().replace(':00.000Z', 'Z')
const hour = (time: string, value: number | null, forecast = false) => ({ time, value, forecast })

describe("today's day", () => {
  it('starts at midnight CST inside the area we cover, all year', () => {
    expect(iso(dayStart('2026-11-25', { in_box: true, timezone: 'America/Chicago' }))).toBe('2026-11-25T06:00Z')
    expect(iso(dayStart('2026-07-01', { in_box: true, timezone: 'America/Chicago' }))).toBe('2026-07-01T06:00Z')
  })

  it("starts at midnight on the location's own clock outside it, through daylight saving time", () => {
    expect(iso(dayStart('2026-11-25', { in_box: false, timezone: 'America/Los_Angeles' }))).toBe('2026-11-25T08:00Z')
    expect(iso(dayStart('2026-07-01', { in_box: false, timezone: 'America/Los_Angeles' }))).toBe('2026-07-01T07:00Z')
    expect(iso(dayStart('2026-03-08', { in_box: false, timezone: 'America/New_York' }))).toBe('2026-03-08T05:00Z')
  })
})

describe('precipitation so far today', () => {
  const start = Date.parse('2026-11-25T06:00Z')

  it('adds up the hours after midnight through the newest with a value, and counts the gaps before it', () => {
    const found = sumSoFar(
      [
        hour('2026-11-25T06:00Z', 5), // yesterday's last hour
        hour('2026-11-25T07:00Z', 0.5),
        hour('2026-11-25T08:00Z', null),
        hour('2026-11-25T09:00Z', 1.25),
        hour('2026-11-25T10:00Z', 0),
        hour('2026-11-25T11:00Z', null), // not in yet
        hour('2026-11-25T12:00Z', 3, true), // the forecast
      ],
      start,
      'America/Chicago',
    )
    expect(found).toEqual({ amount: 1.75, through: '2026-11-25T10:00Z', missing: 1, timeZone: 'America/Chicago' })
  })

  it('counts an hour the answer left out as missing', () => {
    const found = sumSoFar([hour('2026-11-25T07:00Z', 1), hour('2026-11-25T10:00Z', 1)], start, 'America/Chicago')
    expect(found?.missing).toBe(2)
  })

  it('has nothing to say before any hour of today has a value', () => {
    expect(sumSoFar([hour('2026-11-25T06:00Z', 2), hour('2026-11-25T07:00Z', null)], start, 'UTC')).toBeNull()
  })

  it("reads each point's own day from a several-point answer", () => {
    const body = {
      meta: {
        locations: [
          { in_box: true, timezone: 'America/Chicago' },
          { in_box: false, timezone: 'America/Los_Angeles' },
        ],
      },
      data: {
        point: [0, 0, 1, 1],
        time: ['2026-11-25T07:00Z', '2026-11-25T08:00Z', '2026-11-25T08:00Z', '2026-11-25T09:00Z'],
        kind: ['observed', 'observed', 'observed', 'observed'],
        precipitation: [1, 2, 4, 8],
      },
    } as unknown as TableResponse
    const [a, b] = rainSoFarByPoint(body, 2, '2026-11-25', Date.parse('2026-11-25T18:00Z'))
    expect(a?.amount).toBe(3)
    expect(b).toMatchObject({ amount: 8, through: '2026-11-25T09:00Z', missing: 0 })
  })

  it("takes a point's today on its own clock outside the area, when it differs from the grid's", () => {
    const body = {
      meta: {
        locations: [
          { in_box: true, timezone: 'America/Chicago' },
          { in_box: false, timezone: 'America/Los_Angeles' },
          { in_box: false, timezone: 'America/New_York' },
        ],
      },
      data: {
        point: [0, 1, 1, 2, 2],
        time: ['2026-11-26T06:00Z', '2026-11-25T20:00Z', '2026-11-26T06:00Z', '2026-11-25T10:00Z', '2026-11-26T05:00Z'],
        kind: ['observed', 'observed', 'observed', 'observed', 'observed'],
        precipitation: [1, 2, 4, 8, 16],
      },
    } as unknown as TableResponse
    // 12:30 a.m. CST on November 26 is still 10:30 p.m. on the 25th in Los Angeles
    const [a, b] = rainSoFarByPoint(body, 3, '2026-11-26', Date.parse('2026-11-26T06:30Z'))
    expect(a).toBeNull() // the grid's November 26 has no whole hour yet
    expect(b).toMatchObject({ amount: 6, through: '2026-11-26T06:00Z' })
    // 11:30 p.m. CST on November 25 is 12:30 a.m. on the 26th in New York, whose day has no whole hour yet
    const [, , c] = rainSoFarByPoint(body, 3, '2026-11-25', Date.parse('2026-11-26T05:30Z'))
    expect(c).toBeNull()
  })

  it('says how far the total goes and what is missing, in the reader’s units', () => {
    const r = { amount: 3.048, through: '2026-11-25T20:00Z', missing: 2, timeZone: 'America/Chicago' }
    expect(rainSoFarText(r, units('imperial'))).toBe(
      '0.12 in so far today, through Nov 25, 2 p.m. CST; 2 hours missing',
    )
    expect(rainSoFarShort(r, units('imperial'))).toBe('0.12 in so far')
    expect(radarUrl('/map', 43.07312, -89.40123)).toBe('/map?overlay=radar&c=43.073%2C-89.401&z=8')
  })
})
