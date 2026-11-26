// The API's data tiles (docs/api.md, "Tiles"; agdata.tiles): each pixel's color packs a value of the layer, which
// MapLibre colors on the GPU as a `raster-dem` source drawn by a `color-relief` layer (D119), and which the page
// reads back under the pointer. Pure helpers, tested in dataTiles.test.ts; DataMap.svelte puts them on the map.
//
// A pixel holds a 24-bit count of the layer's steps with zero at the middle: value = (R·65536 + G·256 + B) × step
// − 2²³ × step, in the layer's stored unit. Code 0 (alpha 0) is missing; code 1 is "none" (a first or last day
// with no such day, D78); real values are code 2 and up.

import type { ExpressionSpecification } from 'maplibre-gl'

import type { PaletteInfo } from '@/types/api'

import { tileAt, tilePixels } from './tiles'

export const ZERO = 2 ** 23
export const NONE_CODE = 1
/** The zoom the API's tiles stop at: past it MapLibre enlarges zoom 8's tiles */
export const MAX_ZOOM = 8
export const MIN_ZOOM = 3
/** How the static maps and colored tiles draw "none" (agdata.mapimage.NONE_COLOR) */
export const NONE_COLOR = '#dedede'
const TRANSPARENT = 'rgba(0, 0, 0, 0)'

/** A TileJSON's `encoding` (`/tiles/{layer}.json`) */
export type TileEncoding = {
  scheme: 'rgb24'
  unit: string
  step: number
  missing: string
  none?: string
  dates?: string
  redFactor: number
  greenFactor: number
  blueFactor: number
  baseShift: number
}

/** `/tiles/{layer}.json` with `style=default`: the colors' palette and domain come with it */
export type TileJson = {
  tilejson: string
  name: string
  description: string
  attribution: string
  tiles: string[]
  minzoom: number
  maxzoom: number
  bounds: [number, number, number, number]
  request: Record<string, unknown> & { model?: { id: string; version: string }; output?: string }
  palette?: string
  domain?: [number, number]
  domain_unit?: string
  domain_middle?: number
  encoding: TileEncoding
  /** What the map shows beyond its name (the date or range and settings); optional until the API sends it */
  subtitle?: string | null
  /** Notes on how the map was made (its data sources), a line each */
  caption?: string[] | string | null
  /** The API's warnings about the map, in its words */
  warnings?: string[]
  /** A map of levels' names by value (risk levels, susceptibility, a crop's stages with their codes); null for any
   * other map */
  categories?: TileCategory[] | null
}

/** One level of a categorical map, or one stage of a crop's (value −1: before the first stage) */
export type TileCategory = { value: number; code: string | null; name: string }

/** The name for a value of a map with categories: a stage's code and name ("V10, 10 leaf collars"), a risk
 * level's name ("High"); undefined for a value with none */
export function categoryName(categories: TileCategory[], value: number): string | undefined {
  const found = categories.find((c) => c.value === Math.round(value))
  if (!found) return undefined
  const isStage = categories.some((c) => c.value < 0)
  return isStage && found.code ? `${found.code}, ${found.name}` : found.name
}

/** A tick's label on a stage map's color bar: the stage's code ("V10") */
export function categoryCode(categories: TileCategory[], value: number): string {
  const found = categories.find((c) => c.value === Math.round(value))
  return found?.code ?? found?.name ?? ''
}

/** What a pixel holds: a value in the stored unit, 'none' (code 1) or null (missing) */
export type PixelValue = number | 'none' | null

/** The value of a code: code × step − 2²³ × step, computed as (code − 2²³) × step so it keeps its digits */
export const codeValue = (code: number, step: number) => (code - ZERO) * step

/** A pixel's value from its bytes */
export function decodePixel(r: number, g: number, b: number, alpha: number, step: number): PixelValue {
  if (alpha === 0) return null
  const code = r * 65536 + g * 256 + b
  if (code === 0) return null
  if (code === NONE_CODE) return 'none'
  // Rounded to the step's digits: 0.1 × 3 is 0.30000000000000004
  return roundToStep(codeValue(code, step), step)
}

/** A value rounded to a whole number of steps, with no more decimals than the step has */
export function roundToStep(value: number, step: number): number {
  const digits = Math.max(0, Math.ceil(-Math.log10(step) - 1e-9))
  return Number((Math.round(value / step) * step).toFixed(digits))
}

/**
 * MapLibre's `raster-dem` custom encoding for a layer's step. MapLibre decodes R × red + G × green + B × blue −
 * baseShift (DEMData.unpack, the color-relief shader), subtracting baseShift although its style spec says "added".
 * The API's TileJSON gives the same factors (since 2026-11-26); they're made here from the step so the page needs
 * nothing else from it.
 */
export function maplibreEncoding(step: number) {
  return {
    encoding: 'custom' as const,
    redFactor: 65536 * step,
    greenFactor: 256 * step,
    blueFactor: step,
    baseShift: ZERO * step,
  }
}

/** A palette by id from `/palettes`, an id ending `_r` reversed; undefined if unknown */
export function findPalette(id: string, palettes: readonly PaletteInfo[]): PaletteInfo | undefined {
  const reversed = id.endsWith('_r')
  const found = palettes.find((palette) => palette.id === (reversed ? id.slice(0, -2) : id))
  if (!found || !reversed) return found
  return { ...found, id, colors: [...found.colors].reverse() }
}

/**
 * The `color-relief-color` expression: the palette over `domain` (stored units), as the API's static maps color it
 * (agdata.palettes.colorize): a continuous palette's colors evenly spaced from low to high and clipped at the ends,
 * a categorical palette's color per level (0, 1, …). Missing (code 0) is transparent and "none" (code 1) light gray.
 *
 * MapLibre packs each stop into the tiles' encoding, so stops are rounded to whole steps here and any that would
 * meet the one before are dropped (two stops at one value make the shader divide by zero).
 */
export function colorExpression(
  palette: Pick<PaletteInfo, 'kind' | 'colors'>,
  domain: readonly [number, number],
  step: number,
): ExpressionSpecification {
  const stops: [number, string][] = [
    [codeValue(0, step), TRANSPARENT],
    [codeValue(NONE_CODE, step), NONE_COLOR],
  ]
  const colors = palette.colors
  if (palette.kind === 'categorical') {
    colors.forEach((color, level) => stops.push([level, color]))
  } else {
    const [low, high] = domain[1] > domain[0] ? domain : [domain[0], domain[0] + step]
    // The low color from the lowest real value (code 2) up to the domain's low end
    stops.push([codeValue(2, step), colors[0]])
    const last = colors.length - 1
    // The ends always; a middle color only where it falls a whole step from its neighbors
    const top = Math.round(high / step)
    colors.forEach((color, i) => {
      const value = low + ((high - low) * i) / last
      if (i === 0 || i === last || Math.round(value / step) < top) stops.push([value, color])
    })
  }
  const kept: [number, string][] = []
  for (const [value, color] of stops) {
    const at = Math.round(value / step)
    if (kept.length && at <= Math.round(kept[kept.length - 1][0] / step)) continue
    kept.push([roundToStep(value, step), color])
  }
  return ['interpolate', ['linear'], ['elevation'], ...kept.flat()] as unknown as ExpressionSpecification
}

/** A date layer's value (days since 1970-01-01) as a date: "Sep 22, 2026", or "Sep 22" without the year */
export function formatDays(days: number, withYear = true): string {
  return new Date(Math.round(days) * 86_400_000).toLocaleDateString('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}

/** A CSS gradient of a continuous palette, low to high, left to right, for the legend */
export const cssGradient = (colors: readonly string[]) => `linear-gradient(to right, ${colors.join(', ')})`

/**
 * Round ticks between low and high (display units) for a legend: about `count` of them at 1, 2, 2.5 or 5 × a power
 * of ten, and their place along the bar (0–1)
 */
export function legendTicks(low: number, high: number, count = 5): { value: number; at: number }[] {
  if (!(high > low)) return [{ value: low, at: 0 }]
  const raw = (high - low) / count
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= raw * 0.999) ?? 10 * power
  const ticks: { value: number; at: number }[] = []
  for (let v = Math.ceil(low / step - 1e-9) * step; v <= high + step * 1e-9; v += step) {
    const value = Number(v.toPrecision(12))
    ticks.push({ value, at: (value - low) / (high - low) })
  }
  return ticks
}

/**
 * Legend ticks with their labels, as many as fit along a bar of about `chars` characters (each label and a gap of
 * two), from five down to two
 */
export function fittedTicks(
  low: number,
  high: number,
  format: (value: number, digits: number) => string,
  chars = 30,
): { value: number; at: number; label: string }[] {
  let labelled: { value: number; at: number; label: string }[] = []
  for (const count of [5, 4, 3, 2]) {
    const ticks = legendTicks(low, high, count)
    // As many decimals as the roundest ticks need (0.5 in, not 0.50 in)
    const digits = Math.max(0, ...ticks.map((tick) => String(tick.value).split('.')[1]?.length ?? 0))
    labelled = ticks.map((tick) => ({ ...tick, label: format(tick.value, digits) }))
    if (labelled.reduce((sum, tick) => sum + tick.label.length + 2, 0) <= chars) break
  }
  return labelled
}

/** The z8 tile and its pixel under a point: the API's finest tiles, where a pixel (~0.4 km) is finer than a cell */
export const valueTileAt = (lng: number, lat: number) => tileAt([lng, lat], MAX_ZOOM)

/** A tile's URL from its template (`{z}/{x}/{y}`) */
export const tileUrl = (template: string, z: number, x: number, y: number) =>
  template.replace('{z}', String(z)).replace('{x}', String(x)).replace('{y}', String(y))

/** A small map that forgets the least recently used entry past `size` */
export class Lru<K, V> {
  #entries = new Map<K, V>()
  constructor(readonly size: number) {}

  get(key: K): V | undefined {
    const value = this.#entries.get(key)
    if (value !== undefined) {
      this.#entries.delete(key)
      this.#entries.set(key, value)
    }
    return value
  }

  set(key: K, value: V) {
    this.#entries.delete(key)
    this.#entries.set(key, value)
    if (this.#entries.size > this.size) this.#entries.delete(this.#entries.keys().next().value as K)
  }

  delete(key: K) {
    this.#entries.delete(key)
  }

  has(key: K) {
    return this.#entries.has(key)
  }

  get count() {
    return this.#entries.size
  }
}

/** The value at a pixel of a decoded tile */
export function valueAt(pixels: Pick<ImageData, 'data' | 'width'>, px: number, py: number, step: number): PixelValue {
  const i = (py * pixels.width + px) * 4
  const d = pixels.data
  return decodePixel(d[i], d[i + 1], d[i + 2], d[i + 3], step)
}

/**
 * The values under the pointer: each z8 tile's pixels fetched once (the browser's cache usually has it) and kept,
 * the last `size` of them. `at` answers at once from what's kept (undefined while a tile loads, then `onload`).
 */
export class TileValues {
  #tiles: Lru<string, ImageData | Promise<ImageData | null> | null>

  constructor(
    private template: string,
    private step: number,
    private onload: () => void = () => {},
    size = 48,
  ) {
    this.#tiles = new Lru(size)
  }

  /** The value at a point, or undefined while its tile loads */
  at(lng: number, lat: number): PixelValue | undefined {
    const { z, x, y, px, py } = valueTileAt(lng, lat)
    if (x < 0 || y < 0 || x >= 2 ** z || y >= 2 ** z) return null
    const url = tileUrl(this.template, z, x, y)
    const held = this.#tiles.get(url)
    if (held === null) return null // the tile failed: no value rather than asking again on every move
    if (held instanceof Promise) return undefined
    if (held) return valueAt(held, px, py, this.step)
    this.#load(url)
    return undefined
  }

  /** The value at a point, waiting for its tile */
  async atLoaded(lng: number, lat: number): Promise<PixelValue> {
    const { z, x, y, px, py } = valueTileAt(lng, lat)
    const url = tileUrl(this.template, z, x, y)
    let held = this.#tiles.get(url)
    if (held === undefined) held = this.#load(url)
    const pixels = held instanceof Promise ? await held : held
    return pixels ? valueAt(pixels, px, py, this.step) : null
  }

  #load(url: string): Promise<ImageData | null> {
    const loading = tilePixels(url).then(
      (pixels) => {
        this.#tiles.set(url, pixels)
        this.onload()
        return pixels
      },
      () => {
        this.#tiles.set(url, null)
        return null
      },
    )
    this.#tiles.set(url, loading)
    return loading
  }
}
