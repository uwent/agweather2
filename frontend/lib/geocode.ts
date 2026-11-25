// WISP 3: app/frontend/lib/geocode.ts (copied)
// Place search for the system map ("hancock wi"), from OpenStreetMap's Nominatim. Its usage policy
// allows occasional searches from a browser but not search-as-you-type, so the map searches only
// when the user submits. Results are limited to the US and Canada, like system locations.

export type Place = {
  label: string
  /** [lng, lat] */
  center: [number, number]
  /** [west, south, east, north] */
  bounds: [number, number, number, number]
}

const ENDPOINT = 'https://nominatim.openstreetmap.org/search'
export const GEOCODER_ATTRIBUTION = 'Search © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'

type NominatimResult = { display_name: string; lat: string; lon: string; boundingbox: [string, string, string, string] }

export function parsePlaces(results: NominatimResult[]): Place[] {
  return results.map((result) => {
    const [south, north, west, east] = result.boundingbox.map(Number)
    return {
      // "Hancock, Waushara County, Wisconsin, United States" → without the country
      label: result.display_name.replace(/, (United States|Canada)$/, ''),
      center: [Number(result.lon), Number(result.lat)],
      bounds: [west, south, east, north],
    }
  })
}

/** near: the map's current [west, south, east, north], which results inside are preferred to (not limited to) */
export async function searchPlaces(query: string, near?: Place['bounds'], signal?: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({ q: query, format: 'jsonv2', limit: '5', countrycodes: 'us,ca' })
  if (near) params.set('viewbox', near.join(','))
  const response = await fetch(`${ENDPOINT}?${params}`, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`Search failed (${response.status})`)
  return parsePlaces(await response.json())
}
