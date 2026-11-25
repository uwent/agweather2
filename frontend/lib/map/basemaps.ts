// WISP 3: app/frontend/lib/map/basemaps.ts (adapted: OpenFreeMap's light style, the default under data (D119), and our layers kept beneath the basemap's borders and labels)
import type { ExpressionSpecification, LayerSpecification, Map as MapLibreMap, StyleSpecification } from 'maplibre-gl'

import { ROAD_LAYER_PREFIX, roads } from './roads.svelte'

// The basemaps: OpenFreeMap's light style (Positron), quiet under our data and the default (D119);
// USGS National Map imagery (public domain) with OpenFreeMap's roads and place names over it (USGS
// retired USGSImageryTopo, its imagery with them, in November 2026); or OpenFreeMap's streets, for
// a map without data

export type Basemap = 'light' | 'imagery' | 'streets'

/** The toggle's choices on a data map (the streets style is for maps without data) */
export const BASEMAPS: { key: Basemap; name: string }[] = [
  { key: 'light', name: 'Map' },
  { key: 'imagery', name: 'Satellite' },
]

/** The font our labels use; both basemaps serve it */
export const LABEL_FONT = ['Noto Sans Regular']

/** Our labels' paint: white with a black halo, legible on either basemap */
export const labelPaint = (haloWidth = 1) => ({
  'text-color': '#ffffff',
  'text-halo-color': '#000000',
  'text-halo-width': haloWidth,
})

// Roads, place names and county lines over the imagery, from OpenFreeMap's tiles (the Map basemap's
// source), drawn light for a dark background: the main roads pale yellow, the rest white and fainter
// the smaller they are, names in white with a dark halo
const NAME: ExpressionSpecification = ['coalesce', ['get', 'name:en'], ['get', 'name_en'], ['get', 'name']]
const LINES: ExpressionSpecification = ['match', ['geometry-type'], ['LineString', 'MultiLineString'], true, false]
const roadClass = (...classes: string[]): ExpressionSpecification => ['match', ['get', 'class'], classes, true, false]
const OVER_IMAGERY = { 'text-color': '#fff', 'text-halo-color': 'rgba(0, 0, 0, 0.75)', 'text-halo-width': 1.5 }

/** The layers drawn over the imagery, their ids starting ROAD_LAYER_PREFIX (exported for the tests) */
export const IMAGERY_ROADS: LayerSpecification[] = [
  {
    id: 'imagery-county-lines',
    type: 'line',
    source: 'openmaptiles',
    'source-layer': 'boundary',
    minzoom: 7,
    filter: ['all', ['match', ['get', 'admin_level'], [4, 6], true, false], ['!=', ['get', 'maritime'], 1]],
    paint: {
      'line-color': 'rgba(255, 255, 255, 0.6)',
      'line-dasharray': [3, 2],
      'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.75, 12, 1.5],
    },
  },
  {
    id: 'imagery-roads-minor',
    type: 'line',
    source: 'openmaptiles',
    'source-layer': 'transportation',
    minzoom: 12,
    filter: ['all', LINES, roadClass('minor', 'service')],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': 'rgba(255, 255, 255, 0.5)',
      'line-width': ['interpolate', ['exponential', 1.5], ['zoom'], 12, 0.5, 16, 2.5, 20, 10],
    },
  },
  {
    id: 'imagery-roads-secondary',
    type: 'line',
    source: 'openmaptiles',
    'source-layer': 'transportation',
    minzoom: 8,
    filter: ['all', LINES, roadClass('secondary', 'tertiary')],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': 'rgba(255, 255, 255, 0.75)',
      'line-width': ['interpolate', ['exponential', 1.5], ['zoom'], 8, 0.5, 14, 2, 20, 14],
    },
  },
  {
    id: 'imagery-roads-major',
    type: 'line',
    source: 'openmaptiles',
    'source-layer': 'transportation',
    minzoom: 5,
    filter: ['all', LINES, roadClass('motorway', 'trunk', 'primary')],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': 'rgba(255, 236, 160, 0.9)',
      'line-width': ['interpolate', ['exponential', 1.5], ['zoom'], 5, 0.5, 10, 1.5, 14, 3, 20, 18],
    },
  },
  {
    // Route numbers (I 39, US 51, WI 73, County Road J's "J"): how rural roads are known
    id: 'imagery-road-numbers',
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'transportation_name',
    minzoom: 9,
    filter: ['all', ['has', 'ref'], roadClass('motorway', 'trunk', 'primary', 'secondary', 'tertiary')],
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 400,
      'text-field': ['get', 'ref'],
      'text-font': LABEL_FONT,
      'text-size': 11,
    },
    paint: OVER_IMAGERY,
  },
  {
    id: 'imagery-road-names',
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'transportation_name',
    minzoom: 13,
    filter: roadClass('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'minor'),
    layout: {
      'symbol-placement': 'line',
      'text-field': NAME,
      'text-font': LABEL_FONT,
      'text-size': ['interpolate', ['linear'], ['zoom'], 13, 11, 16, 13],
    },
    paint: OVER_IMAGERY,
  },
  {
    id: 'imagery-places',
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'place',
    minzoom: 6,
    filter: roadClass('city', 'town', 'village'),
    layout: {
      'text-field': NAME,
      'text-font': LABEL_FONT,
      'text-size': ['match', ['get', 'class'], 'city', 16, 'town', 14, 12],
      'text-max-width': 8,
    },
    paint: OVER_IMAGERY,
  },
  {
    id: 'imagery-hamlets',
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'place',
    minzoom: 12,
    filter: roadClass('hamlet'),
    layout: { 'text-field': NAME, 'text-font': LABEL_FONT, 'text-size': 11, 'text-max-width': 8 },
    paint: OVER_IMAGERY,
  },
]

const IMAGERY: StyleSpecification = {
  version: 8,
  glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
  sources: {
    imagery: {
      type: 'raster',
      tiles: ['https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 16,
      attribution: 'Imagery: <a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">USGS</a>',
    },
    // Its TileJSON carries the OpenFreeMap and OpenStreetMap credit
    openmaptiles: { type: 'vector', url: 'https://tiles.openfreemap.org/planet' },
  },
  layers: [{ id: 'imagery', type: 'raster', source: 'imagery' }, ...IMAGERY_ROADS],
}
const STREETS = 'https://tiles.openfreemap.org/styles/liberty'
const LIGHT = 'https://tiles.openfreemap.org/styles/positron'

/**
 * Where a data layer goes in a style's layers: before its first border line or label (a symbol
 * layer), so state and county lines and place names stay above our data (D119); on the imagery,
 * before the roads and names drawn over it. The layers' length when there are none.
 */
export function labelsStart(layers: LayerSpecification[]): number {
  const index = layers.findIndex(
    (layer) =>
      layer.type === 'symbol' ||
      ('source-layer' in layer && layer['source-layer'] === 'boundary') ||
      layer.id.startsWith(ROAD_LAYER_PREFIX),
  )
  return index === -1 ? layers.length : index
}

/**
 * The id of the layer a data layer is added before (`map.addLayer(layer, beneathLabels(map))`): the
 * basemap's first border or label, or undefined (on top) when it has none
 */
export function beneathLabels(map: MapLibreMap): string | undefined {
  const layers = map.getStyle()?.layers ?? []
  return layers[labelsStart(layers)]?.id
}

/**
 * A basemap's style; the imagery's road layers shown or not (roads.svelte.ts keeps the setting, and
 * passes it here so a new map or a switch starts that way)
 */
export function basemapStyle(basemap: Basemap, showRoads = roads.on): StyleSpecification | string {
  if (basemap === 'streets') return STREETS
  if (basemap === 'light') return LIGHT
  if (showRoads) return IMAGERY
  return {
    ...IMAGERY,
    layers: IMAGERY.layers.map((layer) =>
      IMAGERY_ROADS.includes(layer)
        ? ({ ...layer, layout: { ...layer.layout, visibility: 'none' } } as LayerSpecification)
        : layer,
    ),
  }
}

/** Replaces each ['get', 'ref_length'] in an expression with a number when the road has none */
function refLengthOrLong(value: unknown): unknown {
  if (!Array.isArray(value)) return value
  if (value[0] === 'get' && value[1] === 'ref_length' && value.length === 2) return ['coalesce', value, 1000]
  return value.map(refLengthOrLong)
}

/**
 * Fixes OpenFreeMap's street style before it's used: its route shield layers compare ref_length,
 * which roads without a number lack, so MapLibre warned for every tile (the comparison then fails,
 * as it now does without the warning)
 */
export function repairStyle(style: StyleSpecification): StyleSpecification {
  return {
    ...style,
    layers: style.layers.map((layer) =>
      'filter' in layer && layer.filter
        ? ({ ...layer, filter: refLengthOrLong(layer.filter) } as LayerSpecification)
        : layer,
    ),
  }
}

/** For a new map, beside its style: repairs a street style loaded by URL (setBasemap does it for a switch) */
export const transformStyle = (_previous: StyleSpecification | undefined, next: StyleSpecification) => repairStyle(next)

// Each map's switches run one at a time (a fast second click would otherwise start a style while the
// last is loading, and the two resolve out of order): what each map was last asked for, what it shows,
// and the switch in progress
const wanted = new WeakMap<MapLibreMap, Basemap>()
const shown = new WeakMap<MapLibreMap, Basemap>()
const running = new WeakMap<MapLibreMap, Promise<unknown>>()
// A style that hasn't loaded by then (its service is down) gives up, so later switches aren't stuck
// behind it
const STYLE_TIMEOUT_MS = 20_000

/**
 * Changes the basemap. A new style replaces every source and layer, so ours (the sources isOwn
 * picks, and the layers drawing them, in their order) are copied into it (carryOver). `before` runs just before
 * the switch itself (terra-draw stops there). Switches on one map run in turn, and
 * one a later call has replaced is skipped (resolving false). Resolves true once the new style is
 * in place, before its tiles load, or false if it doesn't load in time (another click retries).
 */
export function setBasemap(
  map: MapLibreMap,
  basemap: Basemap,
  isOwn: (sourceId: string) => boolean,
  { before }: { before?: () => void } = {},
): Promise<boolean> {
  wanted.set(map, basemap)
  const run = (running.get(map) ?? Promise.resolve()).then(async () => {
    if (wanted.get(map) !== basemap || shown.get(map) === basemap) return false
    before?.()
    const loaded = new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), STYLE_TIMEOUT_MS)
      map.once('style.load', () => {
        clearTimeout(timer)
        resolve(true)
      })
    })
    // Rebuilt rather than diffed, so 'style.load' fires (a diff applies silently)
    map.setStyle(basemapStyle(basemap), {
      diff: false,
      transformStyle: (previous, unrepaired) => {
        const next = repairStyle(unrepaired)
        if (!previous) return next
        return carryOver(previous, next, isOwn)
      },
    })
    const ok = await loaded
    if (ok) shown.set(map, basemap)
    return ok
  })
  running.set(map, run)
  return run
}

/**
 * next with previous's own sources (those isOwn picks) and the layers drawing them, in their order:
 * those beneath previous's borders and labels go beneath next's, the rest on top
 */
export function carryOver(
  previous: StyleSpecification,
  next: StyleSpecification,
  isOwn: (sourceId: string) => boolean,
): StyleSpecification {
  const own = Object.keys(previous.sources).filter(isOwn)
  const start = labelsStart(previous.layers)
  const ours = (layer: LayerSpecification) => 'source' in layer && own.includes(layer.source as string)
  const under = previous.layers.filter((layer, i) => i < start && ours(layer))
  const over = previous.layers.filter((layer, i) => i >= start && ours(layer))
  const at = labelsStart(next.layers)
  return {
    ...next,
    sources: { ...next.sources, ...Object.fromEntries(own.map((id) => [id, previous.sources[id]])) },
    layers: [...next.layers.slice(0, at), ...under, ...next.layers.slice(at), ...over],
  }
}

/**
 * A map's basemap toggle: shows the choice at once, switches with setBasemap (carrying over the
 * sources isOwn picks), and runs `after` once the new style is in place (images and terra-draw come
 * back there). A switch that fails (its style didn't load in time) puts the toggle back on what the
 * map shows, so the same button tries again; one a later click replaced is left to that click.
 */
export class BasemapSwitch {
  #shown: Basemap
  #wanted: Basemap

  constructor(
    initial: Basemap,
    private readonly options: {
      map: () => MapLibreMap | undefined
      isOwn: (sourceId: string) => boolean
      /** Shows a choice on the toggle */
      show: (basemap: Basemap) => void
      before?: () => void
      after?: () => void
    },
  ) {
    this.#shown = initial
    this.#wanted = initial
  }

  async change(to: Basemap): Promise<boolean> {
    const { map, isOwn, show, before, after } = this.options
    const m = map()
    if (!m || to === this.#wanted) return false
    this.#wanted = to
    show(to)
    const ok = await setBasemap(m, to, isOwn, { before })
    if (ok) {
      this.#shown = to
      after?.()
    } else if (this.#wanted === to) {
      this.#wanted = this.#shown
      show(this.#shown)
    }
    return ok
  }
}
