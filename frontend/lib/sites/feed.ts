// One model across your saved sites (track 3 step 9; `/sites/models/{id}`): the model run over every saved site in
// one `/models/{id}/run?points=` (up to 50, no projection), from two weeks back through the forecast, as a row per
// site: a risk strip, today's answer in words, and the next milestone (`meta.summary.points[k]`). Sites whose saved
// settings for the model differ (a biofix, a planting date) go in separate requests, one per set of settings.

import type { SiteModelInfo } from '@/types'
import type { TableResponse } from '@/types/api'

import { modelRun, type ModelRun } from '../charts/modelCharts'
import { addDays } from '../dates'
import type { RiskDay } from '../riskSpan'
import { riskRank } from '../riskLevels'
import { siteLabel, type EffectivePrefs, type Site } from '../sitesDoc'
import type { Units } from '../units'
import { runParams, settingNames, type Chosen } from './modelOptions'
import { answer, answerIndex, nextMilestone, type Answer } from './modelText'

type Model = Pick<SiteModelInfo, 'id' | 'options' | 'biofix' | 'planting' | 'season'>

/** The days before today the feed shows */
export const FEED_DAYS_BACK = 14

/** A saved site's settings for the model: its own, its groups' or all sites' (as a model at the site uses them) */
export function siteChosen(prefs: EffectivePrefs, model: Model): Chosen {
  const names = settingNames(model)
  const own = { ...prefs.options[model.id] }
  if (model.planting && !own.planting_date && prefs.planting) own.planting_date = prefs.planting
  return Object.fromEntries(Object.entries(own).filter(([name]) => names.includes(name)))
}

export type FeedRequest = { params: Record<string, string | boolean>; sites: Site[] }

/** The requests: one per distinct set of settings, each over its sites in the reader's order */
export function feedRequests({
  sites,
  model,
  prefsOf,
  today,
}: {
  sites: readonly Site[]
  model: Model
  prefsOf: (key: string) => EffectivePrefs
  today: string
}): FeedRequest[] {
  const year = Number(today.slice(0, 4))
  const byParams = new Map<string, FeedRequest>()
  for (const site of sites) {
    const chosen = siteChosen(prefsOf(site.key), model)
    const { params } = runParams({ model, chosen, year, thisYear: year, projection: false })
    const full = { ...params, start: addDays(today, -FEED_DAYS_BACK) }
    const key = JSON.stringify(Object.entries(full).sort())
    const found: FeedRequest = byParams.get(key) ?? { params: full, sites: [] }
    found.sites.push(site)
    byParams.set(key, found)
  }
  return [...byParams.values()]
}

/** `points=` for sites: `lat,lng;lat,lng` */
export const pointsParam = (sites: readonly Site[]) => sites.map((s) => `${s.lat},${s.lng}`).join(';')

/** A several-point answer as one answer per point: its rows (by the `point` column), its location and what was
 * resolved there (`meta.summary.points[k]`: biofix, milestones) as the summary */
export function splitPoints(body: Pick<TableResponse, 'meta' | 'data'>, count: number) {
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, unknown[]>
  const points = (data.point ?? []) as number[]
  const meta = body.meta as TableResponse['meta'] & { locations?: unknown[] }
  const summary = (meta.summary ?? {}) as Record<string, unknown>
  const perPoint = (summary.points ?? []) as Record<string, unknown>[]
  return Array.from({ length: count }, (_, k) => {
    const rows = points.flatMap((p, i) => (p === k ? [i] : []))
    const columns = Object.fromEntries(
      Object.entries(data)
        .filter(([name]) => name !== 'point')
        .map(([name, values]) => [name, rows.map((i) => values[i])]),
    )
    const pointSummary = { ...summary, points: undefined, ...(perPoint[k] ?? {}) }
    const request = { ...((meta.request ?? {}) as Record<string, unknown>), biofix: perPoint[k]?.biofix ?? null }
    return {
      meta: { ...meta, summary: pointSummary, request, location: meta.locations?.[k] ?? null },
      data: columns,
    } as unknown as Pick<TableResponse, 'meta' | 'data'>
  })
}

export type FeedRow = {
  site: Site
  /** The site's place in the reader's order */
  order: number
  run: ModelRun
  answer: Answer
  next: string | null
  /** Today's risk level (the run's last day before a projection when it hasn't today), null out of season */
  level: number | null
  /** Each day's risk, for the strip */
  days: RiskDay[]
}

/** A row per site from the answers of `feedRequests` */
export function feedRows({
  requests,
  bodies,
  order,
  model,
  units,
  today,
}: {
  requests: FeedRequest[]
  bodies: Pick<TableResponse, 'meta' | 'data'>[]
  order: readonly Site[]
  model: Pick<SiteModelInfo, 'outputs' | 'risk_levels' | 'stages' | 'season'>
  units: Units
  today: string
}): FeedRow[] {
  const rows: FeedRow[] = []
  requests.forEach((request, r) => {
    const parts = splitPoints(bodies[r], request.sites.length)
    request.sites.forEach((site, k) => {
      const run = modelRun(parts[k])
      const at = answerIndex(run, today)
      rows.push({
        site,
        order: order.findIndex((s) => s.key === site.key),
        run,
        answer: answer({ model, run, units, today }),
        next: nextMilestone({ run, today }),
        level: at >= 0 && run.inSeason?.[at] !== false ? run.level[at] : null,
        days: run.table.days.map((day, i) => ({
          date: day.date,
          kind: day.kind,
          level: run.level[i],
          label: run.label[i],
          inSeason: run.inSeason?.[i] ?? null,
        })),
      })
    })
  })
  return rows.sort((a, b) => a.order - b.order)
}

/** The rows by today's risk, highest first (ties, and sites without a level, in the reader's order); or as they are */
export function sortRows(rows: FeedRow[], by: 'risk' | 'order', levels: number): FeedRow[] {
  if (by === 'order') return rows.toSorted((a, b) => a.order - b.order)
  const rank = (row: FeedRow) => riskRank(row.level, levels)
  return rows.toSorted((a, b) => rank(b) - rank(a) || a.order - b.order)
}

/** The answers' warnings, each once, with the API's "For points 0 and 2: …" naming the sites instead */
export function feedWarnings(requests: FeedRequest[], bodies: Pick<TableResponse, 'meta'>[]): string[] {
  const found: string[] = []
  requests.forEach((request, r) => {
    for (const warning of bodies[r]?.meta.warnings ?? []) {
      const match = /^For points? ([\d, and]+): (.)([\s\S]*)$/.exec(warning)
      let text = warning
      if (match) {
        const names = match[1].split(/, | and /).map((n) => request.sites[Number(n)])
        if (names.every((site) => site !== undefined)) {
          const labels = names.map((site) => siteLabel(site))
          const listed = labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(', ')} and ${labels.at(-1)}`
          text = `At ${listed}: ${match[2]}${match[3]}`
        }
      }
      if (!found.includes(text)) found.push(text)
    }
  })
  return found
}
