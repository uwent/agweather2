// The shared `status` prop in words: "data through" lines and the stale-data banner (docs/frontend.md, States and
// feedback). Times are on the grid's clock, Central Standard Time all year (D74), so every reader sees the same.

import type { DataStatus } from '@/types'

const CST = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Etc/GMT+6', // CST all year: no daylight saving, as the grid's days
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
})

/** "2 p.m. CST, Nov 25" for an instant */
export function cstTime(iso: string): string {
  const parts = Object.fromEntries(CST.formatToParts(new Date(iso)).map((p) => [p.type, p.value]))
  const period = parts.dayPeriod === 'AM' ? 'a.m.' : 'p.m.'
  const time =
    parts.hour === '12' && period === 'p.m.' ? 'noon' : parts.hour === '12' ? 'midnight' : `${parts.hour} ${period}`
  return `${time} CST, ${parts.month} ${parts.day}`
}

/** "Observed through 2 p.m. CST, Nov 25 · forecast to Dec 6", or null without a status */
export function dataThrough(status: DataStatus | null | undefined): string | null {
  if (!status?.observed_through) return null
  const observed = `Observed through ${cstTime(status.observed_through)}`
  if (!status.forecast_through || status.behind.includes('forecast')) return observed
  const until = new Intl.DateTimeFormat('en-US', { timeZone: 'Etc/GMT+6', month: 'short', day: 'numeric' }).format(
    // The forecast's last hour ends a day at midnight: name the day it ends
    new Date(new Date(status.forecast_through).getTime() - 1),
  )
  return `${observed} · forecast to ${until}`
}

/** The banner's sentences when data are late, or none */
export function staleMessages(status: DataStatus | null | undefined): string[] {
  if (!status) return []
  const messages: string[] = []
  if (status.behind.includes('observed')) {
    messages.push(
      status.observed_through
        ? `Weather observations are running late: the newest we have is from ${cstTime(status.observed_through)}. Maps, charts and models will update when new data arrive.`
        : 'Weather observations are not available right now. Maps, charts and models will update when data arrive.',
    )
  }
  if (status.behind.includes('forecast')) {
    const since = status.forecast_cycle ? ` since ${cstTime(status.forecast_cycle)}` : ''
    messages.push(
      status.forecast_fallback === 'openmeteo'
        ? `Our forecast hasn’t updated${since}, so forecasts inside our area come from Open-Meteo until it does.`
        : `Our forecast hasn’t updated${since}, so forecast days may be missing or out of date until it does.`,
    )
  }
  return messages
}
