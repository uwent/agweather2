// The potato volunteer tool's answer (Phase 7 track 5, P1): whether potato tubers left in a field are likely to
// survive the winter, from the `potato-volunteer` model's run at a place. Kirk and Wharton's rule (Michigan State)
// counts the hours with soil below 27 °F from November 1 through March 31; at least 120 hours at a depth kills the
// tubers there. The model counts 2, 4 and 8 in and lowers the risk a level for each depth that reaches 120 hours,
// from Very high (none) to Low (all three): the risk falls as the winter goes on, never rises (`Risk.falls`).
//
// A winter's map appears on January 1 (the model's seasonal product); before then the page shows the place's count
// since November 1 beside last winter's map.
//
//   const winters = winterChoices(today, firstYear)       // '2026-27', '2025-26', … '2016-17'
//   const shown = mapWinter(chosen, today)                 // the map's winter for the one chosen
//   const answer = potatoAnswer({ run, today })           // the counts, the level and when each depth reached 120
//   potatoWords(answer, units, where)                     // the headline and the sentences under it
//   potatoPanels(run, units) / potatoGuides(units)        // the stacked chart's panels and its 32, 27 and 120 lines

import type { ChartGuides, ModelPanel, ModelRun } from '../charts/modelCharts'
import type { Palette } from '../charts/palette'
import { andList, monthDay } from '../models/format'
import { tableRows } from '../tableRows'
import { formatNumber, type Units } from '../units'
import type { Codec } from '../viewState'
import type { TableResponse } from '@/types/api'

/** "January 22" */
const dayText = (iso: string) => monthDay(iso.slice(5, 10))

/** Hours below 27 °F at a depth that kill the tubers there */
export const KILLING_HOURS = 120
/** The killing soil temperature, °F */
export const KILLING_F = 27
/** The first winter the archive holds whole (it starts January 1, 2016) */
export const FIRST_WINTER_YEAR = 2016

/** The depths the model counts, shallowest first, with their outputs and the soil minimum the chart draws */
export const DEPTHS = [
  { column: 'killing_hours_4cm', name: '2 in', metric: '4 cm' },
  { column: 'killing_hours_10cm', name: '4 in', metric: '10 cm' },
  { column: 'killing_hours_8in', name: '8 in', metric: '20 cm' },
] as const

/** A depth as the reader reads it: "2 in", with centimeters beside it for a metric reader */
export const depthText = (depth: (typeof DEPTHS)[number], units: Units) =>
  units.system === 'metric' ? `${depth.name} (${depth.metric})` : depth.name

// --- Winters --------------------------------------------------------------------------------------------------------

/** A winter's name, `2025-26`: November 1, 2025 through March 31, 2026 */
export type WinterName = `${number}-${number}`

export const winterName = (firstYear: number): WinterName =>
  `${firstYear}-${String((firstYear + 1) % 100).padStart(2, '0')}` as WinterName

/** The winter's first year (2025 for `2025-26`) */
export const winterYear = (name: string): number => Number(name.slice(0, 4))

/** "2025–26" */
export const winterLabel = (name: string): string => name.replace('-', '–')

/** The view's `winter=2025-26`: a winter whose second year follows its first */
export const winterCodec: Codec<string> = {
  parse(text) {
    const match = /^(\d{4})-(\d{2})$/.exec(text)
    if (!match) return undefined
    return winterName(Number(match[1])) === text ? text : undefined
  },
  format: (value) => value,
}

/** The winter a day belongs to: November on starts one, and April to October belongs to the one just past */
export function currentWinter(today: string): WinterName {
  const year = Number(today.slice(0, 4))
  return winterName(today.slice(5, 7) >= '11' ? year : year - 1)
}

/** Whether a winter's map hasn't appeared yet: November and December of its first year */
export function beforeMap(winter: string, today: string): boolean {
  return today < `${winterYear(winter) + 1}-01-01`
}

/** The winters to choose from, newest first: the current one (so far) back to 2016–17 */
export function winterChoices(today: string, firstYear = FIRST_WINTER_YEAR): WinterName[] {
  const last = winterYear(currentWinter(today))
  const choices: WinterName[] = []
  for (let y = last; y >= Math.max(firstYear, FIRST_WINTER_YEAR); y--) choices.push(winterName(y))
  return choices
}

/** The winter the map shows for the one chosen: the winter before it while its own map hasn't appeared */
export function mapWinter(chosen: string, today: string): WinterName {
  const year = winterYear(chosen)
  return winterName(beforeMap(chosen, today) ? year - 1 : year)
}

// --- The answer -----------------------------------------------------------------------------------------------------

/** The day a depth's count first reached 120 hours, and whether that day is observed or forecast */
export type Reached = { date: string; forecast: boolean }

export type DepthCount = {
  column: string
  name: string
  /** Hours below 27 °F since November 1 on the answer's day; null where missing */
  hours: number | null
  /** When the count first reached 120 hours (by the forecast, perhaps); null if it hasn't */
  reached: Reached | null
}

export type PotatoAnswer = {
  /** The winter's name and label ('2025-26', '2025–26') */
  winter: string
  label: string
  /** The winter's count is over (March 31 has passed and the day is observed) */
  final: boolean
  /** The day the answer is for: March 31 of a winter past; today (or the last day with data before it) otherwise */
  date: string | null
  /** The last day of the run (the forecast's end in a winter under way) */
  through: string | null
  depths: DepthCount[]
  /** The level that day (0 Low … 3 Very high) and its name */
  level: number | null
  levelName: string | null
}

type Season = { name?: string; label?: string; final?: boolean }

/** The answer for `today` from a run of one winter */
export function potatoAnswer({ run, season, today }: { run: ModelRun; season?: Season | null; today: string }) {
  const days = run.table.days
  const first = run.request.start ?? days[0]?.date ?? today
  const name = season?.name ?? winterName(Number(first.slice(0, 4)))
  const final = season?.final ?? today > `${winterYear(name) + 1}-03-31`
  let at = final ? days.length - 1 : days.findIndex((day) => day.date === today)
  if (at < 0) at = days.findLastIndex((day) => day.date <= today && day.kind !== 'forecast')
  const day = at >= 0 ? days[at] : null
  const depths: DepthCount[] = DEPTHS.map((depth) => {
    const k = days.findIndex((d) => (d.values[depth.column] ?? -1) >= KILLING_HOURS)
    return {
      column: depth.column,
      name: depth.name,
      hours: day?.values[depth.column] ?? null,
      reached: k < 0 ? null : { date: days[k].date, forecast: days[k].kind === 'forecast' },
    }
  })
  return {
    winter: name,
    label: season?.label ?? winterLabel(name),
    final,
    date: day?.date ?? null,
    through: days.at(-1)?.date ?? null,
    depths,
    level: at >= 0 ? (run.level[at] ?? null) : null,
    levelName: at >= 0 ? (run.label[at] ?? null) : null,
  } satisfies PotatoAnswer
}

/** The winter the run covers, from the API's `meta.summary.season` */
export function seasonOf(body: Pick<TableResponse, 'meta'>): Season | null {
  const season = (body.meta.summary as Record<string, unknown> | null)?.season
  return season && typeof season === 'object' ? (season as Season) : null
}

const hoursText = (hours: number | null) => (hours === null ? 'no data' : formatNumber(hours))

/** What the level means for the tubers, in a sentence */
function meaning(answer: PotatoAnswer, units: Units): string {
  const below = `${KILLING_HOURS} hours below ${units.format('degF', KILLING_F)}`
  const killed = answer.depths.filter((d) => d.hours !== null && d.hours >= KILLING_HOURS)
  const names = (list: DepthCount[]) => andList(list.map((d) => d.name))
  const spared = answer.depths.filter((d) => !killed.includes(d))
  const has = answer.final ? 'had' : 'has had'
  if (answer.level === null) return 'We can’t give the risk for this winter: some of the soil data are missing.'
  if (!killed.length)
    return `No depth ${has} ${below}, so tubers left in the field are likely to survive${answer.final ? '' : ' so far'}.`
  if (!spared.length)
    return `The soil ${has} at least ${below} at all three depths, so tubers left in the field are unlikely to survive.`
  return `The soil ${has} at least ${below} at ${names(killed)} but not at ${names(spared)}, so tubers ${spared.length === 1 ? 'at that depth' : 'at those depths'} may survive.`
}

/** The answer in words: the headline (the winter, the place, the counts and the survival risk) and sentences */
export function potatoWords(answer: PotatoAnswer, units: Units, where: string | null) {
  const place = where ? ` ${where}` : ''
  const sofar = answer.final ? '' : ' so far'
  const counts = answer.depths.map((d, k) => `${depthText(DEPTHS[k], units)}: ${hoursText(d.hours)}`).join('; ')
  const span = !answer.final && answer.date ? ` (November 1 to ${dayText(answer.date)})` : ''
  const headline = `Winter ${answer.label}${sofar}${place}${span}: hours of soil below ${units.format('degF', KILLING_F)} at ${counts}. Tuber survival${sofar}: ${answer.levelName ?? 'unknown'}.`
  const details = [meaning(answer, units)]
  const reached = answer.depths.filter((d) => d.reached && !d.reached.forecast)
  if (reached.length)
    details.push(
      `The count reached ${KILLING_HOURS} hours at ${andList(reached.map((d) => `${d.name} on ${dayText(d.reached!.date)}`))}.`,
    )
  const forecast = answer.depths.filter((d) => d.reached?.forecast)
  if (forecast.length)
    details.push(
      `By the forecast, it reaches ${KILLING_HOURS} hours at ${andList(forecast.map((d) => `${d.name} on ${dayText(d.reached!.date)}`))}.`,
    )
  details.push(
    answer.final
      ? 'The winter’s count ended on March 31, and its result stands until next winter’s count begins on November 1.'
      : 'Each winter starts at Very high on November 1, and the risk falls a level as each depth reaches 120 hours. It can only fall, never rise, until the count ends on March 31.',
  )
  return { headline, details }
}

// --- The chart ------------------------------------------------------------------------------------------------------

/** The run with the place's daily low air temperature beside the model's columns (from `/weather/daily`) */
export function withAir(run: ModelRun, body: Pick<TableResponse, 'meta' | 'data'> | null): ModelRun {
  if (!body) return run
  const air = tableRows(body)
  const low = new Map(air.days.map((day) => [day.date, day.values.air_temperature_min ?? null]))
  if (![...low.values()].some((v) => v !== null)) return run
  const unit = air.units.air_temperature_min
  return {
    ...run,
    table: {
      ...run.table,
      units: unit ? { ...run.table.units, air_temperature_min: unit } : run.table.units,
      days: run.table.days.map((day) => ({
        ...day,
        values: { ...day.values, air_temperature_min: low.get(day.date) ?? null },
      })),
    },
  }
}

/** Each depth's color, shallowest first */
const DEPTH_COLORS: ((p: Palette) => string)[] = [(p) => p.precipitation, (p) => p.degreeDays, (p) => p.et]

const has = (run: ModelRun, column: string) => run.table.days.some((day) => day.values[column] != null)

/** The stacked chart's panels: the risk strip, the hours below 27 °F at each depth, the soil's and the air's lows */
export function potatoPanels(run: ModelRun, units: Units): ModelPanel[] {
  const panels: ModelPanel[] = []
  if (run.level.some((level) => level !== null))
    panels.push({ kind: 'risk', key: 'risk', title: 'Chance tubers survive' })
  panels.push({
    kind: 'values',
    key: 'hours',
    title: `Hours below ${units.format('degF', KILLING_F)} since November 1`,
    bars: false,
    input: false,
    series: DEPTHS.map((depth, k) => ({
      column: depth.column,
      name: depthText(depth, units),
      color: DEPTH_COLORS[k],
    })),
  })
  const soil = [
    { column: 'soil_temperature_4cm_min', name: units.system === 'metric' ? '2 in (4 cm)' : '2 in' },
    { column: 'soil_temperature_10cm_min', name: units.system === 'metric' ? '4 in (10 cm)' : '4 in' },
    { column: 'soil_temperature_30cm_min', name: units.system === 'metric' ? '12 in (30 cm)' : '12 in' },
  ].filter((s) => has(run, s.column))
  if (soil.length)
    panels.push({
      kind: 'values',
      key: 'soil',
      title: 'Daily low soil temperature',
      bars: false,
      input: true,
      series: soil.map((s, k) => ({
        ...s,
        color: DEPTH_COLORS[k],
      })),
    })
  if (has(run, 'air_temperature_min'))
    panels.push({
      kind: 'values',
      key: 'air',
      title: 'Daily low air temperature',
      bars: false,
      input: true,
      series: [{ column: 'air_temperature_min', name: 'Air', color: (p) => p.temperature.min }],
    })
  return panels
}

/** The chart's lines: 120 hours on the hours, 32 and 27 °F on the soil's and the air's lows (values in °C, the
 * run's stored unit, as the page asks for it in metric) */
export function potatoGuides(units: Units): ChartGuides {
  const freezing = { value: 0, label: units.format('degF', 32) }
  const killing = { value: ((KILLING_F - 32) * 5) / 9, label: units.format('degF', KILLING_F) }
  return {
    values: [
      { column: DEPTHS[0].column, value: KILLING_HOURS, label: `${KILLING_HOURS} hours` },
      ...['soil_temperature_4cm_min', 'air_temperature_min'].flatMap((column) => [
        { column, ...freezing },
        { column, ...killing },
      ]),
    ],
  }
}

/** The table under the answer: each depth's hours and when it reached 120 */
export function depthRows(answer: PotatoAnswer, units: Units): { depth: string; hours: string; reached: string }[] {
  return answer.depths.map((d, k) => ({
    depth: depthText(DEPTHS[k], units),
    hours: hoursText(d.hours),
    reached: d.reached
      ? `${monthDay(d.reached.date.slice(5))}${d.reached.forecast ? ' (forecast)' : ''}`
      : answer.final
        ? 'Not reached'
        : 'Not yet',
  }))
}
