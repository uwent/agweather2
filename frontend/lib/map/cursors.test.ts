// WISP 3: app/frontend/lib/map/cursors.test.ts (copied)
import { describe, expect, it } from 'vitest'

import { resizeCursor, ROTATE_CURSOR } from './cursors'

const svg = (cursor: string) => decodeURIComponent(cursor.match(/data:image\/svg\+xml,([^"]+)"/)![1])

describe('cursors', () => {
  it('turns the resize arrow to the drag, either way along it', () => {
    expect(svg(resizeCursor(30))).toContain('rotate(30 12 12)')
    expect(svg(resizeCursor(210))).toContain('rotate(30 12 12)')
    expect(svg(resizeCursor(-30))).toContain('rotate(150 12 12)')
  })

  it('falls back to the nearest built-in resize cursor', () => {
    expect(resizeCursor(0)).toMatch(/12 12, ns-resize$/)
    expect(resizeCursor(50)).toMatch(/, nesw-resize$/)
    expect(resizeCursor(95)).toMatch(/, ew-resize$/)
    expect(resizeCursor(130)).toMatch(/, nwse-resize$/)
    expect(resizeCursor(175)).toMatch(/, ns-resize$/)
  })

  it('has a turning cursor that falls back to grab', () => {
    expect(svg(ROTATE_CURSOR)).toContain('<svg')
    expect(ROTATE_CURSOR).toMatch(/, grab$/)
  })
})
