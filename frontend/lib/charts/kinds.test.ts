import { describe, expect, it } from 'vitest'

import { testPalette as palette } from '@/test/palette'

import { band, bar, forecastBand, forecastFrom, formatHour, point, rowLabel, thresholdLine, todayLine } from './kinds'

const kinds = (...list: string[]) => list.map((kind) => ({ kind }) as { kind: 'observed' })

describe('kinds', () => {
  it("starts the forecast at today's partial day", () => {
    expect(forecastFrom(kinds('observed', 'partial', 'forecast'))).toBe(1)
    expect(forecastFrom(kinds('observed', 'forecast'))).toBe(1)
    expect(forecastFrom(kinds('observed', 'projection'))).toBe(1)
    expect(forecastFrom(kinds('observed'))).toBe(-1)
  })

  it('draws an estimated value hollow and a missing one as a gap', () => {
    expect(point(3, false, palette)).toBe(3)
    expect(point(null, true, palette)).toBeNull()
    expect(point(Number.NaN, false, palette)).toBeNull()
    expect(point(3, true, palette)).toMatchObject({ value: 3, symbol: 'emptyCircle' })
    expect(bar(2, true, 'blue', palette)).toMatchObject({ value: 2, itemStyle: { borderColor: 'blue' } })
    expect(bar(null, false, 'blue', palette)).toBeNull()
  })

  it("puts a dashed Today line on today's date or hour", () => {
    expect(todayLine(['2026-07-01', '2026-07-02'], '2026-07-02', palette)).toMatchObject([
      { xAxis: '2026-07-02', lineStyle: { type: 'dashed' }, label: { formatter: 'Today' } },
    ])
    expect(todayLine(['2026-07-02T00:00Z', '2026-07-02T01:00Z'], '2026-07-02', palette)[0].xAxis).toBe(
      '2026-07-02T00:00Z',
    )
    expect(todayLine(['2026-07-01'], '2026-07-02', palette)).toEqual([])
    expect(todayLine(['2026-07-02T00:00Z', '2026-07-02T01:00Z'], '2026-07-02T01:00Z', palette)).toMatchObject([
      { xAxis: '2026-07-02T01:00Z', label: { formatter: 'Now' } },
    ])
  })

  it('labels a threshold and shades and names the forecast', () => {
    expect(thresholdLine(0.0001, 'Freezing (32 °F)', palette)).toMatchObject({
      yAxis: 0,
      label: { formatter: 'Freezing (32 °F)' },
    })
    const dates = ['a', 'b', 'c']
    const { shading, label } = forecastBand({
      dates,
      days: kinds('observed', 'partial', 'forecast'),
      grids: 2,
      axisOffset: 2,
      palette,
    })
    expect(shading.series).toHaveLength(2)
    expect(label?.label.formatter).toBe('Forecast')
    expect(label?.data).toEqual([[{ xAxis: 'b' }, { xAxis: 'c' }]])
    expect(forecastBand({ dates, days: kinds('observed'), grids: 1, axisOffset: 1, palette }).label).toBeUndefined()
  })

  it("draws a projection's band as its height above an invisible lower edge", () => {
    const [lower, upper] = band({ id: 'dsv', lower: [1, 2, null], upper: [3, 5, 4], color: 'projection' }) as {
      data: (number | null)[]
    }[]
    expect(lower.data).toEqual([1, 2, null])
    expect(upper.data).toEqual([2, 3, null])
  })

  it("writes an hour on the location's clock with its zone", () => {
    expect(formatHour('2026-11-25T20:00Z', 'America/Chicago')).toBe('Nov 25, 2 p.m. CST')
    expect(formatHour('2026-07-01T17:00Z', 'America/Chicago')).toBe('Jul 1, noon CDT')
    expect(formatHour('2026-11-25T20:00Z', 'America/Chicago', { short: true })).toBe('2 p.m.')
    expect(formatHour('2026-11-25T06:00Z', 'America/Chicago', { short: true })).toBe('Nov 25')
    expect(rowLabel('2026-11-25')).toBe('Wed, Nov 25')
    expect(rowLabel('2026-11-25', undefined, { short: true })).toBe('Nov 25')
  })
})
