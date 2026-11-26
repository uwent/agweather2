// A site's key: its coordinates rounded to 4 decimal places (about 11 m), which is also its page's address
// (F1: `/sites/43.07,-89.4`). Two saved sites can share a grid cell but not a key. Trailing zeros are left out, so
// the same place always has the same key however its coordinates were typed.

export const KEY_DECIMALS = 4

/** A place found by search or typed coordinates; name '' for coordinates */
export type PickedPlace = { lat: number; lng: number; name: string }

/** A coordinate rounded to the key's precision, -0 made 0 */
export function roundCoord(value: number): number {
  const rounded = Number(value.toFixed(KEY_DECIMALS))
  return Object.is(rounded, -0) ? 0 : rounded
}

export function validCoords(lat: number, lng: number): boolean {
  return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180
}

/** '43.07,-89.4' for (43.07, -89.40001) */
export function siteKey(lat: number, lng: number): string {
  return `${roundCoord(lat)},${roundCoord(lng)}`
}

/** The coordinates in a key or a typed pair ('43.07,-89.4', '43.07, -89.40'), or null if it isn't one */
export function parseSiteKey(text: string): { lat: number; lng: number } | null {
  const match = /^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$/.exec(text)
  if (!match) return null
  const lat = Number(match[1])
  const lng = Number(match[2])
  return validCoords(lat, lng) ? { lat: roundCoord(lat), lng: roundCoord(lng) } : null
}

/** The site page's address for a key (or any coordinates): the one place that builds it */
export function siteUrl(key: string, name?: string): string {
  const path = `/sites/${key}`
  return name ? `${path}?${new URLSearchParams({ name })}` : path
}

/** "43.07° N, 89.40° W", for a site without a name */
export function formatCoords(lat: number, lng: number, digits = 2): string {
  const ns = lat >= 0 ? 'N' : 'S'
  const ew = lng >= 0 ? 'E' : 'W'
  return `${Math.abs(lat).toFixed(digits)}° ${ns}, ${Math.abs(lng).toFixed(digits)}° ${ew}`
}

/** A model at a site: `/sites/44.12,-89.52/models/late-blight-dsv` (the `site-model` route) */
export function siteModelUrl(key: string, model: string): string {
  return `/sites/${key}/models/${encodeURIComponent(model)}`
}
