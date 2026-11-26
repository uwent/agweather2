// WISP 3: app/frontend/lib/map/prefs.ts (adapted: a page's key in place of WISP's operation, and only the settings every map has)
import type { LngLat } from '@/lib/geo'
import { readStored, writeStored } from '@/lib/storage'

import type { Basemap } from './basemaps'
import { OVERLAYS } from './overlays'

// A map's settings, remembered per page (a short key: 'map', 'site') in this browser: the view, the
// basemap and the overlay. Storage can be blocked or cleared, so every read and write is guarded and
// the page works without it. D120's preferences store takes these over once it exists.

export type MapPrefs = {
  view: { center: LngLat; zoom: number } | null
  basemap: Basemap
  /** The data overlay shown (one at a time: radar, rain or the Drought Monitor), or null */
  overlay: string | null
  /** Overlay opacity by id, where the user changed it */
  opacity: Record<string, number>
}

export const DEFAULT_PREFS: MapPrefs = { view: null, basemap: 'light', overlay: null, opacity: {} }

const BASEMAP_KEYS: Basemap[] = ['light', 'imagery', 'streets']
const key = (page: string) => `agweather-map:${page}`

// A fresh copy, so changing a loaded setting's map in place never changes the defaults
const defaults = (): MapPrefs => structuredClone(DEFAULT_PREFS)

export function loadPrefs(page: string): MapPrefs {
  const stored = readStored(key(page))
  if (!stored || typeof stored !== 'object') return defaults()
  const saved = stored as Partial<Record<keyof MapPrefs, unknown>>
  // Layers and basemaps saved earlier that the map no longer has are dropped
  const overlay = OVERLAYS.some(({ id }) => id === saved.overlay) ? (saved.overlay as string) : null
  const basemap = BASEMAP_KEYS.includes(saved.basemap as Basemap) ? (saved.basemap as Basemap) : DEFAULT_PREFS.basemap
  return { ...defaults(), ...saved, overlay, basemap } as MapPrefs
}

export function savePrefs(page: string, prefs: MapPrefs) {
  // Storage blocked (private mode): the settings last for this page only
  writeStored(key(page), prefs)
}
