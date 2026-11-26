// /data's maps as data files (track 7 step 7.1): the `/grids/{layer}` request for a choice, and how large it is,
// counted as the API counts it (`app/api/routes/grids.py`: `_area`, `_grid_spec`, `_check_size`) so the page says
// before the download whether the API takes it.
//
// - Steps: one with a statistic, else each day (or hour) of the range.
// - Cells on the native grid: the rectangle around the area's cells over the archive's window (a state's or a
//   county's from the page's props, a box's found here by projecting its cells' centers as `agdata.grid.NDFD` does),
//   every `stride`-th row and column; JSON and CSV keep only the area's cells with `clip`.
// - On a latitude and longitude grid: the multiples of `res` within the cells' latitudes and longitudes. With `clip`
//   the API takes the area's own cells' extent, a little smaller than its rectangle's, so this counts a few more.
// - Limits: JSON and CSV up to `text_values` values, NetCDF and GeoTIFF up to `file_values` (the whole rectangle,
//   since a file is a full grid); a map's range up to `map_days` days or `map_hours` hours.

import type { DataAreas, DataLimits, GridArea, GridProjection } from '@/types'

import { apiUrl } from '../api'
import { addDays, daysBetween } from '../dates'
import { formatBytes } from '../sites/dataRequest'
import { formatNumber } from '../units'

/** Grid indices, half-open: rows `j0` to `j1` - 1, columns `i0` to `i1` - 1 */
export type Window = { j0: number; j1: number; i0: number; i1: number }
export type Box = { south: number; west: number; north: number; east: number }

const RAD = Math.PI / 180

/** NDFD's Lambert conformal projection on its sphere (one standard parallel): a cell's center and back */
export function lambert(p: GridProjection) {
  const phi1 = p.lat1 * RAD
  const n = Math.sin(phi1)
  const f = (Math.cos(phi1) * Math.tan(Math.PI / 4 + phi1 / 2) ** n) / n
  const rho0 = (p.radius * f) / Math.tan(Math.PI / 4 + phi1 / 2) ** n
  return {
    /** A cell's center (grid indices, fractional too) as latitude and longitude */
    latLng(j: number, i: number): { lat: number; lng: number } {
      const x = p.x0 + i * p.dx
      const y = p.y0 + j * p.dx
      const rho = Math.sign(n) * Math.hypot(x, rho0 - y)
      const lat = (2 * Math.atan(((p.radius * f) / rho) ** (1 / n)) - Math.PI / 2) / RAD
      const lng = p.lon0 + Math.atan2(x, rho0 - y) / n / RAD
      return { lat, lng }
    },
    /** A latitude and longitude as fractional grid indices (cell centers on whole numbers) */
    index(lat: number, lng: number): { j: number; i: number } {
      const rho = (p.radius * f) / Math.tan(Math.PI / 4 + (lat * RAD) / 2) ** n
      const theta = n * (lng - p.lon0) * RAD
      const x = rho * Math.sin(theta)
      const y = rho0 - rho * Math.cos(theta)
      return { j: (y - p.y0) / p.dx, i: (x - p.x0) / p.dx }
    },
  }
}

/** The rectangle around the archive's cells whose centers are in a box, and how many there are, as `/grids`'
 * `bbox` finds them; null when none are */
export function boxArea(p: GridProjection, archive: Window, box: Box): { window: Window; cells: number } | null {
  const proj = lambert(p)
  // The box's edges are curves on the grid: sample them for the range of rows and columns to look in
  let [jLo, jHi, iLo, iHi] = [Infinity, -Infinity, Infinity, -Infinity]
  const steps = 64
  for (let k = 0; k <= steps; k++) {
    const t = k / steps
    for (const [lat, lng] of [
      [box.south, box.west + t * (box.east - box.west)],
      [box.north, box.west + t * (box.east - box.west)],
      [box.south + t * (box.north - box.south), box.west],
      [box.south + t * (box.north - box.south), box.east],
    ]) {
      const { j, i } = proj.index(lat, lng)
      jLo = Math.min(jLo, j)
      jHi = Math.max(jHi, j)
      iLo = Math.min(iLo, i)
      iHi = Math.max(iHi, i)
    }
  }
  const j0 = Math.max(archive.j0, Math.floor(jLo) - 2)
  const j1 = Math.min(archive.j1, Math.ceil(jHi) + 3)
  const i0 = Math.max(archive.i0, Math.floor(iLo) - 2)
  const i1 = Math.min(archive.i1, Math.ceil(iHi) + 3)
  let cells = 0
  const found = { j0: Infinity, j1: -Infinity, i0: Infinity, i1: -Infinity }
  for (let j = j0; j < j1; j++) {
    for (let i = i0; i < i1; i++) {
      const { lat, lng } = proj.latLng(j, i)
      if (lat >= box.south && lat <= box.north && lng >= box.west && lng <= box.east) {
        cells++
        found.j0 = Math.min(found.j0, j)
        found.j1 = Math.max(found.j1, j + 1)
        found.i0 = Math.min(found.i0, i)
        found.i1 = Math.max(found.i1, i + 1)
      }
    }
  }
  return cells ? { window: found, cells } : null
}

/** The latitudes and longitudes a window's cells span (their centers): the extremes lie on its edges */
export function windowExtent(p: GridProjection, w: Window): Box {
  const proj = lambert(p)
  const extent = { south: Infinity, west: Infinity, north: -Infinity, east: -Infinity }
  const visit = (j: number, i: number) => {
    const { lat, lng } = proj.latLng(j, i)
    extent.south = Math.min(extent.south, lat)
    extent.north = Math.max(extent.north, lat)
    extent.west = Math.min(extent.west, lng)
    extent.east = Math.max(extent.east, lng)
  }
  for (let i = w.i0; i < w.i1; i++) {
    visit(w.j0, i)
    visit(w.j1 - 1, i)
  }
  for (let j = w.j0; j < w.j1; j++) {
    visit(j, w.i0)
    visit(j, w.i1 - 1)
  }
  return extent
}

/** The multiples of `res` from `low` to `high`, as `agdata.regrid.latlon_index` takes them */
export function multiples(low: number, high: number, res: number): number {
  return Math.max(0, Math.floor(high / res + 1e-9) - Math.ceil(low / res - 1e-9) + 1)
}

export type AreaChoice =
  | { kind: 'whole' }
  | { kind: 'state'; id: string }
  | { kind: 'county'; id: string }
  | { kind: 'box'; box: Box | null }

export type GridFormat = 'netcdf' | 'geotiff' | 'csv' | 'json'

/** The layer as `/layers` gives it, as much as a file needs */
export type GridLayer = { id: string; time_axis: string; stats: string[] }

export type GridChoice = {
  layer: GridLayer
  /** One day, or a range */
  span: 'day' | 'range'
  /** YYYY-MM-DD: the day, or the range's first */
  start: string
  /** YYYY-MM-DD: the range's last */
  end: string
  /** Combine the range's days (or hours) into one map: a statistic from the layer's `stats`, or null for each step */
  stat: string | null
  area: AreaChoice
  /** JSON and CSV: only the area's cells, not its rectangle */
  clip: boolean
  format: GridFormat
  grid: 'native' | 'latlon'
  res: number
  stride: number
  units: 'us' | 'metric'
}

export type GridContext = {
  limits: DataLimits
  projection: GridProjection
  /** The states and counties, with the archive's window (null until they've loaded) */
  areas: DataAreas | null
}

export type GridEstimate = {
  steps: number
  /** Values in the answer (JSON and CSV: rows) */
  values: number
  bytes: number
  /** What the API would refuse, in its terms; null when it takes the request */
  problem: string | null
}

// Bytes a value takes, measured on the API's answers over Wisconsin: a CSV row (date, kind, lat, lng, value)
// ~33 bytes, JSON's ~36; NetCDF and GeoTIFF compressed, under a byte for temperatures and precipitation
const BYTES_PER_VALUE: Record<GridFormat, number> = { csv: 33, json: 36, netcdf: 1, geotiff: 1 }

/** The steps a choice has: one with a statistic or a single day's daily layer, else each day or hour */
export function gridSteps(choice: GridChoice): number | null {
  const last = choice.span === 'day' ? choice.start : choice.end
  if (!choice.start || !last || last < choice.start) return null
  const days = daysBetween(choice.start, last) + 1
  if (choice.layer.time_axis === 'none') return 1
  if (choice.stat) return 1
  return choice.layer.time_axis === 'hour' ? days * 24 : days
}

/** The area's rectangle and cells, or null while it's unknown (the areas loading, a box not yet given) */
export function areaCells(choice: GridChoice, ctx: GridContext): { window: Window; cells: number } | null {
  if (!ctx.areas) return null
  const [j0, j1, i0, i1] = ctx.areas.window
  const archive = { j0, j1, i0, i1 }
  const { area } = choice
  if (area.kind === 'whole') return { window: archive, cells: (j1 - j0) * (i1 - i0) }
  if (area.kind === 'box') return area.box ? boxArea(ctx.projection, archive, area.box) : null
  const list: GridArea[] = area.kind === 'state' ? ctx.areas.states : ctx.areas.counties
  const found = list.find((a) => a.id === area.id)
  return found ? { window: { j0: found.j0, j1: found.j1, i0: found.i0, i1: found.i1 }, cells: found.cells } : null
}

/** How large a choice's answer is and whether the API takes it; null while its dates or area are incomplete */
export function gridEstimate(choice: GridChoice, ctx: GridContext): GridEstimate | null {
  const steps = gridSteps(choice)
  const area = areaCells(choice, ctx)
  if (steps === null) return null
  if (area === null) {
    if (choice.area.kind !== 'box' || !choice.area.box || !ctx.areas) return null
    const problem = 'The box has no grid cells in the area we cover. Choose a box that overlaps it.'
    return { steps, values: 0, bytes: 0, problem }
  }
  const { window: w } = area
  const rows = w.j1 - w.j0
  const cols = w.i1 - w.i0
  let full: number
  let cells: number
  if (choice.grid === 'latlon') {
    const e = windowExtent(ctx.projection, w)
    full = multiples(e.south, e.north, choice.res) * multiples(e.west, e.east, choice.res)
    cells = full
  } else {
    full = Math.ceil(rows / choice.stride) * Math.ceil(cols / choice.stride)
    cells = choice.clip ? Math.round(area.cells / choice.stride ** 2) : full
  }
  const text = choice.format === 'csv' || choice.format === 'json'
  const values = steps * (text ? cells : full)
  const bytes = values * BYTES_PER_VALUE[choice.format] + (text ? 4000 : 20_000)
  return { steps, values, bytes, problem: gridProblem(choice, ctx.limits, steps, cells, full) }
}

/** The API's refusal of a choice, in its words (`_check_size`, `layermaps.span`); null when it takes it */
export function gridProblem(
  choice: GridChoice,
  limits: DataLimits,
  steps: number,
  cells: number,
  full: number,
): string | null {
  const days = daysBetween(choice.start, choice.span === 'day' ? choice.start : choice.end) + 1
  if (choice.layer.time_axis === 'hour' && days * 24 > limits.map_hours)
    return `The range is ${formatNumber(days * 24)} hours long; a map covers up to ${formatNumber(limits.map_hours)}, about a month. Choose a shorter range.`
  if (choice.layer.time_axis !== 'hour' && days > limits.map_days)
    return `The range is ${formatNumber(days)} days long; a map covers up to ${formatNumber(limits.map_days)}, about a year. Choose a shorter range.`
  if (choice.format === 'csv' || choice.format === 'json') {
    if (steps * cells > limits.text_values)
      return `This request has about ${formatNumber(steps * cells)} values (${formatNumber(steps)} ${steps === 1 ? 'map' : 'maps'} × ${formatNumber(cells)} cells); JSON and CSV hold up to ${formatNumber(limits.text_values)}. Choose NetCDF or GeoTIFF, combine the days into one map, or choose a smaller area or a coarser grid.`
  } else if (steps * full > limits.file_values) {
    return `This request has about ${formatNumber(steps * full)} values (${formatNumber(steps)} ${steps === 1 ? 'map' : 'maps'} × ${formatNumber(full)} cells); a file holds up to ${formatNumber(limits.file_values)}. Choose a smaller area, a coarser grid or a shorter range, or combine the days into one map.`
  }
  return null
}

/** The `/grids/{layer}` request for a choice. Hours: the grid days' hours (midnight to midnight CST is 06:00 to 06:00
 * UTC, each hour labeled by its end). */
export function gridRequest(choice: GridChoice): { path: string; params: Record<string, string | number | null> } {
  const { layer } = choice
  const params: Record<string, string | number | null> = {}
  const last = choice.span === 'day' ? choice.start : choice.end
  if (layer.time_axis === 'hour') {
    params.start = `${choice.start}T07:00Z`
    params.end = `${addDays(last, 1)}T06:00Z`
  } else if (layer.time_axis !== 'none') {
    if (choice.span === 'day') params.date = choice.start
    else Object.assign(params, { start: choice.start, end: last })
  }
  if (choice.stat && (choice.span === 'range' || layer.time_axis === 'hour')) params.stat = choice.stat
  const { area } = choice
  if (area.kind === 'state' || area.kind === 'county') params.region = area.id
  if (area.kind === 'box' && area.box) {
    const { south, west, north, east } = area.box
    params.bbox = [south, west, north, east].join(',')
  }
  if (area.kind !== 'whole' && choice.clip) params.clip = 'true'
  if (choice.grid === 'latlon') {
    params.grid = 'latlon'
    params.res = choice.res
  } else if (choice.stride > 1) params.stride = choice.stride
  params.units = choice.units
  params.format = choice.format
  return { path: `/grids/${encodeURIComponent(layer.id)}`, params }
}

/** The request's URL from the site's root */
export function gridUrl(choice: GridChoice): string {
  const { path, params } = gridRequest(choice)
  return apiUrl(path, params)
}

/** The estimate as a reader reads it: "About 21,100,000 values, about 21 MB." */
export function describeEstimate(estimate: GridEstimate, format: GridFormat): string {
  const unit = format === 'csv' || format === 'json' ? 'rows' : 'values'
  return `${formatNumber(estimate.values)} ${unit}, ${formatBytes(estimate.bytes)}.`
}

/** A box typed as south, west, north and east in degrees; null while it isn't four numbers in order */
export function parseBox(text: { south: string; west: string; north: string; east: string }): Box | null {
  const [south, west, north, east] = [text.south, text.west, text.north, text.east].map((v) =>
    v.trim() === '' ? NaN : Number(v),
  )
  if (![south, west, north, east].every(Number.isFinite)) return null
  if (south >= north || west >= east || south < -90 || north > 90 || west < -180 || east > 180) return null
  return { south, west, north, east }
}
