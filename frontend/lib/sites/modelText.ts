// A model at a site in words (track 3 step 6): the answer the page leads with ("High risk today, Nov 25. DSVs since
// emergence: 22, counted from June 30."), the next milestone ("Next: High risk expected Nov 28 (forecast)."), and
// the rows and columns of the NEWA-style table (the past 7 days and the forecast, with 2-, 7- and 14-day sums).

import type { SiteModelInfo } from '@/types'

import type { ModelRun } from '../charts/modelCharts'
import { formatValue, riskCounts } from '../charts/modelCharts'
import { isForecast } from '../charts/kinds'
import { formatDate } from '../dates'
import type { Day } from '../tableRows'
import type { Units } from '../units'

type Model = Pick<SiteModelInfo, 'outputs' | 'risk_levels' | 'stages' | 'season'>

/** The day the answer is about: today if the run has it, else its last day before any projection (a past season) */
export function answerIndex(run: ModelRun, today: string): number {
  const days = run.table.days
  const at = days.findIndex((day) => day.date === today)
  if (at >= 0) return at
  return days.findLastIndex((day) => day.kind !== 'projection')
}

/** A daily amount with a running total beside it in the outputs (`dsv` and `dsv_total`, `dd` and `dd_total`) */
export function dailyPair(model: Pick<SiteModelInfo, 'outputs'>): { daily: string; total: string } | null {
  const names = new Set(model.outputs.map((q) => q.name))
  const daily = model.outputs.find((q) => names.has(`${q.name}_total`))
  return daily ? { daily: daily.name, total: `${daily.name}_total` } : null
}

/** "May 1 to September 30" */
export function seasonWords(season: readonly [string, string] | readonly string[] | null): string | null {
  if (!season) return null
  const [first, last] = season.map((mmdd) => formatDate(`2001-${mmdd}`))
  return `${first} to ${last}`
}

export type Answer = {
  /** The answer's first sentence ("High risk today, Nov 25.") */
  headline: string
  /** What it rests on ("DSVs since emergence: 22, counted from June 30."), or null */
  detail: string | null
  /** The level shown beside it, null without one */
  level: number | null
}

/** The page's answer: the risk (or a crop model's stage) on today or the run's last day, in words */
export function answer({
  model,
  run,
  units,
  today,
}: {
  model: Model
  run: ModelRun
  units: Units
  today: string
}): Answer {
  const days = run.table.days
  const i = answerIndex(run, today)
  if (i < 0) return { headline: 'The model has no results for these days yet.', detail: null, level: null }
  const day = days[i]
  const when = day.date === today ? `today, ${formatDate(day.date)}` : `on ${formatDate(day.date, { year: true })}`
  const pair = dailyPair(model)
  const totalLabel = pair ? model.outputs.find((q) => q.name === pair.total)?.label : null
  const totalOn = (d: Day) => {
    if (!pair || !totalLabel || d.values[pair.total] == null) return null
    const from = run.request.biofix ? `, counted from ${formatDate(run.request.biofix)}` : ''
    return `${totalLabel}: ${formatValue(run.table, units, pair.total, d)}${from}.`
  }

  if (run.stage) {
    const code = run.stage[i]
    const stage = model.stages.find((s) => s.code === code)
    if (!code)
      return {
        headline: `The crop has no stage ${when}: before planting or after the season.`,
        detail: totalOn(day),
        level: null,
      }
    return {
      headline: `The crop is at ${stage ? `${stage.name} (${code})` : code} ${when}.`,
      detail: totalOn(day),
      level: null,
    }
  }

  if (model.risk_levels.length) {
    if (run.inSeason && run.inSeason[i] === false) {
      const season = seasonWords(model.season)
      const last = run.inSeason.findLastIndex((inSeason, k) => inSeason === true && k <= i)
      const ran = season ? ` The model runs from ${season}.` : ''
      if (last >= 0 && run.label[last])
        return {
          headline: `Out of season ${when}.${ran}`,
          detail: `On ${formatDate(days[last].date)}, the last day of its season, the risk was ${run.label[last]!.toLowerCase()}.${totalOn(days[last]) ? ` ${totalOn(days[last])}` : ''}`,
          level: run.level[last],
        }
      return { headline: `Out of season ${when}.${ran}`, detail: null, level: null }
    }
    const label = run.label[i]
    if (!label) return { headline: `No risk level ${when}.`, detail: run.warnings[0] ?? null, level: null }
    const gated = !riskCounts(run, i) ? ' The crop isn’t at a susceptible stage, so the risk matters less now.' : ''
    return { headline: `${label} risk ${when}.${gated}`, detail: totalOn(day), level: run.level[i] }
  }

  const primary = model.outputs[0]
  if (primary && day.values[primary.name] != null)
    return {
      headline: `${primary.label} ${when}: ${formatValue(run.table, units, primary.name, day)}.`,
      detail: totalOn(day),
      level: null,
    }
  return { headline: `No result ${when}.`, detail: null, level: null }
}

const KIND_WORDS: Record<string, string> = {
  forecast: ' (forecast)',
  partial: ' (forecast)',
  projection: ' (projected from past years’ weather)',
}

/** The next risk level, stage or action window the run reaches after the answer's day; else the last one reached;
 * null without either */
export function nextMilestone({ run, today }: { run: ModelRun; today: string }): string | null {
  const i = answerIndex(run, today)
  const day = run.table.days[i]?.date ?? today
  const dated = run.milestones.filter((m) => m.date !== null).toSorted((a, b) => a.date!.localeCompare(b.date!))
  const words = (m: (typeof dated)[number]) =>
    m.what === 'risk' ? `${m.name} risk` : m.what === 'stage' ? `stage ${m.name}` : m.name
  const next = dated.find((m) => m.date! > day)
  if (next) return `Next: ${words(next)} on ${formatDate(next.date)}${KIND_WORDS[next.day_kind ?? ''] ?? ''}.`
  const last = dated.findLast((m) => m.date! <= day && !m.before_start)
  if (last) return `Last reached: ${words(last)} on ${formatDate(last.date)}.`
  return null
}

/** The table's rows (indexes into the run's days): the 7 days through the answer's day, and the forecast after it */
export function recentRows(run: ModelRun, today: string): number[] {
  const days = run.table.days
  const i = answerIndex(run, today)
  if (i < 0) return []
  const rows: number[] = []
  for (let k = Math.max(0, i - 6); k < days.length; k++) {
    if (k <= i || isForecast(days[k])) rows.push(k)
  }
  return rows
}
