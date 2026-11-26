// Links out of the map explorer to the pages beside it: a site, a model's page and a model at a site. The one place
// that builds them, so the map's links follow those pages' addresses.

import { routes } from '@/lib/routes'
import { roundCoord } from '@/lib/siteKey'

/** A site's page for a point (`/sites/43.07,-89.4`), with the place's name where there is one */
export function sitePath(lat: number, lng: number, name?: string | null): string {
  const path = routes.site({ lat: String(roundCoord(lat)), lng: String(roundCoord(lng)) })
  return name ? `${path}?${new URLSearchParams({ name })}` : path
}

/** A site's Climate tab (`/sites/43.07,-89.4?tab=climate`), with the map's period where it isn't the default 30 years */
export function siteClimatePath(lat: number, lng: number, name?: string | null, period?: string | null): string {
  const path = routes.site({ lat: String(roundCoord(lat)), lng: String(roundCoord(lng)) })
  const query = new URLSearchParams({ tab: 'climate' })
  if (period && period !== 'last30') query.set('cperiod', period)
  if (name) query.set('name', name)
  return `${path}?${query}`
}

/** A model's page (`/models/late-blight-dsv`) */
export const modelPath = (id: string): string => routes.model({ model_id: id })

/** A model at a site (`/sites/43.07,-89.4/models/late-blight-dsv`), with the place's name where there is one */
export function siteModelPath(lat: number, lng: number, id: string, name?: string | null): string {
  const path = routes.siteModel({ lat: String(roundCoord(lat)), lng: String(roundCoord(lng)), model_id: id })
  return name ? `${path}?${new URLSearchParams({ name })}` : path
}
