// WISP 3: app/frontend/lib/charts/totals.ts (copied)
import type { ChartView } from './echarts'

/** A running total of value over the days in view, null outside them and on days without a value */
export function runningTotal<T>(days: T[], value: (day: T) => number | null, view: ChartView): (number | null)[] {
  let total = 0
  return days.map((day, i) => {
    if (i < view.start || i > view.end) return null
    const amount = value(day)
    if (amount === null) return null
    total += amount
    return Number(total.toFixed(2))
  })
}
