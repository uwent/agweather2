import { describe, expect, it } from 'vitest'

import type { DataStatus } from '@/types'

import { cstTime, dataThrough, staleMessages } from './dataStatus'

const status = (patch: Partial<DataStatus> = {}): DataStatus => ({
  observed_through: '2026-11-25T20:00:00Z',
  daily_through: '2026-11-24',
  forecast_cycle: '2026-11-25T18:00:00Z',
  forecast_through: '2026-12-07T06:00:00Z',
  forecast_fallback: null,
  behind: [],
  stale_sources: [],
  ...patch,
})

describe('data status in words', () => {
  it('gives times on the grid’s clock, CST all year', () => {
    expect(cstTime('2026-11-25T20:00:00Z')).toBe('2 p.m. CST, Nov 25')
    expect(cstTime('2026-07-01T06:00:00Z')).toBe('midnight CST, Jul 1')
    expect(cstTime('2026-07-01T18:00:00Z')).toBe('noon CST, Jul 1')
  })

  it('says how far the data go', () => {
    expect(dataThrough(status())).toBe('Observed through 2 p.m. CST, Nov 25 · forecast to Dec 6')
    expect(dataThrough(status({ behind: ['forecast'] }))).toBe('Observed through 2 p.m. CST, Nov 25')
    expect(dataThrough(null)).toBeNull()
  })

  it('says nothing while the data are current, and what’s late otherwise', () => {
    expect(staleMessages(status())).toEqual([])
    expect(staleMessages(null)).toEqual([])
    expect(staleMessages(status({ behind: ['observed', 'forecast'], forecast_fallback: 'openmeteo' }))).toEqual([
      'Weather observations are running late: the newest we have is from 2 p.m. CST, Nov 25. Maps, charts and models will update when new data arrive.',
      'Our forecast hasn’t updated since noon CST, Nov 25, so forecasts inside our area come from Open-Meteo until it does.',
    ])
    expect(staleMessages(status({ behind: ['forecast'], forecast_cycle: null }))).toEqual([
      'Our forecast hasn’t updated, so forecast days may be missing or out of date until it does.',
    ])
  })
})
