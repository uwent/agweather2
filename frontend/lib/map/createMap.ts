// WISP 3: app/frontend/lib/map/createMap.ts (adapted: the default view is our coverage, not Wisconsin's Central Sands)
import type { LngLatBoundsLike, Map as MapLibreMap, MapOptions } from 'maplibre-gl'

import { GEOCODER_ATTRIBUTION } from '@/lib/geocode'

import { type Basemap, basemapStyle, transformStyle } from './basemaps'
import { COVERAGE_BOUNDS } from './coverage'
import { loadMapLibre } from './maplibre'

type MapLibre = Awaited<ReturnType<typeof loadMapLibre>>

/** Every map's first view: the whole coverage, fitted to the map's box */
export const DEFAULT_VIEW: Pick<MapOptions, 'bounds' | 'fitBoundsOptions'> = {
  bounds: COVERAGE_BOUNDS as LngLatBoundsLike,
  fitBoundsOptions: { padding: 8 },
}

/**
 * Every map's start: MapLibre loaded on demand, a map in container on the basemap (the street style
 * repaired, transformStyle) at DEFAULT_VIEW, zoom buttons at the top right, and the compact
 * attribution with the place search's credit. options add to or replace those (a view, gestures):
 * a center replaces the default view. onready gets the map as soon as it's made, before its style
 * loads, with MapLibre's classes. Returns the cleanup for onMount, which removes the map whether or
 * not it was made yet.
 */
export function createMap(
  container: HTMLElement,
  basemap: Basemap,
  onready: (map: MapLibreMap, maplibre: MapLibre) => void,
  options: Partial<MapOptions> = {},
): () => void {
  let map: MapLibreMap | undefined
  let removed = false
  loadMapLibre().then((maplibre) => {
    if (removed) return
    map = new maplibre.Map({
      container,
      style: basemapStyle(basemap),
      transformStyle,
      ...(options.center || options.bounds ? {} : DEFAULT_VIEW),
      attributionControl: { compact: true, customAttribution: GEOCODER_ATTRIBUTION },
      ...options,
    })
    map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right')
    onready(map, maplibre)
  })
  return () => {
    removed = true
    map?.remove()
  }
}
