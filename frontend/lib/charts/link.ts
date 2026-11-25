// WISP 3: app/frontend/lib/charts/link.ts (copied)
// Charts that zoom together (the weather panels and their season slider): each one zoomed by the
// user passes its range, in percent of the x axis, to the rest of its group. They share the same
// days, so the same percentages are the same dates. Only the zoom is shared, not the tooltip.

export type Zoom = { start: number; end: number }

export type LinkedChart = {
  /** Show this range (from another chart in the group) */
  zoom: (zoom: Zoom) => void
  /** Back to the range it opened with */
  reset: () => void
}

const groups = new Map<string, Set<LinkedChart>>()

/** Add a chart to a group; returns the function that takes it out */
export function join(group: string, chart: LinkedChart): () => void {
  const members = groups.get(group) ?? new Set()
  members.add(chart)
  groups.set(group, members)
  return () => {
    members.delete(chart)
    if (!members.size) groups.delete(group)
  }
}

/** Tell the rest of the group about a chart's new range */
export function share(group: string, from: LinkedChart, zoom: Zoom) {
  for (const chart of groups.get(group) ?? []) if (chart !== from) chart.zoom(zoom)
}

/** Put every chart in the group back to its opening range */
export function resetGroup(group: string) {
  for (const chart of groups.get(group) ?? []) chart.reset()
}
