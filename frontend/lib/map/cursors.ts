// WISP 3: app/frontend/lib/map/cursors.ts (copied)
// Mouse cursors for the system picker's handles, as SVG data URLs (CSS has no cursor for turning,
// and only four angles of resize arrow). Each is drawn black with a white outline so it shows on
// imagery and streets alike, with its hotspot at the center.

const svgCursor = (body: string, fallback: string) =>
  `url("data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">${body}</svg>`,
  )}") 12 12, ${fallback}`

// The CSS fallback nearest an angle (0 = up, clockwise), for browsers without SVG cursors
const RESIZE_FALLBACKS = ['ns-resize', 'nesw-resize', 'ew-resize', 'nwse-resize']

/** A double-ended arrow along a screen angle in degrees (0 = up, clockwise), for dragging along it */
export function resizeCursor(angleDeg: number): string {
  const angle = ((Math.round(angleDeg) % 180) + 180) % 180
  const arrow = 'M12 2 L7 7 H10.5 V17 H7 L12 22 L17 17 H13.5 V7 H17 Z'
  return svgCursor(
    `<path d="${arrow}" transform="rotate(${angle} 12 12)" fill="#000" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>`,
    RESIZE_FALLBACKS[Math.round(angle / 45) % 4],
  )
}

// Circling arrows (after Lucide's refresh-cw, ISC license)
const CIRCLE_ARROWS = [
  'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8',
  'M21 3v5h-5',
  'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16',
  'M8 16H3v5',
]
  .map((d) => `<path d="${d}"/>`)
  .join('')

/** Circling arrows, for dragging around a center */
export const ROTATE_CURSOR = svgCursor(
  `<g fill="none" stroke-linecap="round" stroke-linejoin="round" transform="translate(2.4 2.4) scale(0.8)">` +
    `<g stroke="#fff" stroke-width="5">${CIRCLE_ARROWS}</g><g stroke="#000" stroke-width="2.2">${CIRCLE_ARROWS}</g></g>`,
  'grab',
)
