import { describe, expect, it } from 'vitest'

import { modelRun } from '@/lib/charts/modelCharts'
import { units } from '@/lib/units'
import cornRun from '@/test/fixtures/site/model-corn-stages.json'
import ecbRun from '@/test/fixtures/site/model-ecb-2025.json'
import lateBlightRun from '@/test/fixtures/site/model-late-blight.json'
import type { SiteModelInfo } from '@/types'
import type { TableResponse } from '@/types/api'

import { decodeChosen, encodeChosen, runParams, settingNames } from './modelOptions'
import { answer, dailyPair, nextMilestone, recentRows, seasonWords } from './modelText'

const us = units('imperial')
const q = (name: string, label: string, unit = 'index') => ({ name, label, unit, description: '' })
const lateBlight = {
  outputs: [
    q('dsv', 'Disease severity values'),
    q('dsv_14_day', 'DSVs in the last 14 days'),
    q('dsv_total', 'DSVs since emergence'),
  ],
  risk_levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'],
  stages: [],
  season: ['05-01', '09-30'],
}
const ecb = {
  outputs: [q('dd_total', 'Degree days since the biofix', 'degF_day'), q('dd', 'Degree days', 'degF_day')],
  risk_levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'],
  stages: [],
  season: null,
}
const corn = {
  outputs: [q('stage', 'Stage'), q('gdd_total', 'GDD since planting', 'degF_day'), q('gdd', 'GDD', 'degF_day')],
  risk_levels: [],
  stages: [{ code: 'R6', name: 'Black layer' }],
  season: ['04-01', '10-31'],
}
const today = '2026-11-25'

describe('answer', () => {
  it('says a model out of season is, and what its last day of season gave', () => {
    const said = answer({ model: lateBlight, run: modelRun(lateBlightRun as TableResponse), units: us, today })
    expect(said.headline).toBe('Out of season today, Nov 25. The model runs from May 1 to Sep 30.')
    expect(said.detail).toMatch(
      /^On Sep 30, the last day of its season, the risk was \w+\. DSVs since emergence: \d+, counted from May 15\.$/,
    )
    expect(said.level).not.toBeNull()
  })

  it("gives a past season's last day, with its running total in the reader's units", () => {
    const said = answer({ model: ecb, run: modelRun(ecbRun as TableResponse), units: us, today })
    expect(said.headline).toMatch(/^Very low risk on Sep 30, 2025\.$/)
    expect(said.detail).toMatch(/^Degree days since the biofix: [\d,]+ °F·d, counted from Jan 1\.$/)
  })

  it("says a crop model's stage", () => {
    const said = answer({ model: corn, run: modelRun(cornRun as TableResponse), units: us, today })
    expect(said.headline).toBe('The crop is at Black layer (R6) today, Nov 25.')
    expect(said.level).toBeNull()
  })

  it('names the risk today in season', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    const said = answer({ model: lateBlight, run, units: us, today: '2026-08-19' })
    expect(said.headline).toBe('High risk today, Aug 19.')
  })
})

describe('nextMilestone', () => {
  it('gives the next milestone after the day, else the last one reached', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    expect(nextMilestone({ run, today: '2026-06-01' })).toBe('Next: Moderate risk on Jun 29.')
    expect(nextMilestone({ run, today })).toBe('Last reached: High risk on Aug 19.')
  })
})

describe('the table', () => {
  it('shows the 7 days through today and the forecast', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    const rows = recentRows(run, today)
    const dates = rows.map((i) => run.table.days[i].date)
    expect(dates[0]).toBe('2026-11-19')
    expect(dates.at(-1)).toBe(run.table.days.at(-1)!.date)
    expect(dates.length).toBe(7 + 10)
  })

  it('pairs a daily amount with its running total', () => {
    expect(dailyPair(lateBlight)).toEqual({ daily: 'dsv', total: 'dsv_total' })
    expect(dailyPair({ outputs: [q('probability', 'Probability')] })).toBeNull()
  })

  it('says a season in words', () => {
    expect(seasonWords(['05-01', '09-30'])).toBe('May 1 to Sep 30')
    expect(seasonWords(null)).toBeNull()
  })
})

describe('settings', () => {
  const model: Pick<SiteModelInfo, 'id' | 'options' | 'biofix' | 'planting' | 'season'> = {
    id: 'late-blight-dsv',
    options: [
      {
        name: 'resistance',
        label: 'Resistance',
        choices: [{ value: 'low', label: 'Low' }],
        default: 'low',
        date: false,
      },
    ],
    biofix: { default: '05-15', label: 'Emergence', stage: 'Emerged (EM)' },
    planting: { crop: 'Potato', typical_dates: true, options: [] },
    season: ['05-01', '09-30'],
  }

  it('keeps settings as view text', () => {
    const chosen = { biofix: '2026-06-30', planting_date: 'mid', resistance: 'a;b=c' }
    expect(decodeChosen(encodeChosen(chosen))).toEqual(chosen)
    expect(encodeChosen({ biofix: '' })).toBe('')
    expect(decodeChosen('junk;=x;a=%E0%A4%A')).toEqual({})
  })

  it('sends only what the model takes, and a date only in its own season', () => {
    expect(settingNames(model)).toEqual(['biofix', 'planting_date', 'resistance'])
    const chosen = { biofix: '2026-06-30', planting_date: 'mid', other: 'x', resistance: 'low' }
    expect(runParams({ model, chosen, year: 2026, thisYear: 2026, projection: true })).toEqual({
      params: { biofix: '2026-06-30', planting_date: 'mid', resistance: 'low', projection: true },
      notes: [],
    })
    const past = runParams({ model, chosen, year: 2025, thisYear: 2026, projection: true })
    expect(past.params).toEqual({ planting_date: 'mid', resistance: 'low', end: '2025-09-30' })
    expect(past.notes).toEqual(['Your start date is in 2026, so 2025 uses the default.'])
  })

  it('drops a planting date that is neither a date nor a typical one', () => {
    const found = runParams({ model, chosen: { planting_date: 'soon' }, year: 2026, thisYear: 2026, projection: false })
    expect(found.params).toEqual({})
  })
})
