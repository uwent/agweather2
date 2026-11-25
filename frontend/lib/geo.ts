// WISP 3: app/frontend/lib/geo.ts (adapted: only LngLat and pointInPolygon, which the map overlays use; WISP's irrigation geometry isn't taken)

export type LngLat = [number, number]

/** Whether a point is inside a polygon (its outer ring, outside its holes), in plain lng/lat */
export function pointInPolygon(point: LngLat, polygon: LngLat[][]): boolean {
  const [outer, ...holes] = polygon
  return !!outer && inRing(point, outer) && !holes.some((hole) => inRing(point, hole))
}

function inRing([x, y]: LngLat, ring: LngLat[]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}
