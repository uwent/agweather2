import { describe, expect, it } from 'vitest'

import { modelRun, type ModelRun } from '@/lib/charts/modelCharts'
import { units as unitsFor } from '@/lib/units'
import body from '@/test/fixtures/site/model-oak-wilt.json'
import type { TableResponse } from '@/types/api'

import {
  defaultMapDate,
  degreeDaysF,
  flownWords,
  oakWiltAnswer,
  oakWiltWords,
  reached,
  RESTRICTED_DD_F,
} from './oakWilt'

// Madison's cell, January 1 to August 31, 2026, recorded in metric (°C·d); degree days reached 231 °F·d on April 16.
// `flown` was added to the recording from its degree days (the dev server ran model 0.2).
const us = unitsFor('imperial')
const metric = unitsFor('metric')
const full = () => modelRun(body as unknown as TableResponse)

/** The run as it was seen on `today`: days after it forecast, and none past `last` */
function seenOn(today: string, last = '2026-12-31'): ModelRun {
  const run = full()
  run.table.days = run.table.days
    .filter((day) => day.date <= last)
    .map((day) => (day.date > today ? { ...day, kind: 'forecast' as const } : day))
  const n = run.table.days.length
  return { ...run, level: run.level.slice(0, n), label: run.label.slice(0, n) }
}

describe('reading the run', () => {
  it('converts the degree days to °F·d whatever units the run came in', () => {
    const dd = degreeDaysF(full())
    const k = full().table.days.findIndex((day) => day.date === '2026-04-16')
    expect(dd[k]).toBeCloseTo(232.5, 0)
  })

  it('finds the day degree days first reached 231 on or before July 15, and its kind', () => {
    expect(reached(full(), 2026)).toEqual({ date: '2026-04-16', kind: 'observed' })
    expect(reached(seenOn('2026-04-10'), 2026)).toEqual({ date: '2026-04-16', kind: 'forecast' })
    expect(reached(seenOn('2026-04-01', '2026-04-11'), 2026)).toBeNull()
  })
})

describe('oakWiltAnswer', () => {
  it('is restricted from 231 degree days through July 15, with the model level beside it', () => {
    const answer = oakWiltAnswer({ run: seenOn('2026-05-01'), today: '2026-05-01', year: 2026 })
    expect(answer.phase).toBe('restricted')
    expect(answer.start).toEqual({ date: '2026-04-16', kind: 'observed' })
    expect(answer.ddF).toBeGreaterThan(RESTRICTED_DD_F)
    expect(answer.label).toBe('Very high')
    expect(answer.flown).toBe(25)
    // July 14: still DNR's period, though the model is already Low (past 95% of the flight)
    const late = oakWiltAnswer({ run: seenOn('2026-07-14'), today: '2026-07-14', year: 2026 })
    expect([late.phase, late.label]).toEqual(['restricted', 'Low'])
    expect(oakWiltAnswer({ run: seenOn('2026-07-15'), today: '2026-07-15', year: 2026 }).phase).toBe('restricted')
  })

  it('is before the period under 231, saying when the forecast reaches it', () => {
    const answer = oakWiltAnswer({ run: seenOn('2026-04-10'), today: '2026-04-10', year: 2026 })
    expect(answer.phase).toBe('before')
    expect(answer.start?.kind).toBe('forecast')
    const words = oakWiltWords(answer, us)
    expect(words.headline).toBe('The beetles that spread oak wilt are not yet flying in numbers.')
    expect(words.details.join(' ')).toContain('expected to reach 231 °F·d on April 16, by the forecast')
    expect(words.details.join(' ')).toContain(
      'calendar restricted period began on April 1 in the south zone, and in the north zone it begins on April 15.',
    )
  })

  it('says when the forecast ends without reaching 231', () => {
    const answer = oakWiltAnswer({ run: seenOn('2026-03-25', '2026-04-04'), today: '2026-03-25', year: 2026 })
    expect(answer.start).toBeNull()
    expect(oakWiltWords(answer, us).details).toContain('They aren’t expected to reach 231 °F·d by April 4.')
  })

  it('is winter before March, and after July 15 says when this year’s period began', () => {
    expect(oakWiltAnswer({ run: seenOn('2026-02-10', '2026-02-20'), today: '2026-02-10', year: 2026 }).phase).toBe(
      'winter',
    )
    const after = oakWiltAnswer({ run: full(), today: '2026-08-20', year: 2026 })
    expect(after.phase).toBe('after')
    const words = oakWiltWords(after, us)
    expect(words.headline).toBe('Wisconsin’s restricted period for oaks ended on July 15.')
    expect(words.details[0]).toBe('This year the restricted period began here on April 16 and ended on July 15.')
  })

  it('summarizes a past season at July 15', () => {
    const answer = oakWiltAnswer({ run: full(), today: '2027-05-01', year: 2026 })
    expect(answer.phase).toBe('past')
    expect(answer.date).toBe('2026-07-15')
    expect(oakWiltWords(answer, us).headline).toBe('In 2026 the restricted period began here on April 16.')
  })
})

describe('words', () => {
  it('puts the restricted period in DNR’s terms, in the reader’s units', () => {
    const answer = oakWiltAnswer({ run: seenOn('2026-05-01'), today: '2026-05-01', year: 2026 })
    expect(oakWiltWords(answer, us).headline).toBe('Avoid pruning, wounding or harvesting oaks.')
    expect(oakWiltWords(answer, us).details[0]).toBe(
      'Degree days here reached 231 °F·d on April 16, which starts Wisconsin’s restricted period for oaks. It runs through July 15.',
    )
    expect(oakWiltWords(answer, metric).details[0]).toContain('reached 128 °C·d on April 16')
  })

  it('gives the share of C. truncatus flown as the paper’s percentile reached', () => {
    expect(flownWords(null)).toBeNull()
    expect(flownWords(0)).toMatch(/^Fewer than 5%/)
    expect(flownWords(50)).toMatch(/^At least 50% of the season’s Colopterus truncatus/)
  })
})

describe('defaultMapDate', () => {
  it('is today in season and April 15 of the latest season otherwise', () => {
    expect(defaultMapDate('2026-05-20')).toBe('2026-05-20')
    expect(defaultMapDate('2026-11-25')).toBe('2026-04-15')
    expect(defaultMapDate('2027-01-10')).toBe('2026-04-15')
  })
})
