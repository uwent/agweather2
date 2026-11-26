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
    title: 'Freeze dates and odds',
    question: 'When did the last spring freeze or the first fall freeze come this year, and when do they usually come?',
    text: 'This year’s or a past year’s freeze dates at a place beside the typical dates over the last 30, 10 or 5 years, the season’s length, and the chance of a freeze after or by any date, for 32, 28 and 24 °F, a crop’s killing freeze or your own temperature.',
    href: routes.toolFreeze(),
  },
  {
    title: 'Crop GDD outlook',
    question: 'When will my crop reach maturity, and how likely is a fall freeze before then?',
    text: 'Growing degree days since planting at a place for corn hybrids and other crops, with the likely dates of each stage from past years’ weather, the normal year, up to three past years and the chance of a fall freeze.',
    href: routes.toolCropGdd(),
  },
  {
    title: 'Oak wilt',
    question: 'Has Wisconsin’s restricted period for pruning, wounding and harvesting oaks begun where I am?',
    text: 'Degree days since January 1 against the DNR’s 231 degree-day start, through July 15, with the oak wilt vector model’s level, its map and season chart, and the DNR’s calendar periods.',
    href: routes.toolOakWilt(),
  },
  {
    title: 'Day-of-year calendar',
    question: 'What day of the year is a date, and what date is a given day of the year?',
    text: 'Converts between dates and day-of-year numbers, with a printable table for any year from 1900 to 2100.',
    href: routes.calendar(),
  },
]
