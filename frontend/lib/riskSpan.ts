// `/risk` over several days (`start`/`end`, a row per model per day led by `date`) as each model's days, for the
// risk sparklines on site cards and the site page (track 3, Q1): one request gives every model's level from two
// weeks back through the forecast. A one-day answer (no `date` column) reads as one day, `today`.

import type { TableResponse } from '@/types/api'

import { addDays, formatDate } from './dates'

export type RiskDay = {
  date: string
  kind: string | null
  level: number | null
  label: string | null
  inSeason: boolean | null
}

export type ModelRisk = { model: string; name: string; days: RiskDay[] }

/** The days before today a sparkline shows: two weeks, then the forecast */
export const SPARK_DAYS_BACK = 14

/** The `/risk` query for a sparkline: from two weeks back through the forecast's last day (the API's default end) */
export function riskSpanQuery(today: string): { start: string } {
  return { start: addDays(today, -SPARK_DAYS_BACK) }
}

/** Each model's days, in the answer's order of models */
export function riskSpans(body: Pick<TableResponse, 'data'>, today: string): Map<string, ModelRisk> {
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, (string | number | boolean | null)[]>
  const models = (data.model ?? []) as string[]
  const spans = new Map<string, ModelRisk>()
  models.forEach((model, i) => {
    let span = spans.get(model)
    if (!span) {
      span = { model, name: String(data.name?.[i] ?? model), days: [] }
      spans.set(model, span)
    }
    const level = data.risk_level?.[i]
    const label = data.risk_label?.[i]
    const inSeason = data.in_season?.[i]
    span.days.push({
      date: String(data.date?.[i] ?? today),
      kind: (data.kind?.[i] as string | null) ?? null,
      level: typeof level === 'number' ? level : null,
      label: typeof label === 'string' ? label : null,
      inSeason: typeof inSeason === 'boolean' ? inSeason : null,
    })
  })
  for (const span of spans.values()) span.days.sort((a, b) => a.date.localeCompare(b.date))
  return spans
}

/** The rows of one day (today's, for a card or "Risk now"): the answer's columns kept only where `date` is that
 * day, so code reading a one-day answer reads a span the same way */
export function rowsOn<T extends Pick<TableResponse, 'data'>>(body: T, day: string): T {
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, unknown[]>
  if (!data.date) return body
  const keep = data.date.map((date) => date === day)
  return {
    ...body,
    data: Object.fromEntries(Object.entries(data).map(([name, values]) => [name, values.filter((_, i) => keep[i])])),
  }
}

const isAhead = (day: RiskDay) => day.kind === 'forecast' || day.kind === 'partial' || day.kind === 'projection'

/**
 * The sparkline in words, for its text alternative: where the risk goes from today through the forecast. "Rising
 * to High on Nov 28", "Falling to Low on Dec 1", "Moderate through Dec 5", or "No risk level through Dec 5".
 */
export function trendWords(span: ModelRisk, today: string): string {
  const days = span.days
  const now = days.find((d) => d.date === today) ?? days.findLast((d) => d.date <= today)
  const last = days.at(-1)
  if (!now || !last) return 'No risk level for these days.'
  const ahead = days.filter((d) => d.date > now.date)
  const change = ahead.find((d) => d.level !== now.level)
  if (change && change.level !== null && now.level !== null)
    return `${change.level > now.level ? 'Rising' : 'Falling'} to ${change.label} on ${formatDate(change.date)}`
  if (change && change.level !== null) return `${change.label} from ${formatDate(change.date)}`
  if (change) return `${now.label} until ${formatDate(addDays(change.date, -1))}, then no risk level`
  if (now.level === null) return `No risk level through ${formatDate(last.date)}`
  return `${now.label} through ${formatDate(last.date)}`
}

/** The first day that's forecast (or partial, or projected), as an index; -1 without one */
export function forecastIndex(days: RiskDay[]): number {
  return days.findIndex(isAhead)
}
