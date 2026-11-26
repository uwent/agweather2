// /data's locations for a download (track 7 step 7.1): saved sites and places found, each once (by its site key, to
// 4 decimals), up to the API's 50 a request.

import { formatCoords, roundCoord, siteKey } from '../siteKey'
import { MAX_POINTS } from '../sites/dataRequest'

export type Chosen = { key: string; lat: number; lng: number; name: string }

/** The list with a place added at its end, or why it wasn't */
export function addLocation(
  list: readonly Chosen[],
  place: { lat: number; lng: number; name: string },
): { list: Chosen[]; message: string | null } {
  const lat = roundCoord(place.lat)
  const lng = roundCoord(place.lng)
  const key = siteKey(lat, lng)
  const label = place.name || formatCoords(lat, lng)
  if (list.some((c) => c.key === key)) return { list: [...list], message: `${label} is already in the list.` }
  if (list.length >= MAX_POINTS)
    return {
      list: [...list],
      message: `A download can include up to ${MAX_POINTS} locations. Remove one to add ${label}.`,
    }
  return { list: [...list, { key, lat, lng, name: place.name }], message: null }
}

/** Several places added in order, as many as fit; the message says how many didn't */
export function addLocations(
  list: readonly Chosen[],
  places: readonly { lat: number; lng: number; name: string }[],
): { list: Chosen[]; message: string | null } {
  let next = [...list]
  let full = 0
  for (const place of places) {
    const added = addLocation(next, place)
    if (added.message && next.length >= MAX_POINTS) full++
    next = added.list
  }
  const message = full
    ? `A download can include up to ${MAX_POINTS} locations, so ${full} ${full === 1 ? 'site wasn’t' : 'sites weren’t'} added.`
    : null
  return { list: next, message }
}
