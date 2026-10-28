// Dates arrive from Django as ISO strings ("2026-07-01"). They are calendar dates, not instants, so
// they're handled as UTC midnights to avoid shifting a day in the browser's time zone.

export function parseDate(iso: string): Date {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day))
}

export function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function addDays(iso: string, days: number): string {
  const date = parseDate(iso)
  date.setUTCDate(date.getUTCDate() + days)
  return isoDate(date)
}

export function daysBetween(from: string, to: string): number {
  return Math.round((parseDate(to).getTime() - parseDate(from).getTime()) / 86_400_000)
}

// Formatting a date is slow (toLocaleDateString builds a formatter each time), and grids and chart
// axes format the same few hundred dates on every update, so formatters and results are cached
const formatters = new Map<string, Intl.DateTimeFormat>()
const formatted = new Map<string, string>()

/** "Jul 1"; with year: "Jul 1, 2026"; with weekday: "Wed, Jul 1" */
export function formatDate(iso: string | null | undefined, options: { year?: boolean; weekday?: boolean } = {}) {
  if (!iso) return '—'
  const style = `${options.year ? 'y' : ''}${options.weekday ? 'w' : ''}`
  const key = `${iso.slice(0, 10)}|${style}`
  let text = formatted.get(key)
  if (text === undefined) {
    let formatter = formatters.get(style)
    if (!formatter) {
      formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: 'UTC',
        month: 'short',
        day: 'numeric',
        ...(options.year ? { year: 'numeric' } : {}),
        ...(options.weekday ? { weekday: 'short' } : {}),
      })
      formatters.set(style, formatter)
    }
    text = formatter.format(parseDate(iso))
    formatted.set(key, text)
  }
  return text
}

/** "today", "yesterday", "3 days ago" relative to today (ISO) */
export function relativeDay(iso: string, today: string): string {
  const days = daysBetween(iso, today)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days === -1) return 'tomorrow'
  return days > 0 ? `${days} days ago` : `in ${-days} days`
}

/** An instant (a server timestamp) in the browser's time zone: "Jul 1, 2026, 3:04 PM" */
export function formatTimestamp(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
