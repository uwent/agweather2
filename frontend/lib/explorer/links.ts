// Links out of the map explorer to the pages beside it: a site, a model's page and a model at a site. The one place
// that builds them, so the map's links follow those pages' addresses.

import { routes } from '@/lib/routes'
import { roundCoord } from '@/lib/siteKey'

/** A site's page for a point (`/sites/43.07,-89.4`), with the place's name where there is one */
export function sitePath(lat: number, lng: number, name?: string | null): string {
  const path = routes.site({ lat: String(roundCoord(lat)), lng: String(roundCoord(lng)) })
  return name ? `${path}?${new URLSearchParams({ name })}` : path
}

// TODO(wave 4 merge): these become `routes.model({ id })` and `routes.siteModel({ lat, lng, id })` once those
// pages' URL names (`model`, `site-model`) are in routes.ts

/** A model's page (`/models/late-blight-dsv`) */
export const modelPath = (id: string): string => `/models/${encodeURIComponent(id)}`

/** A model at a site (`/sites/43.07,-89.4/models/late-blight-dsv`), with the place's name where there is one */
export function siteModelPath(lat: number, lng: number, id: string, name?: string | null): string {
  const path = `/sites/${roundCoord(lat)},${roundCoord(lng)}/models/${encodeURIComponent(id)}`
  return name ? `${path}?${new URLSearchParams({ name })}` : path
}
