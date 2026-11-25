// A group's map view (F12, track 3 step 11): /map framed to the group's sites with each one marked and named above the
// data, opening on the group's map layer if its preferences choose one. The view carries the group as its sites'
// coordinates and names (`group=`), not the group's id, so a shared link shows the same sites to a reader who doesn't
// have the group.

import type { GeoJSONSource, GeoJSONSourceSpecification, Map as MapLibreMap } from 'maplibre-gl'

import { LABEL_FONT, labelPaint } from '@/lib/map/basemaps'
import { routes } from '@/lib/routes'
import type { Codec } from '@/lib/viewState'

import { siteLabel, type Group, type Site } from '../sitesDoc'

export type MapGroup = { name: string; sites: { lat: number; lng: number; name: string }[] }

const coord = (value: number) => String(Number(value.toFixed(4)))

/** `name;lat,lng,name;lat,lng,name`, each name URI-encoded so its commas and semicolons stay its own */
export const groupCodec: Codec<MapGroup> = {
  parse(text) {
    const [head, ...parts] = text.split(';')
    if (head === undefined || !parts.length) return undefined
    try {
      const sites = parts.map((part) => {
        const [lat, lng, ...rest] = part.split(',')
        const site = { lat: Number(lat), lng: Number(lng), name: decodeURIComponent(rest.join(',')) }
        if (
          !Number.isFinite(site.lat) ||
          !Number.isFinite(site.lng) ||
          Math.abs(site.lat) > 90 ||
          Math.abs(site.lng) > 180
        )
          throw new Error('not a place')
        return site
      })
      return { name: decodeURIComponent(head), sites }
    } catch {
      return undefined
    }
  },
  format: (group) =>
    [
      encodeURIComponent(group.name),
      ...group.sites.map((s) => `${coord(s.lat)},${coord(s.lng)},${encodeURIComponent(s.name)}`),
    ].join(';'),
}

/** A group as the map's view takes it: its sites in the reader's order, named (a site without a name by its
 * coordinates) */
export function mapGroup(group: Group, sites: readonly Site[]): MapGroup {
  const members = sites.filter((s) => group.siteKeys.includes(s.key))
  return { name: group.name, sites: members.map((s) => ({ lat: s.lat, lng: s.lng, name: siteLabel(s) })) }
}

/** The link that opens /map on a group: its sites, and its layer if its preferences choose one */
export function groupMapUrl(group: Group, sites: readonly Site[], layer?: string): string {
  const query = new URLSearchParams({ group: groupCodec.format(mapGroup(group, sites)) })
  if (layer) query.set('layer', layer)
  return `${routes.map()}?${query}`
}

/** The box around a group's sites, `[[west, south], [east, north]]` */
export function groupBounds(group: MapGroup): [[number, number], [number, number]] | null {
  if (!group.sites.length) return null
  const lats = group.sites.map((s) => s.lat)
  const lngs = group.sites.map((s) => s.lng)
  return [
    [Math.min(...lngs), Math.min(...lats)],
    [Math.max(...lngs), Math.max(...lats)],
  ]
}

const SOURCE = 'group-sites'

/** Draws a group's sites on the map (a dot and its name, above the data and the basemap's labels), or clears them
 * (`null`). Again after a basemap switch, which replaces the style and everything added to it. */
export function drawGroup(map: MapLibreMap, group: MapGroup | null): void {
  const data: GeoJSONSourceSpecification['data'] = {
    type: 'FeatureCollection',
    features: (group?.sites ?? []).map((s) => ({
      type: 'Feature',
      properties: { name: s.name },
      geometry: { type: 'Point', coordinates: [s.lng, s.lat] },
    })),
  }
  const source = map.getSource(SOURCE) as GeoJSONSource | undefined
  if (source) {
    source.setData(data)
    return
  }
  map.addSource(SOURCE, { type: 'geojson', data })
  map.addLayer({
    id: `${SOURCE}-dot`,
    type: 'circle',
    source: SOURCE,
    paint: {
      'circle-radius': 5,
      'circle-color': '#ffffff',
      'circle-stroke-color': '#000000',
      'circle-stroke-width': 2,
    },
  })
  map.addLayer({
    id: `${SOURCE}-name`,
    type: 'symbol',
    source: SOURCE,
    layout: {
      'text-field': ['get', 'name'],
      'text-font': LABEL_FONT,
      'text-size': 13,
      'text-anchor': 'bottom',
      'text-offset': [0, -0.6],
      'text-max-width': 12,
      'text-allow-overlap': false,
    },
    paint: labelPaint(1.5),
  })
}
