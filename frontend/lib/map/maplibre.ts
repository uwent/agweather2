// WISP 3: app/frontend/lib/map/maplibre.ts (copied)
// MapLibre, loaded on demand (it's large and only the map pages use it). MapLibre computes its
// worker's URL at run time, which Vite can't follow, so Vite bundles the worker itself and MapLibre
// is told where it is.

import type { Map as MapLibreMap } from 'maplibre-gl'

type MapLibre = typeof import('maplibre-gl')

let loading: Promise<MapLibre> | undefined

export function loadMapLibre(): Promise<MapLibre> {
  loading ??= Promise.all([import('maplibre-gl'), import('maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url')])
    .then(([maplibre, worker]) => {
      maplibre.setWorkerUrl(worker.default)
      return maplibre
    })
    .catch((error) => {
      loading = undefined
      throw error
    })
  return loading
}

/** Shows or hides a map's layers (those it has) */
export function showLayers(map: MapLibreMap | undefined, ids: string[], visible: boolean) {
  for (const id of ids) if (map?.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
}
