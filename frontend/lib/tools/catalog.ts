// The tools the index lists (`/tools`, track 5): only those built, each with the question it answers. Add a tool here
// when its page is built (Ben, 2026-11-26: the index lists built tools only).

import { routes } from '../routes'

export type Tool = {
  title: string
  /** The question it answers, as a reader would ask it */
  question: string
  /** What it shows, in a sentence */
  text: string
  href: string
}

export const TOOLS: Tool[] = [
  {
    title: 'Degree-day calculator',
    question: 'How many growing degree days has my crop or pest had since planting or biofix?',
    text: 'Running totals at a place for up to three settings, through the forecast or a date you choose, with presets for common crops and for each insect we model.',
    href: routes.toolDegreeDays(),
  },
  {
    title: 'Day-of-year calendar',
    question: 'What day of the year is a date, and what date is a given day of the year?',
    text: 'Converts between dates and day-of-year numbers, with a printable table for any year from 1900 to 2100.',
    href: routes.calendar(),
  },
]
