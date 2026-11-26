import { describe, expect, it } from 'vitest'

import { report, SOURCES } from '@/test/fixtures/status'

import { agoText, gapRows, gapsSummary, headline, shortName, sourceRows, spanText } from './statusWords'

const NOW = new Date('2026-11-26T04:30:00Z')

describe('sourceRows', () => {
  it('reads each source against its usual delay', () => {
    const rows = sourceRows(report(), SOURCES, NOW)
    expect(rows.map((r) => r.stateLabel)).toEqual(['On time', 'On time', 'On time', 'On time'])
    expect(rows[0].newest).toBe('3 p.m. CST, Nov 25')
    expect(rows[0].normally).toBe('within 14 hours')
    expect(rows[3].normally).toBe('within 7 days')
    const late = sourceRows(report(), SOURCES, new Date('2026-11-26T12:00:00Z'))
    expect(late.map((r) => r.state)).toEqual(['late', 'late', 'late', 'on-time'])
  })

  it('says when a source has sent nothing', () => {
    const empty = report()
    empty.archive.last_hour_by_source = {}
    expect(sourceRows(empty, SOURCES, NOW).every((r) => r.stateLabel === 'No data')).toBe(true)
    expect(headline(empty, sourceRows(empty, SOURCES, NOW))).toEqual({
      level: 'down',
      text: 'We have no weather data yet.',
    })
  })
})

describe('headline', () => {
  it('says everything is current, with the newest hour and the forecast', () => {
    expect(headline(report(), sourceRows(report(), SOURCES, NOW))).toEqual({
      level: 'ok',
      text: 'All data are up to date, with weather observed through 10 p.m. CST, Nov 25 and the forecast issued 7 p.m. CST, Nov 25.',
    })
  })

  it('leaves out a late source whose stand-in is current', () => {
    const r = report()
    r.archive.last_hour_by_source = {
      ...r.archive.last_hour_by_source,
      rtma: '2026-11-26T13:00Z',
      hrrr: '2026-11-26T13:00Z',
    }
    const at = new Date('2026-11-26T14:00:00Z') // URMA 17 hours behind, RTMA filling in
    const rows = sourceRows(r, SOURCES, at)
    expect(rows[0].state).toBe('late')
    expect(headline(r, rows).level).toBe('ok')
    const later = new Date('2026-11-26T18:00:00Z') // and RTMA 5 hours behind
    expect(headline(r, sourceRows(r, SOURCES, later)).text).toBe(
      'URMA, RTMA and HRRR are running later than usual, so the newest hours of temperature, humidity, wind and precipitation and solar radiation may be missing for now.',
    )
  })

  it('names the forecast falling back to Open-Meteo', () => {
    const stale = report({
      forecast: { cycle: '2026-11-25T01:00Z', last_hour: null, in_use: false, reason: 'stale', fallback: 'openmeteo' },
    })
    const found = headline(stale, sourceRows(stale, SOURCES, NOW))
    expect(found.level).toBe('late')
    expect(found.text).toContain('forecasts for locations inside our area come from Open-Meteo')
  })
})

describe('gaps', () => {
  it('lists the days missing hours by kind of data', () => {
    const r = report()
    r.gaps.variables[1].days = [
      { date: '2026-11-03', missing_hours: 5 },
      { date: '2026-11-04', missing_hours: 1 },
    ]
    const rows = gapRows(r, SOURCES)
    expect(rows[1]).toEqual({
      variable: 'precipitation',
      kind: 'Precipitation',
      sources: 'RTMA and URMA',
      days: [
        { date: '2026-11-03', text: 'Nov 3 (5 hours)' },
        { date: '2026-11-04', text: 'Nov 4 (1 hour)' },
      ],
    })
    expect(gapsSummary(rows, r.gaps.first)).toBe(
      'Some hours are missing from the archive since Oct 27: precipitation on 2 days.',
    )
    expect(gapsSummary(gapRows(report(), SOURCES), '2026-10-27')).toBe(
      'No hours are missing from the archive since Oct 27.',
    )
    expect(gapsSummary([], null)).toBe('We haven’t checked the archive for gaps yet.')
  })
})

describe('words', () => {
  it('spans, ages and short names', () => {
    expect([spanText(1), spanText(4), spanText(168)]).toEqual(['1 hour', '4 hours', '7 days'])
    expect(agoText('2026-11-26T04:00Z', NOW)).toBe('30 minutes')
    expect(agoText('2026-11-23T04:00Z', NOW)).toBe('3 days')
    expect(shortName('ERA5-Land, ECMWF (Copernicus)')).toBe('ERA5-Land')
  })
})
