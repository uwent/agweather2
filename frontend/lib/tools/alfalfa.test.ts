import { describe, expect, it } from 'vitest'

import type { Palette } from '@/lib/charts/palette'
import { units as unitsFor } from '@/lib/units'
import planCutsBody from '@/test/fixtures/alfalfa/plan-cuts.json'
import planBody from '@/test/fixtures/alfalfa/plan.json'
import runCutBody from '@/test/fixtures/alfalfa/run-cut.json'
import runProjectionBody from '@/test/fixtures/alfalfa/run-projection.json'
import type { TableResponse } from '@/types/api'

import {
  cutLine,
  editCuts,
  fallWords,
  gddText,
  parsePlan,
  planOption,
  planQuery,
  planSpan,
  planTable,
  seasonWords,
  sinceCut,
  sinceCutOption,
  sinceCutTable,
  sinceCutWords,
  windowText,
} from './alfalfa'

// Recorded from the dev server at Madison's cell on November 26, 2026 (`units=us`): the default plan (five cuts
// from June 7 to November 1), a plan of four dates checked as given with July 10 held, a run since a cut on August 15
// (window reached September 12, passed September 21) and one since October 15 (471 GDD, the projection flat).
const us = unitsFor('imperial')
const metric = unitsFor('metric')
const TODAY = '2026-11-26'
const body = (b: unknown) => b as TableResponse
const palette = {
  ink: '#111',
  inkMuted: '#666',
  line: '#ccc',
  surface: '#fff',
  temperature: { max: '#c00', min: '#00c', mean: '#606' },
  precipitation: '#06c',
  et: '#0a0',
  degreeDays: '#a60',
  normal: '#888',
  forecast: '#eee',
  projection: '#a60',
  estimated: '#999',
  missing: '#ddd',
  severity: ['#1', '#2', '#3', '#4', '#5'],
  dark: false,
} as Palette

/** The projection run with its milestones replaced, as a season still ahead would give them */
function withMilestones(milestones: object[]) {
  const b = structuredClone(runProjectionBody) as unknown as TableResponse
  const summary = b.meta.summary as Record<string, unknown>
  summary.projection = { ...(summary.projection as object), milestones }
  return b
}

describe('since the last cut', () => {
  it('reads the total through today and when the window was reached and passed', () => {
    const s = sinceCut(body(runCutBody), TODAY)
    expect(s.from).toBe('2026-08-15')
    expect(s.spring).toBe(false)
    expect(s.window).toEqual({ from: 900, until: 1100 })
    expect(s.entered).toEqual({ date: '2026-09-12', forecast: false })
    expect(s.passed).toEqual({ date: '2026-09-21', forecast: false })
    expect(s.asOf).toBe(TODAY)
    expect(s.total).toBeGreaterThan(1100)
    expect(s.enterExpected).toBeNull()
  })

  it('says the window was passed in words', () => {
    const words = sinceCutWords(sinceCut(body(runCutBody), TODAY), us)
    expect(words.headline).toMatch(
      /^Alfalfa here has had \d,\d{3} GDD since the cut on August 15 \(through November 26\)\.$/,
    )
    expect(words.details[0]).toBe(
      'It reached the cutting window (900 GDD) on September 12 and passed 1,100 GDD, the end of the window, on September 21. Past the window, forage quality declines as the crop matures.',
    )
  })

  it('gives the expected date from past years when the window is still ahead', () => {
    const b = withMilestones([
      { what: 'stage', name: 'Cut', reached: 10, of: 10, p10: '2026-12-20', p50: '2026-12-24', p90: '2026-12-29' },
      { what: 'stage', name: 'Late', reached: 2, of: 10, p10: null, p50: null, p90: null },
    ])
    const s = sinceCut(b, TODAY)
    expect(s.entered).toBeNull()
    expect(s.enterExpected).toMatchObject({ p50: '2026-12-24', reached: 10, of: 10 })
    const words = sinceCutWords(s, us)
    expect(words.headline).toContain('since the cut on October 15')
    expect(words.details).toEqual([
      'From past years’ weather after the forecast, it is expected to reach the cutting window (900 GDD) about December 24 (likely between December 20 and December 29).',
    ])
  })

  it('says so when past years mostly don’t reach the window', () => {
    const none = sinceCutWords(sinceCut(body(runProjectionBody), TODAY), us)
    expect(none.details[0]).toBe(
      'In none of 10 past years’ weather after the forecast does it reach the cutting window (900 GDD) before the end of the year.',
    )
    const few = withMilestones([{ name: 'Cut', reached: 3, of: 10, p10: '2026-12-20', p50: '2026-12-28', p90: null }])
    expect(sinceCutWords(sinceCut(few, TODAY), us).details[0]).toContain('in only 3 of 10')
  })

  it('counts from January 1 without a cut', () => {
    const b = structuredClone(runCutBody) as unknown as TableResponse
    ;(b.meta.request as Record<string, unknown>).biofix = '2026-01-01'
    const s = sinceCut(b, TODAY)
    expect(s.spring).toBe(true)
    expect(sinceCutWords(s, us).headline).toContain('since January 1')
  })

  it('draws the window as a band and the projection dashed over its range', () => {
    const s = sinceCut(body(runProjectionBody), TODAY)
    const option = sinceCutOption({ since: s, units: us, palette, today: TODAY }) as {
      series: { id: string; markArea?: { data: unknown[] } }[]
    }
    const ids = option.series.map((x) => x.id)
    expect(ids).toContain('gdd-projection')
    expect(ids).toContain('band-gdd-upper')
    expect(option.series[0].markArea?.data).toEqual([[{ yAxis: 900, name: 'Cutting window' }, { yAxis: 1100 }]])
    // In metric the window is in °C·d
    const m = sinceCutOption({ since: s, units: metric, palette, today: TODAY }) as typeof option
    expect(m.series[0].markArea?.data).toEqual([[{ yAxis: 500, name: 'Cutting window' }, { yAxis: 1100 / 1.8 }]])
  })

  it('tables the days newest first with the projection’s range', () => {
    const t = sinceCutTable(sinceCut(body(runProjectionBody), TODAY), us)
    expect(t.columns).toEqual(['GDD since the cut (°F·d)', '10th percentile', '90th percentile'])
    expect(t.rows[0].date).toBe('2026-12-31')
  })
})

describe('the plan', () => {
  const plan = parsePlan(body(planBody))

  it('reads the summary and the days', () => {
    expect(plan.year).toBe(2026)
    expect(plan.springFreeze).toEqual({ date: '2026-04-07', basis: 'observed' })
    expect(plan.seasonEnd).toEqual({ date: '2026-11-01', basis: 'typical' })
    expect(plan.interval).toBe(1000)
    expect(plan.cuts.map((c) => c.date)).toEqual(['2026-06-07', '2026-07-11', '2026-08-10', '2026-09-11', '2026-11-01'])
    expect(plan.cuts[0]).toEqual({
      date: '2026-06-07',
      held: false,
      gdd: 987,
      days: 61,
      status: 'window',
      projected: false,
    })
    expect(plan.fall).toMatchObject({ lastCut: '2026-11-01', years: 30, under: 25, beforeCut: 5 })
    expect(plan.thresholds).toEqual({ cutFrom: 900, cutUntil: 1100, fallUnder: 360, fallOver: 900, killingFreeze: 24 })
    expect(plan.years).toEqual({ first: 1996, last: 2025, years: 30 })
    expect(plan.days).toHaveLength(365)
    expect(plan.days.find((d) => d.date === '2026-06-07')).toMatchObject({ cut: true, sinceCut: 987 })
    expect(plan.days.find((d) => d.date === '2026-06-08')?.sinceCut).toBe(28)
  })

  it('says where the season starts and ends', () => {
    expect(seasonWords(plan, us)).toBe(
      'The season counts from this year’s last spring killing freeze (24 °F or colder), on April 7. Cuts are scheduled through November 1, the date by which 1 year in 10 has had its first fall killing freeze.',
    )
    const typical = { ...plan, springFreeze: { date: '2026-04-20', basis: 'typical' as const } }
    expect(seasonWords(typical, us)).toContain('so the season counts from that date, April 20.')
  })

  it('gives a line per cut', () => {
    expect(cutLine(plan, 0, us)).toBe(
      'Cut 1, June 7: 987 GDD in 61 days since the season began, in the cutting window.',
    )
    expect(cutLine(plan, 1, us)).toBe('Cut 2, July 11: 991 GDD in 34 days since cut 1, in the cutting window.')
    const checked = parsePlan(body(planCutsBody))
    expect(cutLine(checked, 0, us)).toBe(
      'Cut 1, June 1: 826 GDD in 55 days since the season began, before the cutting window.',
    )
    expect(cutLine(checked, 1, us)).toBe(
      'Cut 2, July 10: 1,118 GDD in 39 days since cut 1, past the cutting window. Held in place.',
    )
    expect(cutLine(checked, 1, metric)).toContain('621 °C·d')
  })

  it('puts the fall rule and the period’s years in words', () => {
    const words = fallWords(plan, us)
    expect(words.rule).toContain('under 360 GDD')
    expect(words.rule).toContain('over 900 GDD')
    expect(words.check).toEqual([
      'With the last cut on November 1, the regrowth before the first fall killing freeze, in each of the 30 years from 1996 to 2025, was under 360 GDD in 25 years, over 900 GDD in no years and between them in no years; in 5 years the freeze came on or before the cut.',
      'In a typical year the killing freeze comes about November 18, after 129 GDD of regrowth.',
      'This year it came on November 24, after 183 GDD of regrowth.',
    ])
    expect(fallWords({ ...plan, fall: null }, us).check).toEqual([])
  })

  it('asks for a schedule, or checks the reader’s dates', () => {
    const base = { year: 2026, thisYear: 2026, period: 'last30' as const, target: null, held: [] as string[] }
    expect(planQuery({ ...base, by: 'interval', cuts: [] })).toEqual({
      units: 'us',
      year: undefined,
      period: undefined,
      interval: 1000,
    })
    expect(
      planQuery({ ...base, by: 'count', target: 3, cuts: [], held: ['2026-06-01'], year: 2024, period: 'last10' }),
    ).toEqual({
      units: 'us',
      year: 2024,
      period: 'last10',
      count: 3,
      held: ['2026-06-01'],
    })
    // With dates, only the held ones among them go, and neither interval nor count
    expect(
      planQuery({
        ...base,
        by: 'count',
        target: 4,
        cuts: ['2026-06-01', '2026-07-10'],
        held: ['2026-07-10', '2026-08-01'],
      }),
    ).toEqual({
      units: 'us',
      year: undefined,
      period: undefined,
      cuts: ['2026-06-01', '2026-07-10'],
      held: ['2026-07-10'],
    })
  })

  it('edits the plan’s own dates', () => {
    const checked = parsePlan(body(planCutsBody)).cuts
    expect(editCuts(checked, { kind: 'hold', index: 0 })).toEqual({
      cuts: ['2026-06-01', '2026-07-10', '2026-08-20', '2026-10-01'],
      held: ['2026-06-01', '2026-07-10'],
    })
    // A held cut moved keeps its hold, and the dates stay in order
    expect(editCuts(checked, { kind: 'date', index: 1, date: '2026-05-20' })).toEqual({
      cuts: ['2026-05-20', '2026-06-01', '2026-08-20', '2026-10-01'],
      held: ['2026-05-20'],
    })
    expect(editCuts(checked, { kind: 'remove', index: 1 })).toEqual({
      cuts: ['2026-06-01', '2026-08-20', '2026-10-01'],
      held: [],
    })
    // Two cuts moved onto one day become one
    expect(editCuts(checked, { kind: 'date', index: 0, date: '2026-07-10' }).cuts).toEqual([
      '2026-07-10',
      '2026-08-20',
      '2026-10-01',
    ])
  })

  it('draws the sawtooth with the cuts marked over the killing-freeze chance', () => {
    const [lo, hi] = planSpan(plan)
    expect(plan.days[lo].date).toBe('2026-03-01')
    expect(plan.days[hi].date).toBe('2026-12-15')
    const option = planOption({ plan, units: us, palette, today: TODAY }) as {
      series: { id: string; data: unknown[]; xAxisIndex: number }[]
      grid: unknown[]
    }
    expect(option.grid).toHaveLength(2)
    const cuts = option.series.find((s) => s.id === 'cuts')!
    const marked = cuts.data.filter((v) => v !== null) as { value: number; label: { formatter: string } }[]
    expect(marked.map((m) => [m.label.formatter, m.value])).toEqual([
      ['Cut 1', 987],
      ['Cut 2', 991],
      ['Cut 3', 984],
      ['Cut 4', 1010],
      ['Cut 5', 986],
    ])
    expect(option.series.find((s) => s.id === 'kill-chance')?.xAxisIndex).toBe(1)
    // After the freeze on November 24 nothing is counted, so the normal's days draw nothing here
    expect(option.series.find((s) => s.id === 'since-cut-normal')!.data.every((v) => v === null)).toBe(true)
  })

  it('draws the normal dashed from the last day of this year’s weather', () => {
    // As seen in summer: the days from September 1 on from the normal
    const summer = { ...plan, days: plan.days.map((d) => (d.date >= '2026-09-01' ? { ...d, kind: 'normal' } : d)) }
    const option = planOption({ plan: summer, units: us, palette, today: '2026-08-31' }) as {
      series: { id: string; data: unknown[] }[]
    }
    const dates = planTable(summer, us)
      .rows.map((r) => r.date)
      .toReversed()
    const normal = option.series.find((s) => s.id === 'since-cut-normal')!.data
    const solid = option.series.find((s) => s.id === 'since-cut')!.data
    expect(dates[normal.findIndex((v) => v !== null)]).toBe('2026-08-31')
    expect(dates[solid.findLastIndex((v) => v !== null)]).toBe('2026-08-31')
  })

  it('tables the plan newest first', () => {
    const t = planTable(plan, us)
    expect(t.columns[0]).toBe('Weather')
    expect(t.rows[0].date).toBe('2026-12-15')
    expect(t.rows.find((r) => r.date === '2026-06-07')?.values[3]).toBe('Cut 1')
  })
})

describe('words', () => {
  it('writes GDD in the reader’s units', () => {
    expect(gddText(1234.4, us)).toBe('1,234 GDD')
    expect(gddText(900, metric)).toBe('500 °C·d')
    expect(windowText({ from: 900, until: 1100 }, us)).toBe('900–1,100 GDD')
    expect(windowText({ from: 900, until: 1100 }, metric)).toBe('500–611 °C·d')
  })
})
