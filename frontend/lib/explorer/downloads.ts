// The map explorer's downloads (frontend.md's "GeoTIFF or NetCDF of the view; TileJSON for GIS"): the API's grid files
// of the map on screen, with the tiles' own settings (`tileRequest`), over the area in view, and the TileJSON of its
// colored tiles. The time goes to `/grids` as the tiles' `{time}` goes to it on the server (api/routes/tiles.py's
// `_layer_query`): a day as `date`, an hour as `time`, a range as `start` and `end`, `latest` as nothing.

import { API_BASE, queryString, type QueryScalar } from '@/lib/api'
import { COVERAGE_BOUNDS } from '@/lib/map/coverage'

import type { TileRequest } from './view'

/** West, south, east, north */
export type Bounds = [number, number, number, number]

/** The settings of `/grids` for the map the tiles show */
export function gridParams(tiles: TileRequest): Record<string, QueryScalar | null> {
  const params: Record<string, QueryScalar | null> = { ...tiles.params, stat: tiles.stat }
  const range = /^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$/.exec(tiles.time)
  if (tiles.time === 'latest') return params
  if (range) return { ...params, start: range[1], end: range[2] }
  if (/^\d{4}-\d{2}$/.test(tiles.time)) return { ...params, season: tiles.time }
  if (tiles.time.includes('T')) return { ...params, time: tiles.time }
  return { ...params, date: tiles.time }
}

/** The view's area as `/grids`' `bbox` (south,west,north,east), within the coverage and rounded outward to 0.01°; null
 * when the view is off the coverage or holds all of it (the whole coverage is then the area) */
export function viewBbox(view: Bounds | null): string | null {
  if (!view) return null
  const [w0, s0, e0, n0] = COVERAGE_BOUNDS
  const [w, s, e, n] = [Math.max(view[0], w0), Math.max(view[1], s0), Math.min(view[2], e0), Math.min(view[3], n0)]
  if (!(w < e && s < n)) return null
  if (w === w0 && s === s0 && e === e0 && n === n0) return null
  const down = (v: number) => Math.floor(v * 100) / 100
  const up = (v: number) => Math.ceil(v * 100) / 100
  return [down(s), down(w), up(n), up(e)].join(',')
}

export type DownloadLinks = {
  geotiff: string
  netcdf: string
  /** The TileJSON of the colored tiles */
  tilejson: string
  /** Whether the files cover the view (else the whole coverage) */
  inView: boolean
  /** The units the files' values are in */
  system: 'us' | 'metric'
}

/**
 * The links for the map on screen. Values come in the reader's units, but degree days in US units, as their setting
 * (`dd=modified_50_86`) is written in °F. The TileJSON takes the reader's colors: its palette and, when the units
 * agree, its range.
 */
export function downloadLinks(
  tiles: TileRequest,
  options: { bounds: Bounds | null; system: 'us' | 'metric'; palette: string | null; scale: string | null },
): DownloadLinks {
  const system = 'dd' in tiles.params && tiles.params.dd ? 'us' : options.system
  const bbox = viewBbox(options.bounds)
  const grid = { ...gridParams(tiles), units: system, bbox }
  const path = `${API_BASE}/grids/${encodeURIComponent(tiles.layer)}`
  const file = (format: string) => `${path}?${queryString({ ...grid, format })}`
  const scale = system === options.system ? options.scale : options.scale === 'default' ? 'default' : null
  const tilejson = `${API_BASE}/tiles/${encodeURIComponent(tiles.layer)}.json?${queryString({
    ...tiles.params,
    units: system,
    stat: tiles.stat,
    time: tiles.time,
    style: 'default',
    palette: options.palette,
    scale,
  })}`
  return { geotiff: file('geotiff'), netcdf: file('netcdf'), tilejson, inView: bbox !== null, system }
}
