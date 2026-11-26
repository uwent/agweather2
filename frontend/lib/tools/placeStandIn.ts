// STAND-IN, TO BE REPLACED (w7-oakwilt, 2026-11-26): the parts of w7-tools' `lib/tools/place.ts` the oak wilt page
// uses, with the same names and types, so the swap at merge is an import change. Delete this file then.

import { roundCoord } from '../siteKey'
import { codecs, field, type LatLng } from '../viewState'

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
