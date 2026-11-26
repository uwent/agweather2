// A fitted model's training area on the map (D101): the outline built by `scripts/make_training_areas.py` from the
// Census Bureau's boundaries, loaded only when a fitted model's map is shown, and whether a point is inside it.

type Ring = [number, number][]
type Polygon = { type: 'Polygon'; coordinates: Ring[] }
type MultiPolygon = { type: 'MultiPolygon'; coordinates: Ring[][] }

export type TrainingOutline = { codes: string[]; geometry: Polygon | MultiPolygon }

let loading: Promise<Record<string, TrainingOutline>> | undefined

/** A model's outline, or null when it has none (the file is fetched once, the first time it's needed) */
export async function trainingOutline(modelId: string): Promise<TrainingOutline | null> {
  loading ??= import('./training-areas.json').then(
    (module) => module.default as unknown as Record<string, TrainingOutline>,
  )
  return (await loading)[modelId] ?? null
}

/** Whether a point is inside the outline (even–odd over every ring, so holes count as outside) */
export function insideOutline(geometry: Polygon | MultiPolygon, lng: number, lat: number): boolean {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
  let inside = false
  for (const ring of polygons.flat()) {
    for (let a = 0, b = ring.length - 1; a < ring.length; b = a++) {
      const [x1, y1] = ring[a]
      const [x2, y2] = ring[b]
      if (y1 > lat !== y2 > lat && lng < ((x2 - x1) * (lat - y1)) / (y2 - y1) + x1) inside = !inside
    }
  }
  return inside
}

/** The outline as a feature, for a GeoJSON source */
export const outlineFeature = (geometry: Polygon | MultiPolygon) => ({
  type: 'Feature' as const,
  properties: {},
  geometry,
})
