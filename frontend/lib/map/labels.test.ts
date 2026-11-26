import { describe, expect, it } from 'vitest'

import { labelBox, layoutLabels, leaderEnd, MAX_LABELS, placeLabels, type PlacementInput, type Rect } from './labels'

function overlaps(a: Rect, b: Rect) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

describe('placeLabels', () => {
  const viewport = { width: 1000, height: 700 }
  const label = (id: string, x: number, y: number): PlacementInput => ({ id, anchor: { x, y }, w: 150, h: 24 })

  function boxes(inputs: PlacementInput[], obstacles: Rect[] = []) {
    const offsets = placeLabels(inputs, viewport, obstacles)
    return inputs.map((p) => labelBox(p, offsets.get(p.id)!))
  }

  it('separates a tight cluster so no two labels overlap', () => {
    const cluster = Array.from({ length: 8 }, (_, i) =>
      label(String(i), 500 + (i % 3) * 12, 350 + Math.floor(i / 3) * 12),
    )
    const placed = boxes(cluster)
    for (let i = 0; i < placed.length; i++)
      for (let j = i + 1; j < placed.length; j++) expect(overlaps(placed[i], placed[j])).toBe(false)
  })

  it('keeps every label inside the viewport, even for an anchor at the edge', () => {
    for (const box of boxes([label('edge', 995, 5), label('other', 5, 695)])) {
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.y).toBeGreaterThanOrEqual(0)
      expect(box.x + box.w).toBeLessThanOrEqual(viewport.width)
      expect(box.y + box.h).toBeLessThanOrEqual(viewport.height)
    }
  })

  it('steers clear of the legend', () => {
    const legend: Rect = { x: 0, y: 500, w: 260, h: 200 }
    const [box] = boxes([label('near-legend', 120, 520)], [legend])
    expect(overlaps(box, legend)).toBe(false)
  })

  it('places nothing for no labels', () => {
    expect(placeLabels([], viewport).size).toBe(0)
  })
})

describe('leaderEnd', () => {
  const box: Rect = { x: 100, y: 100, w: 50, h: 20 }

  it('meets the box at the edge nearest the anchor', () => {
    expect(leaderEnd({ x: 125, y: 200 }, box)).toEqual({ x: 125, y: 120 })
    expect(leaderEnd({ x: 0, y: 0 }, box)).toEqual({ x: 100, y: 100 })
  })

  it('draws no line when the anchor is under the label', () => {
    expect(leaderEnd({ x: 110, y: 110 }, box)).toBeNull()
  })
})

describe('layoutLabels', () => {
  // A plain projection: a degree is 100 pixels from (−90, 45) at the top left
  const project = (lng: number, lat: number) => ({ x: (lng + 90) * 100, y: (45 - lat) * 100 })
  const viewport = { width: 400, height: 300 }
  const measure = (text: string) => text.length * 7

  it('names only the points inside the view, each on its anchor', () => {
    const placed = layoutLabels(
      [
        { id: 'in', text: 'North field', lat: 44, lng: -89 },
        { id: 'out', text: 'Far away', lat: 40, lng: -80 },
      ],
      project,
      viewport,
      measure,
    )
    expect(placed.map((p) => p.id)).toEqual(['in'])
    expect(placed[0].anchor).toEqual({ x: 100, y: 100 })
    expect(placed[0].box.w).toBe('North field'.length * 7 + 16)
  })

  it(`keeps the first ${MAX_LABELS} in the reader's order`, () => {
    const many = Array.from({ length: 14 }, (_, i) => ({
      id: String(i),
      text: `Site ${i}`,
      lat: 44,
      lng: -89.5 + i * 0.1,
    }))
    const placed = layoutLabels(many, project, viewport, measure)
    expect(placed.map((p) => p.id)).toEqual(Array.from({ length: MAX_LABELS }, (_, i) => String(i)))
  })
})
