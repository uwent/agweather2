// The map explorer's dates, hours and notes in words (CLAUDE.md, Writing for the public): dates as "Nov 25,
// 2026", hours in Central Standard Time all year as the grid's days are (D74), "2 p.m. CST".

import { formatDate } from '@/lib/dates'
import type { LayerInfo } from '@/types/api'

/** "Nov 25, 2026" */
export const formatDay = (iso: string) => formatDate(iso.slice(0, 10), { year: true })

/** An hour in UTC (`2026-11-25T20`, or with `:00Z`) as Central Standard Time: "2 p.m. CST, Nov 25, 2026" */
export function formatHour(hour: string, withDate = true): string {
  const at = new Date(`${hour.slice(0, 13)}:00:00Z`)
  at.setUTCHours(at.getUTCHours() - 6)
  const h = at.getUTCHours()
  const clock = h === 0 ? 'midnight' : h === 12 ? 'noon' : `${h % 12} ${h < 12 ? 'a.m.' : 'p.m.'}`
  const time = `${clock} CST`
  return withDate ? `${time}, ${formatDay(at.toISOString())}` : time
}

/** The layer's newest data in words: "Observed through Nov 24, 2026 · forecast to Dec 6, 2026" */
export function dataThrough(layer: Pick<LayerInfo, 'range' | 'time_axis'>): string | null {
  const { last, forecast_through } = layer.range
  if (!last) return null
  const when = (iso: string) => (layer.time_axis === 'hour' ? formatHour(iso) : formatDay(iso))
  const observed = `Observed through ${when(last)}`
  return forecast_through ? `${observed} · forecast to ${when(forecast_through)}` : observed
}

/** What a layer's maps can show, for the date control: "You can map any day from Jan 1, 2016 to Dec 6, 2026. Days
 * through Nov 24, 2026 are observed; later days are a forecast." */
export function availableWords(layer: Pick<LayerInfo, 'range' | 'time_axis'>): string | null {
  const { first, last, forecast_through } = layer.range
  if (!first || !last) return null
  const hourly = layer.time_axis === 'hour'
  const when = (iso: string) => (hourly ? formatHour(iso) : formatDay(iso))
  const unit = hourly ? 'hour' : 'day'
  const reach = `You can map any ${unit} from ${when(first)} to ${when(forecast_through ?? last)}.`
  if (!forecast_through || forecast_through <= last) return `${reach} All of them are observed.`
  return `${reach} ${hourly ? 'Hours' : 'Days'} through ${when(last)} are observed; later ${unit}s are a forecast.`
}

/** The forecast's boundary on the date control: "Observed through Nov 24", "Observed through Nov 25, 2 p.m. CST" */
export function observedLabel(layer: Pick<LayerInfo, 'range' | 'time_axis'>): string | null {
  const last = layer.range.last
  if (!last) return null
  if (layer.time_axis !== 'hour') return `Observed through ${formatDate(last.slice(0, 10))}`
  const at = new Date(`${last.slice(0, 13)}:00:00Z`)
  at.setUTCHours(at.getUTCHours() - 6)
  return `Observed through ${formatDate(at.toISOString())}, ${formatHour(last, false)}`
}

/** What the map's time is in words: "Nov 25, 2026", "Jul 1 to Jul 14, 2026 (total)", "Jan 1 to Jul 8, 2026" */
export function timeWords(time: string, stat: string | null, latest: string | null, hourly: boolean): string {
  if (time === 'latest') {
    if (!latest) return 'Latest'
    return hourly ? formatHour(latest) : formatDay(latest)
  }
  const range = /^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$/.exec(time)
  if (range) {
    const [, start, end] = range
    const sameYear = start.slice(0, 4) === end.slice(0, 4)
    const from = formatDate(start, { year: !sameYear })
    const statWord = { sum: 'total', mean: 'average', min: 'lowest', max: 'highest' }[stat ?? ''] ?? stat
    return `${from} to ${formatDay(end)}${statWord ? ` (${statWord})` : ''}`
  }
  return time.length > 10 ? formatHour(time) : formatDay(time)
}
