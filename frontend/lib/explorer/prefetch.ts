// The next day's tiles, fetched quietly once the map's are in (Phase 7 track 2 step 3), so a step forward is
// quick: the API computes the next day's map on the first tile, and the browser keeps the tiles (their
// Cache-Control) for MapLibre's own requests to the same addresses. Only the next day: a model's map can take
// seconds to compute, and the API keeps a few dozen maps.

import { API_BASE, queryString } from '@/lib/api'
import { MAX_ZOOM, MIN_ZOOM } from '@/lib/map/dataTiles'
import { tileAt } from '@/lib/map/radar'

import type { TileRequest } from './view'

/** At most this many tiles a prefetch */
export const MAX_TILES = 40

/** The tiles a map shows of [west, south, east, north] at a zoom (MapLibre's tile zoom: the whole zoom below,
 * held to the API's zooms), at most `limit` */
export function visibleTiles(
  bounds: [number, number, number, number],
  zoom: number,
  limit = MAX_TILES,
): { z: number; x: number; y: number }[] {
  const z = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.floor(zoom)))
  const [west, south, east, north] = bounds
  const clampLat = (lat: number) => Math.max(-85, Math.min(85, lat))
  const nw = tileAt([west, clampLat(north)], z)
  const se = tileAt([east, clampLat(south)], z)
  const tiles: { z: number; x: number; y: number }[] = []
  for (let y = nw.y; y <= se.y; y++) {
    for (let x = nw.x; x <= se.x; x++) {
      if (tiles.length >= limit) return tiles
      tiles.push({ z, x: ((x % 2 ** z) + 2 ** z) % 2 ** z, y })
    }
  }
  return tiles
}

/** A tile's address as DataMap asks for it (the same URL, so the browser's cache serves MapLibre) */
export function tileUrl(request: TileRequest, tile: { z: number; x: number; y: number }, origin = location.origin) {
  const query = queryString({ stat: request.stat, ...request.params })
  const path = `${API_BASE}/tiles/${encodeURIComponent(request.layer)}/${encodeURIComponent(request.time)}`
  return `${origin}${path}/${tile.z}/${tile.x}/${tile.y}.png${query ? `?${query}` : ''}`
}

/** Fetches the tiles at low priority; a newer prefetch aborts this one */
export function prefetchTiles(
  request: TileRequest,
  bounds: [number, number, number, number],
  zoom: number,
  signal: AbortSignal,
): void {
  for (const tile of visibleTiles(bounds, zoom)) {
    fetch(tileUrl(request, tile), { signal, priority: 'low' } as RequestInit).catch(() => {})
  }
}
