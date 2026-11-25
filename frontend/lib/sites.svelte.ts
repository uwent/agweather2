// STUB: replaced by the sites store agent's file at merge (an in-memory list with the three calls the site page uses)

import { siteKey } from './siteKey'

export type Site = { key: string; lat: number; lng: number; name: string }

const state = $state<{ sites: Site[] }>({ sites: [] })

/** The saved site at a key, if any */
export function siteAt(key: string): Site | undefined {
  return state.sites.find((site) => site.key === key)
}

export function isSaved(key: string): boolean {
  return siteAt(key) !== undefined
}

/** Saves a site; refused, with the reason for the reader, when its key is taken */
export function addSite(site: {
  lat: number
  lng: number
  name: string
}): { ok: true; site: Site } | { ok: false; error: string } {
  const key = siteKey(site.lat, site.lng)
  const existing = siteAt(key)
  if (existing) return { ok: false, error: `You already saved this location as ${existing.name}.` }
  const saved = { key, ...site }
  state.sites.push(saved)
  return { ok: true, site: saved }
}
