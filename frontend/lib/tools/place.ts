// The place a tool answers for (track 5): a point picked by search, typed coordinates or a saved site, kept in the
// tool's view as `at` (to 4 decimals, a site's key) and `name` (what the search found, or the shared link's), so a
// tool's Share link opens on the same place. `PlacePicker.svelte` shows it and changes it; a page spreads
// `PLACE_FIELDS` into its view's fields and reads the place with `placeOf`.
//
//   const view = viewState({ ...PLACE_FIELDS, dd: field(codecs.string, '') })
//   const place = $derived(placeOf($view))
//   <PlacePicker {place} onpick={(p) => view.patch(placeView(p))} />

import { codecs, field, type LatLng } from '../viewState'
import { roundCoord, siteKey } from '../siteKey'
import { sitePath } from '../explorer/links'
import { siteLabel } from '../sitesDoc'
import type { LocateData } from '@/types/api'
import { coordinates, placeName } from '../sites/text'

/** A tool's place: its coordinates and a name for it (a search's or a link's), null where it has none */
export type Place = { lat: number; lng: number; name: string | null }

/** The view's settings for the place: `at=43.0731,-89.4012&name=Madison` */
export type PlaceView = { at: LatLng | null; name: string }

export const PLACE_FIELDS = {
  at: field(codecs.latLng(4), null),
  name: field(codecs.string, ''),
}

/** The place a view names, or null if it names none */
export function placeOf(view: PlaceView): Place | null {
  if (!view.at) return null
  const name = view.name.trim().slice(0, 80)
  return { lat: view.at.lat, lng: view.at.lng, name: name || null }
}

/** The view's settings for a place picked (rounded to a site's key, so the same place is the same link) */
export function placeView(place: Place | null): PlaceView {
  if (!place) return { at: null, name: '' }
  return { at: { lat: roundCoord(place.lat), lng: roundCoord(place.lng) }, name: place.name?.trim() ?? '' }
}

/** What to call a place: its saved site's name, else its own, else where /locate puts it, else its coordinates */
export function placeTitle(
  place: Place,
  saved: { name: string; lat: number; lng: number } | null | undefined,
  location?: Pick<LocateData, 'county' | 'state'> | null,
): string {
  if (saved) return siteLabel(saved)
  return place.name || placeName(location ?? null) || coordinates(place.lat, place.lng)
}

/** The line under a place's name: where it is, its coordinates, and whether we cover it */
export function placeLine(place: Place, location: Pick<LocateData, 'county' | 'state' | 'in_box'> | null): string {
  const where = placeName(location)
  const parts = [where, coordinates(place.lat, place.lng)].filter(Boolean)
  const line = parts.join(' · ')
  if (location && !location.in_box) return `${line}. Outside the area we cover: weather from Open-Meteo’s models.`
  return line
}

/** The site page for a place, with its name where it has one */
export const placeSitePath = (place: Place): string => sitePath(place.lat, place.lng, place.name)

/** A place's site key (`43.0731,-89.4012`), as saved sites are kept */
export const placeKey = (place: Place): string => siteKey(place.lat, place.lng)
