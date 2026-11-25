import { describe, expect, it } from 'vitest'

import risk from '@/test/fixtures/site/risk.json'
import riskSpan from '@/test/fixtures/site/risk-span.json'
import type { TableResponse } from '@/types/api'

import { forecastIndex, riskSpanQuery, riskSpans, rowsOn, trendWords, type ModelRisk } from './riskSpan'

const today = '2026-11-25'

describe('riskSpans', () => {
  it('gives each model its days in order, from two weeks back through the forecast', () => {
    const spans = riskSpans(riskSpan as TableResponse, today)
    expect([...spans.keys()]).toContain('potato-volunteer')
    const days = spans.get('potato-volunteer')!.days
    expect(days[0].date).toBe('2026-11-11')
    expect(days.at(-1)!.date).toBe('2026-12-05')
    expect(days.find((d) => d.date === today)!.kind).toBe('partial')
    expect(forecastIndex(days)).toBe(14)
  })

  it('reads a one-day answer as today', () => {
    const spans = riskSpans(risk as TableResponse, today)
    expect([...spans.values()].every((s) => s.days.length === 1 && s.days[0].date === today)).toBe(true)
  })

  it('asks from two weeks back, leaving the end to the API (the forecast’s last day)', () => {
    expect(riskSpanQuery(today)).toEqual({ start: '2026-11-11' })
  })
})

describe('rowsOn', () => {
  it("keeps one day's rows of a span, and a one-day answer as it is", () => {
    const one = rowsOn(riskSpan as TableResponse, today)
    const data = one.data as Record<string, unknown[]>
    expect(data.date.every((d) => d === today)).toBe(true)
    expect(data.model.length).toBe(5)
    expect(rowsOn(risk as TableResponse, today)).toBe(risk)
  })
})

describe('trendWords', () => {
  const span = (levels: (number | null)[]): ModelRisk => ({
    model: 'm',
    name: 'M',
    days: levels.map((level, i) => ({
      date: `2026-11-${String(24 + i).padStart(2, '0')}`,
      kind: i < 1 ? 'observed' : 'forecast',
      level,
      label: level === null ? null : ['Very low', 'Low', 'Moderate', 'High', 'Very high'][level],
      inSeason: true,
    })),
  })

  it('says where the risk goes through the forecast', () => {
    expect(trendWords(span([1, 1, 1, 3, 3]), today)).toBe('Rising to High on Nov 27')
    expect(trendWords(span([3, 3, 2, 2]), today)).toBe('Falling to Moderate on Nov 26')
    expect(trendWords(span([2, 2, 2]), today)).toBe('Moderate through Nov 26')
    expect(trendWords(span([null, null, 1]), today)).toBe('Low from Nov 26')
    expect(trendWords(span([2, 2, null]), today)).toBe('Moderate until Nov 25, then no risk level')
    expect(trendWords(span([null, null]), today)).toBe('No risk level through Nov 25')
  })
})
