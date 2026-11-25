import { describe, expect, it } from 'vitest'

import { riskColor, riskRank } from '@/lib/riskLevels'
import type { ModelEntry } from '@/types'
import type { TableResponse } from '@/types/api'

import { riskModels, topRisks, weatherByPoint, weatherQuery } from './cardData'

const model = (id: string, crops: string[], levels = 5): ModelEntry => ({
  id,
  name: id,
  group: 'disease',
  crops,
  status: 'beta',
  risk_levels: Array.from({ length: levels }, (_, k) => `L${k}`),
  season: null,
})

const catalog = [
  model('late-blight-dsv', ['potato', 'tomato']),
  model('tar-spot', ['corn'], 4),
  model('apple-scab', ['apple'], 2),
  model('corn-stages', ['corn'], 0),
  model('x', ['other']),
  model('y', ['other']),
  model('hidden', ['other']),
  model('none', ['other']),
]

const table = (data: Record<string, unknown[]>) => ({ meta: {}, data }) as unknown as TableResponse
const prefs = { crops: undefined, models: undefined, hiddenModels: [], options: {}, planting: undefined }

describe('riskModels', () => {
  it('asks for the chosen models with risk; else the chosen crops’; else lets the API choose', () => {
    expect(riskModels(prefs, catalog)).toBeUndefined()
    expect(riskModels({ ...prefs, crops: ['corn'] }, catalog)).toEqual(['tar-spot'])
    expect(riskModels({ ...prefs, models: ['corn-stages', 'apple-scab'] }, catalog)).toEqual(['apple-scab'])
    expect(riskModels({ ...prefs, crops: ['corn', 'potato'], hiddenModels: ['tar-spot'] }, catalog)).toEqual([
      'late-blight-dsv',
    ])
  })
})

describe('topRisks', () => {
  it('keeps the three highest on their own scales, counts the rest, drops hidden models', () => {
    const body = table({
      model: ['late-blight-dsv', 'tar-spot', 'apple-scab', 'x', 'y', 'hidden', 'none'],
      name: ['Late blight', 'Tar spot', 'Apple scab', 'X', 'Y', 'Hidden', 'None'],
      risk_level: [2, 3, 0, 1, 1, 4, null],
      risk_label: ['Moderate', 'High', 'Low', 'Low', 'Low', 'Very high', null],
    })
    const found = topRisks(body, catalog, ['hidden'])
    expect(found.top.map((r) => [r.name, r.label, r.levels])).toEqual([
      ['Tar spot', 'High', 4],
      ['Late blight', 'Moderate', 5],
      ['X', 'Low', 5],
    ])
    expect([found.more, found.none]).toEqual([2, 1])
  })

  it("ranks today's rows of a span, giving each its days for the sparkline, and counts one out of season as none", () => {
    const body = table({
      date: ['2026-11-24', '2026-11-25', '2026-11-26', '2026-11-24', '2026-11-25', '2026-11-26'],
      model: ['late-blight-dsv', 'late-blight-dsv', 'late-blight-dsv', 'x', 'x', 'x'],
      name: ['Late blight', 'Late blight', 'Late blight', 'X', 'X', 'X'],
      kind: ['observed', 'partial', 'forecast', 'observed', 'partial', 'forecast'],
      risk_level: [4, 1, 3, 2, 2, 2],
      risk_label: ['L4', 'L1', 'L3', 'L2', 'L2', 'L2'],
      in_season: [true, true, true, false, false, false],
    })
    const found = topRisks(body, catalog, [], 3, '2026-11-25')
    expect(found.top.map((r) => [r.model, r.level])).toEqual([['late-blight-dsv', 1]])
    expect(found.top[0].days?.map((d) => d.level)).toEqual([4, 1, 3])
    expect(found.none).toBe(1)
  })

  it('drops models the catalog doesn’t list (retired ones)', () => {
    const body = table({ model: ['retired'], name: ['Retired'], risk_level: [4], risk_label: ['Very high'] })
    expect(topRisks(body, catalog)).toEqual({ top: [], more: 0, none: 0 })
  })
})

describe('weather', () => {
  it('asks for several sites’ today and tomorrow in stored units', () => {
    expect(
      weatherQuery(
        [
          { lat: 43.07, lng: -89.4 },
          { lat: 44, lng: -90 },
        ],
        '2026-11-25',
      ),
    ).toEqual({
      points: '43.07,-89.4;44,-90',
      vars: ['air_temperature_max', 'air_temperature_min', 'precipitation_sum'],
      start: '2026-11-25',
      end: '2026-11-26',
      units: 'metric',
    })
  })

  it('reads each point’s days by its index', () => {
    const body = table({
      point: [0, 0, 1],
      date: ['2026-11-25', '2026-11-26', '2026-11-26'],
      kind: ['partial', 'forecast', 'forecast'],
      air_temperature_max: [5.8, 7.4, 3],
      air_temperature_min: [-1.7, 2.5, -4],
      precipitation_sum: [null, 0, 1.2],
    })
    const [a, b] = weatherByPoint(body, 2, '2026-11-25')
    expect(a.today).toEqual({ date: '2026-11-25', kind: 'partial', high: 5.8, low: -1.7, precipitation: null })
    expect(a.tomorrow?.high).toBe(7.4)
    expect(b.today).toBeNull()
    expect(b.tomorrow?.precipitation).toBe(1.2)
  })
})

describe('risk colors', () => {
  it('use the severity tokens for five levels, the probability ones otherwise', () => {
    expect(riskColor(4, 5)).toBe('var(--color-risk-severity-5)')
    expect(riskColor(0, 4)).toBe('var(--color-risk-probability-1)')
    expect(riskColor(2, 3)).toBe('var(--color-risk-probability-4)')
    expect(riskColor(1, 2)).toBe('var(--color-risk-probability-4)')
    expect(riskColor(null, 5)).toBeUndefined()
    expect(riskRank(3, 4)).toBe(1)
    expect(riskRank(2, 5)).toBe(0.5)
  })
})
