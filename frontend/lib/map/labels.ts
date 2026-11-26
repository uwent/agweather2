// late-blight-db: src/lib/map/labels.ts (adapted: only the placement, for the saved sites named on a map's image; the
// county labels' selection and dates, and dragged labels, left out)

/** A deliberate cap: past ~10, labels crowd the map into illegibility */
export const MAX_LABELS = 10

export type Point = { x: number; y: number }
export type Rect = { x: number; y: number; w: number; h: number }
/** Offset of the label box's centre from its anchor, in screen pixels */
export type Offset = { dx: number; dy: number }

export type PlacementInput = {
  id: string
  anchor: Point
  /** Measured label size */
  w: number
  h: number
}

/** A label as placed: its text, the point it names and its box, in the map's CSS pixels */
export type LabelLayout = { id: string; text: string; anchor: Point; box: Rect }

const LEADER = 48
const GAP = 6
const ITERATIONS = 80

function overlap(a: Rect, b: Rect, gap: number): { x: number; y: number } | null {
  const ox = Math.min(a.x + a.w + gap, b.x + b.w + gap) - Math.max(a.x, b.x)
  const oy = Math.min(a.y + a.h + gap, b.y + b.h + gap) - Math.max(a.y, b.y)
  return ox > 0 && oy > 0 ? { x: ox, y: oy } : null
}

/**
 * Places labels so they don't overlap each other or the map's own furniture (the legend).
 *
 * Labels start on a short leader pointing away from the group's centre, so a cluster fans outward instead of piling
 * onto itself. Overlaps are then pushed apart along whichever axis needs the smaller move, repeatedly, and labels are
 * kept inside the viewport. A heuristic, not a solver: ten labels in one small region can still crowd.
 */
export function placeLabels(
  inputs: PlacementInput[],
  viewport: { width: number; height: number },
  obstacles: Rect[] = [],
): Map<string, Offset> {
  const offsets = new Map<string, Offset>()
  if (inputs.length === 0) return offsets

  const centre =
    inputs.length === 1
      ? { x: viewport.width / 2, y: viewport.height / 2 }
      : {
          x: inputs.reduce((s, p) => s + p.anchor.x, 0) / inputs.length,
          y: inputs.reduce((s, p) => s + p.anchor.y, 0) / inputs.length,
        }

  const margin = 8
  const fits = (p: PlacementInput, o: Offset) => {
    const r = labelBox(p, o)
    return (
      r.x >= margin &&
      r.y >= margin &&
      r.x + r.w <= viewport.width - margin &&
      r.y + r.h <= viewport.height - margin &&
      // A label on top of its own point hides the very thing it labels
      leaderEnd(p.anchor, r) !== null &&
      !obstacles.some((ob) => overlap(r, ob, GAP))
    )
  }

  for (const p of inputs) {
    let vx = p.anchor.x - centre.x
    let vy = p.anchor.y - centre.y
    const len = Math.hypot(vx, vy)
    // Alone, or dead centre: up and to the right reads naturally
    if (len < 1) [vx, vy] = [Math.SQRT1_2, -Math.SQRT1_2]
    else [vx, vy] = [vx / len, vy / len]

    // The preferred direction first, then others in order of how far they turn from it. Near a viewport edge the
    // preferred direction points off-screen, and clamping would push the label back over its own point
    const preferred = Math.atan2(vy, vx)
    const candidates = [0, 1, -1, 2, -2, 3, -3, 4].map((k) => {
      const angle = preferred + (k * Math.PI) / 4
      const [cx, cy] = [Math.cos(angle), Math.sin(angle)]
      return { dx: cx * (LEADER + p.w / 2), dy: cy * (LEADER + p.h / 2) }
    })
    offsets.set(p.id, candidates.find((o) => fits(p, o)) ?? candidates[0])
  }

  const clamp = (p: PlacementInput, o: Offset): Offset => {
    const minX = margin + p.w / 2 - p.anchor.x
    const maxX = viewport.width - margin - p.w / 2 - p.anchor.x
    const minY = margin + p.h / 2 - p.anchor.y
    const maxY = viewport.height - margin - p.h / 2 - p.anchor.y
    return {
      dx: Math.min(Math.max(o.dx, minX), Math.max(minX, maxX)),
      dy: Math.min(Math.max(o.dy, minY), Math.max(minY, maxY)),
    }
  }

  for (let iter = 0; iter < ITERATIONS; iter++) {
    let moved = false

    for (let i = 0; i < inputs.length; i++) {
      for (let j = i + 1; j < inputs.length; j++) {
        const a = inputs[i]
        const b = inputs[j]
        const oa = offsets.get(a.id)!
        const ob = offsets.get(b.id)!
        const ra = labelBox(a, oa)
        const rb = labelBox(b, ob)
        const o = overlap(ra, rb, GAP)
        if (!o) continue

        // Separate along the axis that needs the smaller push
        const alongX = o.x < o.y
        const sign = alongX
          ? Math.sign(ra.x + ra.w / 2 - (rb.x + rb.w / 2)) || 1
          : Math.sign(ra.y + ra.h / 2 - (rb.y + rb.h / 2)) || 1
        const push = ((alongX ? o.x : o.y) + 0.5) / 2

        if (alongX) {
          offsets.set(a.id, { dx: oa.dx + sign * push, dy: oa.dy })
          offsets.set(b.id, { dx: ob.dx - sign * push, dy: ob.dy })
        } else {
          offsets.set(a.id, { dx: oa.dx, dy: oa.dy + sign * push })
          offsets.set(b.id, { dx: ob.dx, dy: ob.dy - sign * push })
        }
        moved = true
      }
    }

    for (const p of inputs) {
      let o = offsets.get(p.id)!
      for (const obstacle of obstacles) {
        const r = labelBox(p, o)
        const ov = overlap(r, obstacle, GAP)
        if (!ov) continue
        if (ov.x < ov.y) {
          const sign = Math.sign(r.x + r.w / 2 - (obstacle.x + obstacle.w / 2)) || 1
          o = { dx: o.dx + sign * (ov.x + 0.5), dy: o.dy }
        } else {
          const sign = Math.sign(r.y + r.h / 2 - (obstacle.y + obstacle.h / 2)) || 1
          o = { dx: o.dx, dy: o.dy + sign * (ov.y + 0.5) }
        }
        moved = true
      }
      offsets.set(p.id, clamp(p, o))
    }

    if (!moved) break
  }

  return offsets
}

/** Where a leader line meets its label: the point on the box's edge nearest the anchor. Null when the anchor is
 * inside the box, where a line would only be noise */
export function leaderEnd(anchor: Point, box: Rect): Point | null {
  const x = Math.min(Math.max(anchor.x, box.x), box.x + box.w)
  const y = Math.min(Math.max(anchor.y, box.y), box.y + box.h)
  return x === anchor.x && y === anchor.y ? null : { x, y }
}

export function labelBox(input: Pick<PlacementInput, 'anchor' | 'w' | 'h'>, o: Offset): Rect {
  return {
    x: input.anchor.x + o.dx - input.w / 2,
    y: input.anchor.y + o.dy - input.h / 2,
    w: input.w,
    h: input.h,
  }
}

/**
 * The labels for named points (saved sites) inside a map's view: each projected to the map's CSS pixels, those
 * outside left out, at most `max` (the first in the reader's order), placed clear of each other and the obstacles.
 * `measure` gives a text's width in CSS pixels.
 */
export function layoutLabels(
  points: { id: string; text: string; lat: number; lng: number }[],
  project: (lng: number, lat: number) => Point,
  viewport: { width: number; height: number },
  measure: (text: string) => number,
  obstacles: Rect[] = [],
  max = MAX_LABELS,
): LabelLayout[] {
  const inside = points
    .map((p) => ({ ...p, anchor: project(p.lng, p.lat) }))
    .filter(({ anchor: a }) => a.x >= 0 && a.y >= 0 && a.x <= viewport.width && a.y <= viewport.height)
    .slice(0, max)
  const inputs = inside.map((p) => ({ id: p.id, anchor: p.anchor, w: Math.ceil(measure(p.text)) + 16, h: 22 }))
  const offsets = placeLabels(inputs, viewport, obstacles)
  return inside.map((p, i) => ({
    id: p.id,
    text: p.text,
    anchor: p.anchor,
    box: labelBox(inputs[i], offsets.get(p.id)!),
  }))
}
