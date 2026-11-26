import { describe, expect, it } from 'vitest'

import { compareTable, freezeChances } from '@/lib/charts/climateCharts'
import { units } from '@/lib/units'
import chancesBody from '@/test/fixtures/climate/chances.json'
import presets from '@/test/fixtures/site/presets.json'
import compareBody from '@/test/fixtures/tools/compare-corn.json'
import cornBody from '@/test/fixtures/tools/corn-run.json'
import soybeanBody from '@/test/fixtures/tools/degree-days-soybean.json'
import body2012 from '@/test/fixtures/tools/year-2012.json'
import body2020 from '@/test/fixtures/tools/year-2020.json'
import { testPalette as palette } from '@/test/palette'
import type { TableResponse } from '@/types/api'

import {
  CHART_STAGES,
  cropChoices,
  cropGddOption,
  cropGddRows,
  cropGddSummary,
  dateReaching,
  dateText,
  fallChance,
  fallChances,
  latestTotal,
  normalCurve,
  outlookAnswer,
  outlookFromDegreeDays,
  outlookFromRun,
  plantingDate,
  stageRows,
  stageTargets,
  subjectWords,
  yearCurve,
  yearsCodec,
  type Outlook,
  type TargetDate,
} from './cropGdd'

// Recorded at Madison (43.07, −89.4) on November 25, 2026: a 2700 GDD hybrid planted May 8, soybean planted May 17
// with a 2,400 °F·d target, 2012 (Open-Meteo) and 2020 from May 8, the normal from May 8 (1996–2025)
const us = units('imperial')
const metric = units('metric')
const body = (b: unknown) => b as TableResponse
const corn = outlookFromRun(body(cornBody))!
const table = compareTable(body(compareBody))
const normal = normalCurve({ table, setting: 'modified_50_86', dates: corn.dates })
const years = [body2012, body2020].map((b) =>
  yearCurve({ body: body(b), setting: 'modified_50_86', dates: corn.dates }),
)
const chances = freezeChances(body(chancesBody))

describe('crops', () => {
  it('offers the presets counted from planting, corn first, with their killing freeze', () => {
    const crops = cropChoices(presets.data)
    expect(crops[0]).toMatchObject({ id: 'corn', setting: 'modified_50_86', model: 'corn-stages', freezeF: 28 })
    expect(crops.map((c) => c.id)).toContain('soybean')
    expect(crops.map((c) => c.id)).not.toContain('alfalfa')
    expect(crops.find((c) => c.id === 'spring-wheat')?.freezeF).toBeNull()
  })

  it('keeps up to three comparison years in the view', () => {
    expect(yearsCodec.parse('2012,2020')).toEqual([2012, 2020])
    expect(yearsCodec.parse('2012,2012,2019,2020,2021')).toEqual([2012, 2019, 2020])
    expect(yearsCodec.parse('x')).toBeUndefined()
    expect(yearsCodec.format([2012, 2020])).toBe('2012,2020')
  })

  it('plants on the reader’s date, else the typical one, else a fallback', () => {
    expect(plantingDate({ chosen: '2026-05-01', typical: '05-08', fallback: '05-10', year: 2026 })).toEqual({
      date: '2026-05-01',
      from: 'chosen',
    })
    // A date from another year (an old link) gives way to this year's typical date
    expect(plantingDate({ chosen: '2025-05-01', typical: '05-08', fallback: null, year: 2026 }).date).toBe('2026-05-08')
    expect(plantingDate({ chosen: null, typical: null, fallback: '05-10', year: 2026 })).toEqual({
      date: '2026-05-10',
      from: 'fallback',
    })
    expect(plantingDate({ chosen: null, typical: null, fallback: null, year: 2026 }).date).toBe('2026-05-15')
  })
})

describe('the corn stage model’s outlook', () => {
  it('runs from planting through December 31 with the stages the table lists', () => {
    expect(corn.dates[0]).toBe('2026-05-08')
    expect(corn.dates.at(-1)).toBe('2026-12-31')
    expect(corn.source).toBe('model')
    expect(corn.targets.map((t) => t.code)).toEqual([
      'VE',
      'V6',
      'V10',
      'VT',
      'R1',
      'R2',
      'R3',
      'R4',
      'R5',
      'R5.5',
      'R6',
    ])
    const r6 = corn.targets.at(-1)!
    expect(r6).toMatchObject({ name: 'Black layer', gdd: 2700, p50: '2026-09-27', reached: 10, of: 10 })
    expect(r6.status).toBe('reached')
    expect(corn.targets.find((t) => t.code === 'VT')?.estimated).toBe(true)
    expect(corn.projectionYears).toHaveLength(10)
  })

  it('takes the stage thresholds for the hybrid from the run', () => {
    const targets = stageTargets(body(cornBody), CHART_STAGES)
    expect(targets.map((t) => [t.code, t.gdd])).toEqual([
      ['VE', 110],
      ['V6', expect.any(Number)],
      ['R1', 1442.5],
      ['R5', expect.any(Number)],
      ['R6', 2700],
    ])
  })

  it('is null when the run has nothing to show (a planting past the forecast)', () => {
    const empty = {
      meta: { ...cornBody.meta, summary: { stages: [] } },
      data: { date: ['2026-12-10'], kind: [null], gdd_total: [0] },
    }
    expect(outlookFromRun(body(empty))).toBeNull()
  })

  it('knows the latest total that isn’t projected', () => {
    const latest = latestTotal(corn)!
    expect(latest.kind).toBe('forecast')
    expect(latest.date).toBe('2026-12-05')
    expect(latest.gdd).toBeCloseTo(3128.76, 1)
  })
})

describe('degree days for other crops', () => {
  it('reads the target from `/degree-days`, from the planting date on', () => {
    const outlook = outlookFromDegreeDays({
      body: body(soybeanBody),
      setting: 'modified_50_86',
      planting: '2026-05-17',
      targets: [{ code: 'target', name: 'Your target', gdd: 2400, estimated: false }],
    })
    expect(outlook.dates[0]).toBe('2026-05-17')
    expect(outlook.total[0]).not.toBeNull()
    expect(outlook.targets[0]).toMatchObject({ p50: '2026-09-10', status: 'reached', reached: 10, of: 10 })
    expect(outlook.source).toBe('degree-days')
  })
})

describe('the normal and past years', () => {
  it('aligns the normal from planting to the outlook’s dates', () => {
    expect(normal.mean).toHaveLength(corn.dates.length)
    const i = corn.dates.indexOf('2026-09-27')
    expect(normal.mean[i]).toBeCloseTo(2456.8, 1)
    expect(normal.low[i]).toBeLessThan(normal.mean[i]!)
    expect(normal.high[i]).toBeGreaterThan(normal.mean[i]!)
    expect(dateReaching(corn.dates, normal.mean, 110)).toBe('2026-05-20')
  })

  it('puts a past year on this year’s dates by month and day, naming Open-Meteo’s', () => {
    const [y2012, y2020] = years
    expect(y2012).toMatchObject({ year: 2012, openMeteo: true })
    expect(y2020.openMeteo).toBe(false)
    expect(y2012.values[0]).not.toBeNull()
    expect(dateReaching(y2012.dates, y2012.values, 2700)).toBe('2012-09-13')
    // 2020 fell short of 2,700 by December 31
    expect(dateReaching(y2020.dates, y2020.values, 2700)).toBeNull()
  })
})

describe('the freeze chance', () => {
  it('is the fall chance by a date, none before July', () => {
    expect(fallChance(chances, 28, '2026-10-15')).toBe(17)
    expect(fallChance(chances, 28, '2026-06-15')).toBe(0)
    expect(fallChance(chances, 30, '2026-10-15')).toBeNull()
    expect(fallChance(null, 28, '2026-10-15')).toBeNull()
    const line = fallChances(chances, 28, corn.dates)
    expect(line[0]).toBeNull()
    expect(line[corn.dates.indexOf('2026-11-13')]).toBe(70)
  })
})

const projected: TargetDate = {
  code: 'R6',
  name: 'Black layer',
  gdd: 2700,
  estimated: false,
  p10: '2026-09-14',
  p50: '2026-09-22',
  p90: '2026-10-03',
  reached: 10,
  of: 10,
  status: 'projected',
}
const latest = { date: '2026-08-10', gdd: 1650, kind: 'forecast' as const }
const subject = subjectWords({ crop: 'Corn (field)', hybrid: '2700', planting: '2026-05-01' })

describe('the answer in words', () => {
  it('projects maturity with its range and the chance of a freeze before it', () => {
    expect(subject).toBe('A 2700 GDD hybrid planted May 1')
    const words = outlookAnswer({
      subject,
      what: 'black layer',
      maturity: projected,
      latest,
      normalDate: '2026-09-30',
      freezeF: 28,
      chance: 15,
      units: us,
    })
    expect(words.headline).toBe(
      'A 2700 GDD hybrid planted May 1 is projected to reach black layer about Sep 22 (likely Sep 14 to Oct 3), with a 15% chance of a hard freeze (28 °F) before then.',
    )
    expect(words.details).toEqual([
      '1,650 °F·d since planting through the forecast (Aug 10).',
      'In a normal year it would reach black layer on Sep 30.',
    ])
  })

  it('says how many past years got there when not all did', () => {
    const words = outlookAnswer({
      subject,
      what: 'black layer',
      maturity: { ...projected, reached: 7 },
      latest,
      normalDate: null,
      freezeF: 30,
      chance: null,
      units: metric,
    })
    expect(words.headline).toMatch(/about Sep 22 \(likely Sep 14 to Oct 3\)\.$/)
    expect(words.details[1]).toBe(
      'With the weather of 10 past years after the forecast, it got there by December 31 in 7 of them; the dates are from those years.',
    )
    expect(words.details[0]).toMatch(/^917 °C·d since planting/)
  })

  it('says when maturity is unlikely, or was reached', () => {
    const unlikely = outlookAnswer({
      subject,
      what: 'black layer',
      maturity: { ...projected, p10: null, p50: null, p90: null, reached: 3, status: 'none' },
      latest,
      normalDate: null,
      freezeF: 28,
      chance: null,
      units: us,
    })
    expect(unlikely.headline).toBe(
      'A 2700 GDD hybrid planted May 1 is unlikely to reach black layer this year: with the weather of 10 past years after the forecast, it got there by December 31 in only 3 of them.',
    )
    expect(unlikely.details).toEqual(['So far: 1,650 °F·d through Aug 10.'])

    const r6 = corn.targets.at(-1)!
    const reached = outlookAnswer({
      subject: subjectWords({ crop: 'Corn (field)', hybrid: '2700', planting: '2026-05-08' }),
      what: 'black layer',
      maturity: r6,
      latest: latestTotal(corn),
      normalDate: dateReaching(corn.dates, normal.mean, 2700),
      freezeF: 28,
      chance: 3,
      units: us,
    })
    expect(reached.headline).toBe('A 2700 GDD hybrid planted May 8 reached black layer on Sep 27.')
    expect(reached.details).toEqual(['In a normal year it would have reached it on Nov 13.'])

    const forecast = outlookAnswer({
      subject: subjectWords({ crop: 'Soybean', hybrid: null, planting: '2026-05-17' }),
      what: '2,400 °F·d',
      maturity: { ...projected, p10: '2026-09-20', p50: '2026-09-20', p90: '2026-09-20', status: 'forecast' },
      latest: null,
      normalDate: null,
      freezeF: 28,
      chance: 2,
      units: us,
    })
    expect(forecast.headline).toBe(
      'Soybean planted May 17 is forecast to reach 2,400 °F·d on Sep 20, with a 2% chance of a hard freeze (28 °F) by then.',
    )
  })

  it('says a season without a projection fell short', () => {
    const words = outlookAnswer({
      subject,
      what: 'black layer',
      maturity: { ...projected, p10: null, p50: null, p90: null, reached: 0, of: 1, status: 'none' },
      latest: { date: '2026-12-31', gdd: 2450, kind: 'observed' },
      normalDate: null,
      freezeF: 28,
      chance: null,
      units: us,
    })
    expect(words.headline).toBe('A 2700 GDD hybrid planted May 1 had 2,450 °F·d by Dec 31, short of black layer.')
  })
})

describe('the table', () => {
  it('gives each stage this year’s date, the normal year’s and each past year’s', () => {
    const rows = stageRows({ outlook: corn, normal, years })
    const r6 = rows.at(-1)!
    expect(r6).toMatchObject({ code: 'R6', thisYear: 'Sep 27', normal: '2026-11-13', years: ['2012-09-13', null] })
    expect(dateText(projected)).toBe('About Sep 22 (Sep 14 – Oct 3)')
    expect(dateText({ ...projected, reached: 7 })).toBe('About Sep 22 (Sep 14 – Oct 3), 7 of 10 years')
    expect(dateText({ ...projected, status: 'forecast', p10: '2026-09-22', p90: '2026-09-22' })).toBe(
      'Sep 22 (forecast)',
    )
    expect(dateText({ ...projected, p50: null, reached: 3, status: 'none' })).toBe('3 of 10 years')
    expect(dateText({ ...projected, p50: null, reached: 0, of: 1, status: 'none' })).toBe('Not reached')
  })
})

describe('the chart', () => {
  const option = cropGddOption({
    outlook: corn,
    normal,
    normalYears: table.years,
    years,
    stages: stageTargets(body(cornBody), CHART_STAGES),
    chances: fallChances(chances, 28, corn.dates),
    freezeF: 28,
    units: us,
    palette,
    today: '2026-11-25',
  }) as {
    grid: object[]
    legend: { data: string[] }
    series: { id?: string; name?: string; xAxisIndex?: number; data: unknown[]; markLine?: { data: object[] } }[]
  }
  const byId = (id: string) => option.series.find((s) => s.id === id)!

  it('stacks GDD since planting over the fall freeze chance', () => {
    expect(option.grid).toHaveLength(2)
    expect(byId('freeze').xAxisIndex).toBe(1)
    expect(option.legend.data).toEqual([
      'Normal (1996–2025), usual range',
      'Normal (1996–2025)',
      'Projection, 10th–90th percentile',
      '2012',
      '2020',
      '2026',
      '2026, projected',
      'Chance of a hard freeze (28 °F) by this date',
    ])
  })

  it('draws the observed and forecast solid, the projection dashed from the day before it', () => {
    const solid = byId('this-year').data
    const dashed = byId('projection').data
    const from = corn.kinds.indexOf('projection')
    expect(solid[from]).toBeNull()
    expect(solid[from - 1]).not.toBeNull()
    expect(dashed[from - 2]).toBeNull()
    expect(dashed[from - 1]).toBe(solid[from - 1])
  })

  it('marks today and the stages', () => {
    const marks = byId('this-year').markLine!.data as { xAxis?: string; label: { formatter: string } }[]
    expect(marks.map((m) => m.label.formatter)).toEqual(['Today', 'VE', 'V6', 'R1', 'R5', 'R6'])
  })

  it('converts to metric at display', () => {
    const metricOption = cropGddOption({
      outlook: corn,
      normal: null,
      normalYears: null,
      years: [],
      stages: [],
      chances: corn.dates.map(() => null),
      freezeF: 28,
      units: metric,
      palette,
      today: '2026-11-25',
    }) as typeof option
    const solid = metricOption.series.find((s) => s.id === 'this-year')!.data as number[]
    const i = corn.dates.indexOf('2026-09-27')
    expect(solid[i]).toBeCloseTo((corn.total[i] as number) / 1.8, 2)
  })

  it('says what it shows in words and as a table, newest first', () => {
    const maturity = corn.targets.at(-1)!
    expect(cropGddSummary({ outlook: corn, maturity, normalDate: '2026-11-13', freezeF: 28, units: us })).toBe(
      '3,129 °F·d since planting through Dec 5. Black layer: Sep 27. A normal year reaches it on Nov 13. The lower chart shows the chance that the first fall hard freeze (28 °F) has come by each date.',
    )
    const data = cropGddRows({
      outlook: corn as Outlook,
      normal,
      years,
      chances: fallChances(chances, 28, corn.dates),
      units: us,
    })
    expect(data.columns).toHaveLength(7)
    expect(data.rows[0].date).toBe('2026-12-31')
    expect(data.rows.at(-1)!.date).toBe('2026-05-08')
  })
})
