// The day-of-year calendar (`/calendar`, track 5; v1's `weather#doycal`): a date's day of the year and back, and
// the 31 × 12 table of a year's days. Pure, in UTC calendar dates, for the years the page offers (1900–2100).

export const FIRST_YEAR = 1900
export const LAST_YEAR = 2100

export const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
}

export const daysInYear = (year: number): number => (isLeapYear(year) ? 366 : 365)

/** Days in a month (1–12) */
export function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

/** The day of the year (1–366) of a date (`2026-03-01` is 60) */
export function dayOfYear(iso: string): number {
  const [year, month, day] = iso.split('-').map(Number)
  return Math.round((Date.UTC(year, month - 1, day) - Date.UTC(year, 0, 1)) / 86_400_000) + 1
}

/** The date of a day of the year, or null if the year hasn't that many days */
export function dateOfDay(year: number, day: number): string | null {
  if (!Number.isInteger(day) || day < 1 || day > daysInYear(year)) return null
  const date = new Date(Date.UTC(year, 0, day))
  return date.toISOString().slice(0, 10)
}

/** The table's rows: for each day of the month (1–31), each month's day of the year, null past the month's end */
export function calendarRows(year: number): (number | null)[][] {
  const starts = MONTHS.map((_, m) => dayOfYear(`${year}-${String(m + 1).padStart(2, '0')}-01`))
  return Array.from({ length: 31 }, (_, d) =>
    MONTHS.map((_, m) => (d + 1 <= daysInMonth(year, m + 1) ? starts[m] + d : null)),
  )
}

/** Whether the year is a leap year and what that changes, for the note under the table */
export function leapNote(year: number): string {
  return isLeapYear(year)
    ? `${year} is a leap year, with 366 days: from March 1 on, each day of the year is one more than in other years (March 1 is day 61, December 31 day 366).`
    : `${year} is not a leap year: it has 365 days (March 1 is day 60, December 31 day 365).`
}

/** "March 1, 2026" */
export function longDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return `${MONTHS[month - 1]} ${day}, ${year}`
}
