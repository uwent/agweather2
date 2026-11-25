// WISP 3: app/frontend/lib/map/overlays.ts (adapted: AgWeather's words, and the drought area our coverage)
import { type LngLat, pointInPolygon } from '@/lib/geo'

import { COVERAGE_BOUNDS } from './coverage'

import { reflectivityAt } from './radar'

// Optional public layers for the map, loaded by the browser from their
// providers, never by our server. Each can fail or be slow; the map marks a failing one
// unavailable and carries on. valueAt says what a layer has at a point, for the tooltip.

export type OverlayId = 'radar' | 'rain24' | 'rain72' | 'qpf1' | 'qpf3' | 'qpf7' | 'drought'

export type Legend =
  /** A color ramp from light to heavy */
  | { kind: 'ramp'; colors: string[]; start: string; end: string }
  /** Colors from rain depths (the class's lower bound), labeled in the user's units */
  | { kind: 'depths'; items: { inches: number; color: string }[] }
  | { kind: 'classes'; items: { label: string; color: string }[] }

/** What a layer has at a point */
export type OverlayValue =
  | { kind: 'none' }
  /** A rain depth, or a class of them (from inches up to upTo) */
  | { kind: 'depth'; inches: number; upTo?: number | null }
  | { kind: 'text'; text: string; color?: string }

type Base = {
  id: OverlayId
  name: string
  description: string
  credit: { name: string; url: string }
  /** For the map's attribution control */
  attribution: string
  legend: Legend
  /** What the tooltip says where the layer has nothing */
  none: string
  opacity: number
  /** How often to reload it while it's shown */
  refreshMinutes?: number
  /** When the data is for, for the panel ("Radar at 3:20 PM") */
  time?: () => Promise<string | null>
}
export type RasterOverlay = Base & {
  kind: 'raster'
  tiles: (stamp: number) => string[]
  valueAt: (point: LngLat, signal?: AbortSignal) => Promise<OverlayValue>
}
/** The drought layer's polygons are loaded whole, so its values are looked up in the browser */
export type VectorOverlay = Base & { kind: 'drought' }
export type Overlay = RasterOverlay | VectorOverlay

async function json(url: string, signal?: AbortSignal) {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`${response.status} from ${url}`)
  return response.json()
}

/** "Sat 3:20 PM" in the browser's time zone */
export function describeTime(date: Date): string {
  return date.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })
}

const NOAA = 'https://mapservices.weather.noaa.gov'
const point = ([lng, lat]: LngLat) => JSON.stringify({ x: lng, y: lat, spatialReference: { wkid: 4326 } })

/** An ArcGIS image service's pixel value at a point ("NoData" where there's none), as a number or null */
async function identify(service: string, at: LngLat, mosaicRule: object | null, signal?: AbortSignal) {
  const params = new URLSearchParams({
    geometry: point(at),
    geometryType: 'esriGeometryPoint',
    returnGeometry: 'false',
    returnCatalogItems: 'false',
    f: 'json',
  })
  if (mosaicRule) params.set('mosaicRule', JSON.stringify(mosaicRule))
  const data = await json(`${service}/identify?${params}`, signal)
  const value = Number(data?.value)
  return data?.value === undefined || data.value === 'NoData' || Number.isNaN(value) ? null : value
}

// Radar: the Iowa Environmental Mesonet's tiles, for the picture and (from the same tile's colors,
// radar.ts) the value at a point
const IEM = 'https://mesonet.agron.iastate.edu'

/** What a reflectivity means for rain, roughly (NWS guidance) */
export function describeReflectivity(dbz: number): string {
  if (dbz < 20) return 'Very light, or not reaching the ground'
  if (dbz < 30) return 'Light rain'
  if (dbz < 40) return 'Moderate rain'
  if (dbz < 50) return 'Heavy rain'
  return 'Very heavy rain, maybe hail'
}

async function radarTime() {
  const data = await json(`${IEM}/data/gis/images/4326/USCOMP/n0q_0.json`)
  return data?.meta?.valid ? `Radar at ${describeTime(new Date(data.meta.valid))}` : null
}

// Recent rain: NOAA's MRMS estimates (radar with gauges), drawn with NOAA's own classes. Its pixel
// values are millimeters.
const MRMS_SERVICE = `${NOAA}/raster/rest/services/obs/mrms_qpe/ImageServer`
const MM_PER_INCH = 25.4
const mrmsMosaic = (hours: 24 | 72) => ({
  mosaicMethod: 'esriMosaicAttribute',
  where: `name='conus_QPE_${hours}H'`,
})
const mrmsTiles = (hours: 24 | 72) => (stamp: number) => [
  `${MRMS_SERVICE}/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32` +
    `&transparent=true&mosaicRule=${encodeURIComponent(JSON.stringify(mrmsMosaic(hours)))}` +
    `&renderingRule=${encodeURIComponent(JSON.stringify({ rasterFunction: `rft_${hours}hr` }))}&f=image&t=${stamp}`,
]
async function mrmsValue(hours: 24 | 72, at: LngLat, signal?: AbortSignal): Promise<OverlayValue> {
  const mm = await identify(MRMS_SERVICE, at, mrmsMosaic(hours), signal)
  // The service gives dry ground as 0, so NoData (or no answer) means the estimate is missing there
  if (mm === null) return { kind: 'text', text: 'No data here' }
  const inches = mm / MM_PER_INCH
  return inches < 0.01 ? { kind: 'none' } : { kind: 'depth', inches }
}
// NOAA's classes for the 24- and 72-hour estimates (lower bounds, inches), the lower ones
const MRMS_COLORS = [
  '#00ecec',
  '#00c8f0',
  '#00a0ff',
  '#003cff',
  '#00ff00',
  '#00dc00',
  '#00be00',
  '#008d00',
  '#ffff00',
  '#f0d200',
  '#e7b400',
  '#c87800',
]
const mrmsLegend = (bounds: number[]): Legend => ({
  kind: 'depths',
  items: bounds.map((inches, i) => ({ inches, color: MRMS_COLORS[i] })),
})
const MRMS_CREDIT = { name: 'NOAA MRMS, National Weather Service', url: 'https://www.nssl.noaa.gov/projects/mrms/' }
const MRMS_ATTRIBUTION = 'Rain estimates: <a href="https://www.nssl.noaa.gov/projects/mrms/">NOAA MRMS</a>'

// Forecast rain: the Weather Prediction Center's forecast, drawn by its map service; its polygons are
// bands (0.01 to 0.10 inches, and so on), so a point is in one or none
const WPC_QPF = `${NOAA}/vector/rest/services/precip/wpc_qpf/MapServer`
/** WPC's quantitative precipitation forecast layers: day 1, days 1–3, days 1–7 */
export const QPF_LAYERS = { qpf1: 1, qpf3: 9, qpf7: 11 } as const
/** WPC's classes, inches */
export const QPF_CLASSES = [0.01, 0.1, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 4, 5, 7, 10, 15, 20]
const qpfTiles = (layer: number) => (stamp: number) => [
  `${WPC_QPF}/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true` +
    `&layers=show:${layer}&f=image&t=${stamp}`,
]
/** The forecast's class at a point: from its lower bound up to the next class */
export function qpfValue(classes: number[]): OverlayValue {
  if (!classes.length) return { kind: 'none' }
  const inches = Math.max(...classes)
  return { kind: 'depth', inches, upTo: QPF_CLASSES.find((bound) => bound > inches) ?? null }
}
const qpfValueAt = (layer: number) => async (at: LngLat, signal?: AbortSignal) => {
  const params = new URLSearchParams({
    geometry: `${at[0]},${at[1]}`,
    geometryType: 'esriGeometryPoint',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    outFields: 'qpf',
    returnGeometry: 'false',
    f: 'json',
  })
  const data = await json(`${WPC_QPF}/${layer}/query?${params}`, signal)
  return qpfValue((data?.features ?? []).map((f: { attributes: { qpf: number } }) => Number(f.attributes.qpf)))
}
const WPC_CREDIT = { name: 'NOAA Weather Prediction Center', url: 'https://www.wpc.ncep.noaa.gov/qpf/qpf2.shtml' }
const WPC_ATTRIBUTION = 'Forecast rain: <a href="https://www.wpc.ncep.noaa.gov/">NOAA WPC</a>'
const QPF_LEGEND: Legend = {
  kind: 'depths',
  items: [
    { inches: 0.01, color: '#7fff00' },
    { inches: 0.1, color: '#00ff00' },
    { inches: 0.25, color: '#088b00' },
    { inches: 0.5, color: '#104e8b' },
    { inches: 0.75, color: '#1e90ff' },
    { inches: 1, color: '#00b2ee' },
    { inches: 1.5, color: '#8968cd' },
    { inches: 2, color: '#8b008b' },
    { inches: 3, color: '#ff0000' },
    { inches: 5, color: '#ff7f00' },
  ],
}

/** WPC's issue_time ("2026-10-17 22:03:02", UTC) as a Date */
export const parseWpcTime = (value: string) => new Date(`${value.replace(' ', 'T')}Z`)

const qpfTime = (layer: number) => async () => {
  const data = await json(
    `${WPC_QPF}/${layer}/query?where=1%3D1&outFields=issue_time&returnGeometry=false&resultRecordCount=1&f=json`,
  )
  const issued = data?.features?.[0]?.attributes?.issue_time
  return issued ? `Issued ${describeTime(parseWpcTime(issued))}` : null
}

const QPF_NOTE =
  "Prepared by National Weather Service forecasters. AgWeather's own forecast, from the National Blend of Models, can differ."

const qpf = (id: 'qpf1' | 'qpf3' | 'qpf7', name: string, description: string): RasterOverlay => ({
  id,
  kind: 'raster',
  name,
  description: `${description} ${QPF_NOTE}`,
  credit: WPC_CREDIT,
  attribution: WPC_ATTRIBUTION,
  legend: QPF_LEGEND,
  none: 'Less than 0.01 in',
  opacity: 0.6,
  refreshMinutes: 60,
  tiles: qpfTiles(QPF_LAYERS[id]),
  valueAt: qpfValueAt(QPF_LAYERS[id]),
  time: qpfTime(QPF_LAYERS[id]),
})

const mrms = (id: 'rain24' | 'rain72', hours: 24 | 72, bounds: number[]): RasterOverlay => ({
  id,
  kind: 'raster',
  name: `Rain, last ${hours} hours`,
  description:
    "Estimated from radar and rain gauges (NOAA MRMS), updated hourly. Compare it with your gauge and AgWeather's precipitation.",
  credit: MRMS_CREDIT,
  attribution: MRMS_ATTRIBUTION,
  legend: mrmsLegend(bounds),
  none: 'No rain',
  opacity: 0.7,
  refreshMinutes: 30,
  tiles: mrmsTiles(hours),
  valueAt: (at, signal) => mrmsValue(hours, at, signal),
})

/** Rain layers: one at a time */
export const RAIN_OVERLAYS: RasterOverlay[] = [
  {
    id: 'radar',
    kind: 'raster',
    name: 'Radar now',
    description: 'Radar showing where rain is falling across the US, updated every 5 minutes.',
    credit: { name: 'Iowa Environmental Mesonet, NOAA', url: 'https://mesonet.agron.iastate.edu/ogc/' },
    attribution: 'Radar: <a href="https://mesonet.agron.iastate.edu/">Iowa Environmental Mesonet</a>, NOAA',
    legend: {
      kind: 'ramp',
      colors: [
        '#04e9e7',
        '#019ff4',
        '#0300f4',
        '#02fd02',
        '#01c501',
        '#008e00',
        '#fdf802',
        '#e5bc00',
        '#fd9500',
        '#fd0000',
        '#bc0000',
        '#f800fd',
      ],
      start: 'Light',
      end: 'Heavy',
    },
    none: 'No rain on radar',
    opacity: 0.7,
    refreshMinutes: 5,
    // The stamp makes a refresh fetch new tiles rather than the browser's cached ones
    tiles: (stamp) => [`${IEM}/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png?t=${stamp}`],
    valueAt: async (at, signal) => {
      const dbz = await reflectivityAt(at, signal)
      return dbz === null || dbz < 5
        ? { kind: 'none' }
        : { kind: 'text', text: `${describeReflectivity(dbz)} (${Math.round(dbz)} dBZ)` }
    },
    time: radarTime,
  },
  mrms('rain24', 24, [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 2.5]),
  mrms('rain72', 72, [0.01, 0.1, 0.25, 0.5, 1, 1.5, 2, 3, 4, 5]),
  qpf('qpf1', 'Forecast rain, day 1', 'The next 24 hours from 7 pm Central.'),
  qpf('qpf3', 'Forecast rain, days 1–3', 'The next 3 days.'),
  qpf('qpf7', 'Forecast rain, days 1–7', 'The next 7 days.'),
]

const USDM_QUERY =
  'https://services5.arcgis.com/0OTVzJS4K09zlixn/ArcGIS/rest/services/USDM_current/FeatureServer/0/query'

/** The Drought Monitor's categories and standard colors */
export const DROUGHT_CATEGORIES = [
  { dm: 0, label: 'D0 Abnormally dry', color: '#ffff00' },
  { dm: 1, label: 'D1 Moderate drought', color: '#fcd37f' },
  { dm: 2, label: 'D2 Severe drought', color: '#ffaa00' },
  { dm: 3, label: 'D3 Extreme drought', color: '#e60000' },
  { dm: 4, label: 'D4 Exceptional drought', color: '#730000' },
]

export const DROUGHT_OVERLAY: VectorOverlay = {
  id: 'drought',
  kind: 'drought',
  name: 'Drought Monitor',
  description: 'The U.S. Drought Monitor, released each Thursday.',
  credit: { name: 'National Drought Mitigation Center, USDA, NOAA', url: 'https://droughtmonitor.unl.edu/' },
  attribution: 'Drought: <a href="https://droughtmonitor.unl.edu/">U.S. Drought Monitor</a>',
  legend: { kind: 'classes', items: DROUGHT_CATEGORIES.map(({ label, color }) => ({ label, color })) },
  none: 'No drought',
  opacity: 0.45,
}

export const OVERLAYS: Overlay[] = [...RAIN_OVERLAYS, DROUGHT_OVERLAY]

/** Bottom to top; each overlay is drawn under the ones after it, and all under the systems */
export const OVERLAY_ORDER: OverlayId[] = ['drought', 'radar', 'rain24', 'rain72', 'qpf1', 'qpf3', 'qpf7']

/** [west, south, east, north] */
export type Bounds = [number, number, number, number]

/** The Drought Monitor's current polygons in an area, as GeoJSON, simplified to about 1 km */
export function droughtUrl([west, south, east, north]: Bounds): string {
  const params = new URLSearchParams({
    where: '1=1',
    outFields: 'DM,ValidStart',
    geometry: [west, south, east, north].map((value) => value.toFixed(3)).join(','),
    geometryType: 'esriGeometryEnvelope',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    outSR: '4326',
    maxAllowableOffset: '0.01',
    geometryPrecision: '4',
    f: 'geojson',
  })
  return `${USDM_QUERY}?${params}`
}

/** The area to load drought polygons for: around the points, wide enough to zoom out a little, or the coverage without any */
export function droughtBounds(points: LngLat[], margin = 3): Bounds {
  if (!points.length) return COVERAGE_BOUNDS
  const lngs = points.map(([lng]) => lng)
  const lats = points.map(([, lat]) => lat)
  return [
    Math.min(...lngs) - margin,
    Math.min(...lats) - margin,
    Math.max(...lngs) + margin,
    Math.max(...lats) + margin,
  ]
}

type Geometry = { type: 'Polygon'; coordinates: LngLat[][] } | { type: 'MultiPolygon'; coordinates: LngLat[][][] }
export type DroughtFeature = {
  type: 'Feature'
  properties: { DM: number; ValidStart?: number | null }
  geometry: Geometry | null
}
export type DroughtData = { type: 'FeatureCollection'; features: DroughtFeature[] }

const contains = (geometry: Geometry | null, point: LngLat) =>
  geometry?.type === 'Polygon'
    ? pointInPolygon(point, geometry.coordinates)
    : geometry?.type === 'MultiPolygon'
      ? geometry.coordinates.some((polygon) => pointInPolygon(point, polygon))
      : false

/**
 * The Drought Monitor category at a point: the highest one whose area contains it (the map's areas
 * overlap, D1 inside D0 and so on), or null for none
 */
export function droughtAt(data: DroughtData, point: LngLat) {
  const found = data.features.filter((feature) => contains(feature.geometry, point)).map((f) => f.properties.DM)
  if (!found.length) return null
  return DROUGHT_CATEGORIES.find((category) => category.dm === Math.max(...found)) ?? null
}

/** The map's week ("Map for Oct 13"), from its features' ValidStart (epoch ms) */
export function droughtDate(data: DroughtData): Date | null {
  const start = data.features.find((feature) => feature.properties.ValidStart)?.properties.ValidStart
  return start ? new Date(start) : null
}
