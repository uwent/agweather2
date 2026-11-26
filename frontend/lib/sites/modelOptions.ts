// A model's settings at a site (track 3 step 6): the date it counts from (`biofix`), the planting date (`early`,
// `mid`, `late` or a date) and the model's and its crop model's options, kept as one record of strings by parameter
// name: in the site's preferences once it's saved (`Prefs.options[model]`), else in the page's view (its Share link).
// `runParams` turns them, the season and the extended forecast into the `/models/{id}/run` query.

import type { SiteModelInfo } from '@/types'

export type Chosen = Record<string, string>

type Model = Pick<SiteModelInfo, 'id' | 'options' | 'biofix' | 'planting' | 'season'>

/** The parameter names a model takes from its settings */
export function settingNames(model: Model): string[] {
  return [
    ...(model.biofix ? ['biofix'] : []),
    ...(model.planting ? ['planting_date', ...model.planting.options.map((o) => o.name)] : []),
    ...model.options.map((o) => o.name),
  ]
}

/** Settings as view text, `biofix=2026-06-30;planting_date=mid` (empty values left out) */
export function encodeChosen(chosen: Chosen): string {
  return Object.entries(chosen)
    .filter(([, value]) => value !== '')
    .map(([name, value]) => `${name}=${encodeURIComponent(value)}`)
    .join(';')
}

export function decodeChosen(text: string): Chosen {
  const chosen: Chosen = {}
  for (const part of text.split(';')) {
    const at = part.indexOf('=')
    if (at <= 0) continue
    try {
      chosen[part.slice(0, at)] = decodeURIComponent(part.slice(at + 1))
    } catch {
      continue
    }
  }
  return chosen
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
export const PLANTING_TIERS = ['early', 'mid', 'late'] as const

/**
 * The run's query beyond the point and units: the settings the model takes (a date only in the season it's in: a
 * 2026 spray date says nothing of 2025, which then counts from the default, with a note saying so), the season's
 * last day for a past year (its own season's end, or December 31), and `projection=true` for the extended forecast
 * this year.
 */
export function runParams({
  model,
  chosen,
  year,
  thisYear,
  projection,
}: {
  model: Model
  chosen: Chosen
  year: number
  thisYear: number
  projection: boolean
}): { params: Record<string, string | boolean>; notes: string[] } {
  const params: Record<string, string | boolean> = {}
  const notes: string[] = []
  for (const name of settingNames(model)) {
    const value = chosen[name]
    if (!value) continue
    if (ISO_DATE.test(value) && Number(value.slice(0, 4)) !== year) {
      notes.push(
        `Your ${name === 'biofix' ? 'start date' : name === 'planting_date' ? 'planting date' : 'date'} is in ${value.slice(0, 4)}, so ${year} uses the default.`,
      )
      continue
    }
    if (name === 'planting_date' && !ISO_DATE.test(value) && !(PLANTING_TIERS as readonly string[]).includes(value))
      continue
    params[name] = value
  }
  if (year < thisYear) params.end = `${year}-${model.season?.[1] ?? '12-31'}`
  else if (projection) params.projection = true
  return { params, notes }
}
