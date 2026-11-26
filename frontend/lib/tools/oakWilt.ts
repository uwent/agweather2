// The oak wilt tool's answer (Phase 7 track 5, T1 d): Wisconsin DNR's restricted period for pruning, wounding and
// harvesting oaks, read from the `oak-wilt-vectors` model's run at a place. DNR's Oak Harvesting Guidelines restrict
// harvesting from April 1 (south zone) or April 15 (north zone) through July 15; its degree-day tool, built with
// UW–Madison on Jagemann et al. 2018, starts the period instead when 231 degree days (°F, base 41 °F, from January
// 1) have built up, the point at which 5% of the beetle Colopterus truncatus has flown. The model's own level
// (VDIFN's, Moderate from 231) is shown beside the answer, not in place of it.
//
//   const answer = oakWiltAnswer({ run, today, year })   // the phase, the dates and the numbers, from a ModelRun
//   oakWiltWords(answer, units)                         // the headline and the sentences under it

import type { ModelRun } from '../charts/modelCharts'
import { monthDay } from '../models/format'
import { convert, formatNumber, type Units } from '../units'

/** DNR's degree-day start of the restricted period, °F·d (base 41 °F from January 1) */
export const RESTRICTED_DD_F = 231

/** DNR's calendar periods: its guidelines' restricted periods for harvesting where oak wilt is near */
export const DNR_PERIODS = [
  { zone: 'North zone', start: '04-15', end: '07-15' },
  { zone: 'South zone', start: '04-01', end: '07-15' },
] as const

/** The last day of the restricted period, every year */
export const END = '07-15'

export const DNR_LINKS = {
  guidelines:
    'https://embed.widencdn.net/pdf/download/widnr/aqszuho7ee/Oak-Harvesting-Guidelines-Web-version.pdf?u=lhzbht&showinbrowser=true',
  oakWilt: 'https://dnr.wisconsin.gov/topic/foresthealth/oakwilt',
  harvestingMap: 'https://dnr.wisconsin.gov/topic/foresthealth/oakwilt/harvestingmap',
  degreeDayGuide: 'https://dnr.wisconsin.gov/topic/foresthealth/oakwiltvectorsguide',
} as const

/**
 * winter: before March, when the beetles don't fly and degree days have hardly begun;
 * before: degree days haven't reached 231 yet (March to July 15);
 * restricted: 231 reached, through July 15;
 * after: after July 15;
 * past: a past season, summarized.
 */
export type Phase = 'winter' | 'before' | 'restricted' | 'after' | 'past'

/** The day a total first reached a value, and whether that day is observed, forecast or projected */
export type Reached = { date: string; kind: 'observed' | 'forecast' | 'projection' }

export type OakWiltAnswer = {
  phase: Phase
  year: number
  /** The day the answer is for: today's row (or the run's last observed day) this year, July 15 for a past year */
  date: string | null
  /** Degree days since January 1 on that day, °F·d */
  ddF: number | null
  /** When the degree days reached 231 (on or before July 15), or null */
  start: Reached | null
  /** The model's level that day (0 the lowest) and its name */
  level: number | null
  label: string | null
  /** At least this share (%) of C. truncatus has flown (the model's `flown`, 0.3); null when the run hasn't it */
  flown: number | null
  /** The last day the run reaches (the forecast's end, or the projection's) */
  through: string | null
}

const kindOf = (kind: string): Reached['kind'] =>
  kind === 'projection' ? 'projection' : kind === 'forecast' || kind === 'partial' ? 'forecast' : 'observed'

/** The run's degree days since January 1 in °F·d, a value a day (null where missing) */
export function degreeDaysF(run: ModelRun): (number | null)[] {
  const unit = run.table.units.dd_total ?? 'degF_day'
  return run.table.days.map((day) => convert(day.values.dd_total ?? null, unit, 'degF_day'))
}

/** When the season's degree days first reached `threshold` °F·d on or before July 15, or null */
export function reached(run: ModelRun, year: number, threshold = RESTRICTED_DD_F): Reached | null {
  const dd = degreeDaysF(run)
  const end = `${year}-${END}`
  const k = run.table.days.findIndex((day, i) => day.date <= end && dd[i] !== null && dd[i]! >= threshold)
  return k < 0 ? null : { date: run.table.days[k].date, kind: kindOf(run.table.days[k].kind) }
}

/** The answer for `today` in `year` (this year's run), or the summary of a past season */
export function oakWiltAnswer({ run, today, year }: { run: ModelRun; today: string; year: number }): OakWiltAnswer {
  const days = run.table.days
  const dd = degreeDaysF(run)
  const thisYear = Number(today.slice(0, 4))
  const past = year < thisYear
  // The day the answer is for: July 15 of a past season; today this year, or the last day with weather before it
  let at = past
    ? days.findLastIndex((day) => day.date <= `${year}-${END}`)
    : days.findIndex((day) => day.date === today)
  if (!past && at < 0) at = days.findLastIndex((day) => day.date <= today && day.kind !== 'projection')
  const day = at >= 0 ? days[at] : null
  const start = reached(run, year)
  const ddF = at >= 0 ? dd[at] : null
  const date = day?.date ?? null
  let phase: Phase
  if (past) phase = 'past'
  else if (today > `${year}-${END}`) phase = 'after'
  else if (ddF !== null && ddF >= RESTRICTED_DD_F) phase = 'restricted'
  else if (today < `${year}-03-01`) phase = 'winter'
  else phase = 'before'
  const known = days.filter((d) => d.kind !== 'projection' || d.values.dd_total != null)
  return {
    phase,
    year,
    date,
    ddF,
    start,
    level: day ? (run.level[at] ?? null) : null,
    label: day ? (run.label[at] ?? null) : null,
    flown: day ? (day.values.flown ?? null) : null,
    through: known.at(-1)?.date ?? null,
  }
}

/** "231 °F·d" in the reader's units ("128 °C·d") */
export function degreeDaysText(valueF: number, units: Units): string {
  return units.format('degF_day', valueF)
}

/** "April 16" */
const dayText = (iso: string) => monthDay(iso.slice(5, 10))

const when = (r: Reached) =>
  r.kind === 'projection'
    ? `around ${dayText(r.date)}, judging by past years’ weather after the forecast`
    : r.kind === 'forecast'
      ? `on ${dayText(r.date)}, by the forecast`
      : `on ${dayText(r.date)}`

/** The answer in words: a headline in DNR's terms and the sentences under it */
export function oakWiltWords(answer: OakWiltAnswer, units: Units): { headline: string; details: string[] } {
  const threshold = degreeDaysText(RESTRICTED_DD_F, units)
  const sofar = answer.ddF === null ? null : `${degreeDaysText(answer.ddF, units)} since January 1 (base 41 °F, 5 °C)`
  const details: string[] = []
  switch (answer.phase) {
    case 'restricted':
      details.push(
        `Degree days here reached ${threshold} ${answer.start ? when(answer.start) : 'earlier this year'}, which starts Wisconsin’s restricted period for oaks. It runs through July 15.`,
      )
      if (sofar) details.push(`Degree days so far: ${sofar}.`)
      return { headline: 'Avoid pruning, wounding or harvesting oaks.', details }
    case 'before':
      if (sofar) details.push(`Degree days so far: ${sofar}. The restricted period starts at ${threshold}.`)
      if (answer.start) details.push(`Degree days are expected to reach ${threshold} ${when(answer.start)}.`)
      else if (answer.through) details.push(`They aren’t expected to reach ${threshold} by ${dayText(answer.through)}.`)
      if (answer.date && answer.date.slice(5) >= DNR_PERIODS[1].start)
        details.push(
          `Wisconsin’s calendar restricted period began on ${answer.date.slice(5) >= DNR_PERIODS[0].start ? 'April 1 in the south zone and April 15 in the north zone' : 'April 1 in the south zone, and in the north zone it begins on April 15'}. In a cold spring, DNR’s guidelines leave harvesting in April to the landowner’s judgement. Wounds and stumps can be infected for up to 72 hours after cutting.`,
        )
      return { headline: 'The beetles that spread oak wilt are not yet flying in numbers.', details }
    case 'winter':
      details.push(
        `Degree days count from January 1 and seldom build up before March. The restricted period starts when they reach ${threshold}, usually in April.`,
      )
      if (sofar) details.push(`Degree days so far: ${sofar}.`)
      return { headline: 'The beetles that spread oak wilt are not flying now.', details }
    case 'after':
      details.push(
        answer.start
          ? `This year the restricted period began here ${when(answer.start)} and ended on July 15.`
          : `This year degree days here didn’t reach ${threshold} before July 15.`,
      )
      details.push(
        'Few beetles carry the fungus after mid-July. The best time to prune oaks is the dormant season, from November through March.',
      )
      return { headline: 'Wisconsin’s restricted period for oaks ended on July 15.', details }
    case 'past':
      return {
        headline: answer.start
          ? `In ${answer.year} the restricted period began here on ${dayText(answer.start.date)}.`
          : `In ${answer.year} degree days here didn’t reach ${threshold} before July 15.`,
        details: answer.start
          ? [
              `That is when degree days reached ${threshold}. The period ended on July 15${answer.ddF === null ? '' : `, with ${degreeDaysText(answer.ddF, units)} since January 1`}.`,
            ]
          : [],
      }
  }
}

/** "At least 25% of Colopterus truncatus, the main early-season beetle, have flown" (null without the share) */
export function flownWords(flown: number | null): string | null {
  if (flown === null) return null
  if (flown < 5)
    return 'Fewer than 5% of the season’s Colopterus truncatus beetles, the main carrier in spring, have flown.'
  return `At least ${formatNumber(flown)}% of the season’s Colopterus truncatus beetles, the main carrier in spring, have flown.`
}

/** "April 1 to July 15" */
export function periodText(period: { start: string; end: string }): string {
  return `${monthDay(period.start)} to ${monthDay(period.end)}`
}

/** The date the map shows by default: today in season (March through July), else April 15 of the latest season */
export function defaultMapDate(today: string): string {
  const year = Number(today.slice(0, 4))
  const month = today.slice(5, 7)
  if (month >= '03' && month <= '07') return today
  return month < '03' ? `${year - 1}-04-15` : `${year}-04-15`
}
