import { describe, expect, it } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import type { LayerInfo } from '@/types/api'

import {
  addHours,
  bandOf,
  boundaryOf,
  centerOf,
  cstDayStart,
  dayTimeline,
  edgeOf,
  hourTimeline,
  indexAt,
  indexOf,
  inYear,
  isRecent,
  labelPlacement,
  recentTimeline,
  moveBy,
  segmentsOf,
  whenAt,
  yearsOf,
} from './timeline'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
// The fixture's daily layers: 2016-01-01 to 2026-11-24 observed, forecast through 2026-12-06
const daily = layer('air_temperature_min')
// Hourly: observed through 2026-11-25T20Z (2 p.m. CST), forecast through 2026-12-06T19Z
const hourly = layer('air_temperature_hourly')

describe('a daily layer’s timeline', () => {
  it('runs over the chosen day’s year, selectable within the archive and forecast', () => {
    const t = dayTimeline(daily, '2026-07-01')!
    expect(t.start).toBe('2026-01-01')
    expect(t.count).toBe(365)
    expect(t.min).toBe(0)
    expect(whenAt(t, t.max)).toBe('2026-12-06')
    expect(whenAt(t, t.observed)).toBe('2026-11-24')
    expect(indexOf(t, '2026-07-01')).toBe(181)
  })

  it('has no forecast in a past year, and no days before the archive’s first', () => {
    const past = dayTimeline(daily, '2020-03-01')!
    expect(past.count).toBe(366)
    expect(past.max).toBe(365)
    expect(boundaryOf(past)).toBeNull()
    expect(segmentsOf(past).forecast).toBeNull()
    const first = dayTimeline({ ...daily, range: { ...daily.range, first: '2016-03-15' } }, '2016-06-01')!
    expect(whenAt(first, first.min)).toBe('2016-03-15')
  })

  it('places the forecast’s boundary after the last observed day', () => {
    const t = dayTimeline(daily, '2026-11-01')!
    const boundary = boundaryOf(t)!
    expect(boundary).toBeCloseTo(edgeOf(t, indexOf(t, '2026-11-25')))
    const { observed, forecast } = segmentsOf(t)
    expect(observed).toEqual([0, boundary])
    expect(forecast![0]).toBe(boundary)
    expect(forecast![1]).toBeCloseTo(edgeOf(t, indexOf(t, '2026-12-07')))
  })

  it('labels months, the odd ones minor', () => {
    const t = dayTimeline(daily, '2026-11-01')!
    expect(t.ticks.map((tick) => tick.label)).toEqual([
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ])
    expect(t.ticks[1].minor).toBe(true)
    expect(t.ticks[2].at).toBeCloseTo(59 / 365)
  })

  it('is null for a layer without days', () => {
    expect(dayTimeline({ range: { first: null, last: null, forecast_through: null } }, '2026-07-01')).toBeNull()
  })
})

describe('positions and clamping', () => {
  const t = dayTimeline(daily, '2026-11-01')!

  it('maps a pointer’s fraction to a day, held to what can be chosen', () => {
    expect(whenAt(t, indexAt(t, 0))).toBe('2026-01-01')
    expect(whenAt(t, indexAt(t, 0.5))).toBe('2026-07-02')
    // Past the forecast's last day: its last day
    expect(whenAt(t, indexAt(t, 0.99))).toBe('2026-12-06')
    expect(whenAt(t, indexAt(t, -1))).toBe('2026-01-01')
    expect(centerOf(t, 0)).toBeCloseTo(0.5 / 365)
  })

  it('moves by steps within the bounds', () => {
    const nov20 = indexOf(t, '2026-11-20')
    expect(whenAt(t, moveBy(t, nov20, 7))).toBe('2026-11-27')
    expect(whenAt(t, moveBy(t, nov20, 30))).toBe('2026-12-06')
    expect(whenAt(t, moveBy(t, 3, -7))).toBe('2026-01-01')
  })

  it('shows a range as a band, clipped to the window', () => {
    expect(bandOf(t, '2026-07-01', '2026-07-14')).toEqual([edgeOf(t, 181), edgeOf(t, 195)])
    // A season from a biofix the year before starts at the window's edge
    expect(bandOf(t, '2025-10-01', '2026-03-01')![0]).toBe(0)
    expect(bandOf(t, '2025-01-01', '2025-03-01')).toBeNull()
  })

  it('places the boundary’s labels where they fit', () => {
    expect(labelPlacement(0.5)).toBe('split')
    expect(labelPlacement(0.9)).toBe('before')
    expect(labelPlacement(0.1)).toBe('after')
  })
})

describe('a daily layer’s recent timeline', () => {
  it('runs over the last 6 weeks observed and the forecast, the boundary well clear of the end', () => {
    const t = recentTimeline(daily)!
    expect(t.start).toBe('2026-10-14')
    expect(whenAt(t, t.observed)).toBe('2026-11-24')
    expect(whenAt(t, t.max)).toBe('2026-12-06')
    expect(t.count).toBe(54)
    expect(boundaryOf(t)).toBeCloseTo(42 / 54)
    expect(t.ticks.map((tick) => tick.label)).toEqual([
      'Oct 14',
      'Oct 21',
      'Oct 28',
      'Nov 4',
      'Nov 11',
      'Nov 18',
      'Nov 25',
      'Dec 2',
    ])
  })

  it('knows which days it holds', () => {
    expect(isRecent('2026-11-20', daily)).toBe(true)
    expect(isRecent('2026-12-06', daily)).toBe(true)
    expect(isRecent('2026-10-13', daily)).toBe(false)
  })
})

describe('an hourly layer’s timeline', () => {
  it('runs over the 7 CST days around the newest hour', () => {
    const t = hourTimeline(hourly, null)!
    // The newest hour, 20Z Nov 25, is 2 p.m. CST: the window starts at CST midnight Nov 22 (06Z)
    expect(t.start).toBe('2026-11-22T06')
    expect(t.count).toBe(168)
    expect(whenAt(t, t.observed)).toBe('2026-11-25T20')
    expect(whenAt(t, t.max)).toBe('2026-11-29T05')
    expect(t.ticks[0]).toEqual({ at: 0, label: 'Nov 22', minor: false })
    expect(t.ticks).toHaveLength(7)
  })

  it('moves to the chosen hour’s days when it’s outside them', () => {
    const t = hourTimeline(hourly, '2026-07-08T18')!
    expect(t.start).toBe('2026-07-05T06')
    expect(indexOf(t, '2026-07-08T18')).toBe(3 * 24 + 12)
    expect(boundaryOf(t)).toBeNull()
    expect(hourTimeline(hourly, '2026-11-24T03')!.start).toBe('2026-11-22T06')
  })

  it('counts hours and CST days', () => {
    expect(addHours('2026-11-25T20', 10)).toBe('2026-11-26T06')
    expect(cstDayStart('2026-11-26T05')).toBe('2026-11-25T06')
    expect(cstDayStart('2026-11-26T06')).toBe('2026-11-26T06')
  })
})

describe('a year chosen', () => {
  it('lists the years from the newest, and keeps the day of the year', () => {
    expect(yearsOf(daily)).toEqual([2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016])
    expect(inYear('2026-07-08', 2020, daily)).toBe('2020-07-08')
    expect(inYear('2024-02-29', 2023, daily)).toBe('2023-02-28')
    // Held to the forecast's last day
    expect(inYear('2025-12-20', 2026, daily)).toBe('2026-12-06')
  })
})
