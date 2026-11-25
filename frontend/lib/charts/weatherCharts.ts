// WISP 3: app/frontend/lib/charts/weatherCharts.ts (adapted: panels over the API's catalog columns, in the units
// the answer gives and converted at display; kinds from ./kinds; hourly rows as well as days)
//
// A site's weather as small multiples (frontend.md, Charts): one panel per measure, each its own chart with its
// own scale, all on one time axis and zooming together, never two units on one axis. A panel may have a second
// grid below its first, for a running total (precipitation) or a related measure in another unit (dew point
// under humidity, reference ET under sunlight). Thresholds are labelled reference lines; the forecast is shaded
// and labelled; estimated values are hollow; missing values are gaps.
//
//   const panels = shownPanels(weatherPanels({ hourly: false }), table)
//   build = (palette, view) => panelOption(panels[0], table, { units, palette, today, roll: 7, view })
//   panelSummary(panels[0], table, units)  // the chart in words: its text alternative and summary
//   panelTable(panels[0], table, units)    // "Summary and data"'s table, newest first

import type { CsvValue } from '../csv'
import type { Day, Table } from '../tableRows'
import type { Units } from '../units'
import type { ChartView, EChartsCoreOption } from './echarts'
import { bar, forecastBand, isForecast, point, rowLabel, thresholdLine, todayLine } from './kinds'
import { baseOption, type Palette } from './palette'
import { runningTotal } from './totals'

export type Measure = {
  /** The API's column (`air_temperature_max`, or `air_temperature` hourly) */
  column: string
  name: string
  color: (palette: Palette) => string
  /** Drawn dashed: a mean beside a high and low */
  dashed?: boolean
}

export type WeatherPanel = {
  key: string
  title: string
  /** What the panel shows and why it matters, for its card's (i) */
  info: (units: Units) => string
  series: Measure[]
  /** Daily amounts (rain, sunlight) as bars rather than lines */
  bars?: boolean
  /** A running total of the first series over the days in view, in a grid below */
  totals?: boolean
  /** A related measure in its own unit, in a grid below */
  below?: { title: string; series: Measure[]; bars?: boolean }
  /** Reference lines, each in the stored unit of the panel's first column (`unit`, a symbol) */
  thresholds?: { value: number; unit: string; name: (units: Units) => string }[]
}

const SOIL_DEPTHS = [
  ['4cm', '2 inches', '4 cm'],
  ['10cm', '4 inches', '10 cm'],
  ['30cm', '12 inches', '30 cm'],
] as const

const MOISTURE_LAYERS = [
  ['0_to_7cm', '0–3 inches', '0–7 cm'],
  ['7_to_28cm', '3–11 inches', '7–28 cm'],
  ['28_to_100cm', '11–39 inches', '28–100 cm'],
] as const

/** The weather panels, daily or hourly, most looked at first */
export function weatherPanels({ hourly }: { hourly: boolean }): WeatherPanel[] {
  const column = (daily: string, hour: string) => (hourly ? hour : daily)
  const depthColors = [
    (p: Palette) => p.temperature.max,
    (p: Palette) => p.temperature.mean,
    (p: Palette) => p.temperature.min,
  ]
  const layerColors = [(p: Palette) => p.precipitation, (p: Palette) => p.degreeDays, (p: Palette) => p.projection]
  const freezing = { value: 0, unit: 'degC', name: (units: Units) => `Freezing (${units.format('degC', 0)})` }

  return [
    {
      key: 'temperature',
      title: 'Air temperature',
      info: (units) =>
        hourly
          ? `Air temperature each hour, 2 m (6.5 ft) above the ground. The dashed line marks freezing, ${units.format('degC', 0)}.`
          : `Each day's high, low and mean air temperature, 2 m (6.5 ft) above the ground. The dashed line marks freezing, ${units.format('degC', 0)}: lows near it risk frost.`,
      series: hourly
        ? [{ column: 'air_temperature', name: 'Temperature', color: (p) => p.temperature.mean }]
        : [
            { column: 'air_temperature_max', name: 'High', color: (p) => p.temperature.max },
            { column: 'air_temperature_min', name: 'Low', color: (p) => p.temperature.min },
            { column: 'air_temperature_mean', name: 'Mean', color: (p) => p.temperature.mean, dashed: true },
          ],
      thresholds: [freezing],
    },
    {
      key: 'precipitation',
      title: 'Precipitation',
      info: () =>
        `Rain and the water in melted snow, ${hourly ? 'each hour' : 'each day'}. The lower panel adds it up from the first ${hourly ? 'hour' : 'day'} in view, so zooming changes the total. A missing value is counted as no rain in the total; we never estimate precipitation.`,
      bars: true,
      totals: true,
      series: [
        { column: column('precipitation_sum', 'precipitation'), name: 'Precipitation', color: (p) => p.precipitation },
      ],
    },
    {
      key: 'humidity',
      title: 'Humidity and dew point',
      info: () =>
        hourly
          ? 'Relative humidity each hour, and below it the dew point: the temperature at which dew forms. Long humid spells favor leaf diseases such as late blight and white mold.'
          : "Each day's mean and lowest relative humidity, and below them the day's mean dew point: the temperature at which dew forms. Long humid spells favor leaf diseases such as late blight and white mold.",
      series: hourly
        ? [{ column: 'relative_humidity', name: 'Relative humidity', color: (p) => p.precipitation }]
        : [
            { column: 'relative_humidity_mean', name: 'Mean humidity', color: (p) => p.precipitation },
            { column: 'relative_humidity_min', name: 'Lowest humidity', color: (p) => p.degreeDays },
          ],
      below: {
        title: 'Dew point',
        series: [{ column: column('dew_point_mean', 'dew_point'), name: 'Dew point', color: (p) => p.temperature.min }],
      },
    },
    {
      key: 'wind',
      title: 'Wind',
      info: (units) =>
        `${hourly ? 'Wind speed each hour' : "Each day's mean wind speed"} and the highest gust, 10 m (33 ft) above the ground. Many pesticide labels restrict spraying above ${units.format('mph', 10)}.`,
      series: [
        {
          column: column('wind_speed_mean', 'wind_speed'),
          name: hourly ? 'Speed' : 'Mean speed',
          color: (p) => p.precipitation,
        },
        { column: column('wind_gust_max', 'wind_gust'), name: 'Highest gust', color: (p) => p.temperature.max },
      ],
    },
    {
      key: 'sun',
      title: 'Sunlight and evapotranspiration',
      info: () =>
        hourly
          ? 'Sunlight reaching the ground each hour, and below it reference evapotranspiration (ET0): the water a well-watered grass would use.'
          : 'The sunlight reaching the ground over each day, the main driver of crop water use, and below it reference evapotranspiration (ET0): the water a well-watered grass would use, from the FAO-56 Penman–Monteith equation.',
      bars: !hourly,
      series: [
        { column: column('shortwave_radiation_sum', 'shortwave_radiation'), name: 'Sunlight', color: (p) => p.et },
      ],
      below: {
        title: 'Reference ET',
        bars: !hourly,
        series: [{ column: column('et0_sum', 'et0'), name: 'Reference ET', color: (p) => p.degreeDays }],
      },
    },
    {
      key: 'soil_temperature',
      title: 'Soil temperature',
      info: (units) =>
        `Modeled soil temperature at three depths${hourly ? '' : ', averaged over each day'}. About ${units.format('degF', 50)} at seed depth is a common threshold for planting corn and soybeans.`,
      series: SOIL_DEPTHS.map(([depth, us, metric], i) => ({
        column: column(`soil_temperature_${depth}_mean`, `soil_temperature_${depth}`),
        name: `${us} (${metric})`,
        color: depthColors[i],
      })),
    },
    {
      key: 'soil_moisture',
      title: 'Soil moisture',
      info: () =>
        'Modeled water in the soil at three depths, as a share of its volume (ECMWF). It is not a measurement in your field and knows nothing of irrigation.',
      series: MOISTURE_LAYERS.map(([layer, us, metric], i) => ({
        column: column(`soil_moisture_${layer}_mean`, `soil_moisture_${layer}`),
        name: `${us} (${metric})`,
        color: layerColors[i],
      })),
    },
  ]
}

/** Every column a set of panels reads, to ask the API for (`vars=`) */
export function panelColumns(panels: WeatherPanel[]): string[] {
  return [...new Set(panels.flatMap((panel) => allMeasures(panel).map((measure) => measure.column)))]
}

const allMeasures = (panel: WeatherPanel) => [...panel.series, ...(panel.below?.series ?? [])]

/** The panels with something to show: a column with a value on some row */
export function shownPanels(panels: WeatherPanel[], table: Table): WeatherPanel[] {
  return panels.filter((panel) =>
    allMeasures(panel).some((measure) => table.days.some((day) => day.values[measure.column] != null)),
  )
}

/** A column's value on a row, in the reader's units */
function shown(table: Table, units: Units, column: string, day: Day): number | null {
  const value = day.values[column] ?? null
  const symbol = table.units[column]
  return symbol ? units.toDisplay(symbol, value) : value
}

/** A column's unit label in the reader's units ('' for a unitless one) */
export function unitLabel(table: Table, units: Units, column: string): string {
  const symbol = table.units[column]
  return symbol ? units.label(symbol) : ''
}

/** Decimals for a column's values: the unit's in the reader's system */
function digitsOf(table: Table, units: Units, column: string): number {
  const symbol = table.units[column]
  return symbol ? units.digits(symbol) : 1
}

/** The rolled column for a measure (`air_temperature_max_7d`), when the table has it */
function rolledColumn(table: Table, measure: Measure, roll: number | null | undefined): string | null {
  if (!roll) return null
  const name = `${measure.column}_${roll}d`
  return table.days.some((day) => name in day.values) ? name : null
}

const rolledName = (measure: Measure, roll: number, bars: boolean) =>
  `${measure.name}, ${roll}-day ${bars ? 'total' : 'mean'}`

export type PanelOptions = {
  units: Units
  palette: Palette
  /** The grid's today (ISO date), for the dashed Today line */
  today: string
  /** A smoothing window (days) whose `_Nd` columns the table holds: drawn over the values, which fade */
  roll?: number | null
  /** The rows in view once zoomed (the running total starts at the first) */
  view?: ChartView
}

/** The ECharts option for one panel */
export function panelOption(panel: WeatherPanel, table: Table, options: PanelOptions): EChartsCoreOption {
  const { units, palette, today, roll } = options
  const days = table.days
  const view = options.view ?? { start: 0, end: days.length - 1 }
  const base = baseOption(palette)
  const dates = days.map((day) => day.date)
  const timeZone = table.location?.timezone ?? undefined
  const lower = panel.totals ? panel.series.slice(0, 1) : (panel.below?.series ?? [])
  const lowerBars = panel.totals ? false : !!panel.below?.bars
  const gridCount = lower.length ? 2 : 1

  const upperSeries = panel.series.filter((measure) => days.some((day) => day.values[measure.column] != null))
  const lowerSeries = lower.filter((measure) => days.some((day) => day.values[measure.column] != null))

  const { shading, label: forecastLabel } = forecastBand({
    dates,
    days,
    grids: gridCount,
    axisOffset: gridCount,
    palette,
  })
  const firstColumn = panel.series[0].column
  const marks = [
    // Hourly, the line is now: the latest observed hour
    ...todayLine(dates, table.hourly ? (days.findLast((day) => day.kind === 'observed')?.date ?? '') : today, palette),
    ...(panel.thresholds ?? []).map((line) =>
      thresholdLine(units.toDisplay(line.unit, line.value) ?? line.value, line.name(units), palette),
    ),
  ]

  const rounded = (value: number | null) => (value === null ? null : Number(value.toFixed(3)))
  const smoothing = (measure: Measure) => rolledColumn(table, measure, roll)
  const faded = upperSeries.some((measure) => smoothing(measure))

  function drawn(measure: Measure, grid: 0 | 1, bars: boolean) {
    const color = measure.color(palette)
    const data = days.map((day) => {
      const value = rounded(shown(table, units, measure.column, day))
      const estimated = day.estimated.has(measure.column)
      return bars ? bar(value, estimated, color, palette) : point(value, estimated, palette)
    })
    const fade = grid === 0 && faded ? 0.35 : 1
    return {
      id: `${grid}-${measure.column}`,
      name: measure.name,
      xAxisIndex: grid,
      yAxisIndex: grid,
      data,
      itemStyle: { color, opacity: fade },
      ...(bars
        ? { type: 'bar', barMaxWidth: 10 }
        : {
            type: 'line',
            symbol: 'circle',
            showSymbol: false,
            symbolSize: 4,
            connectNulls: false,
            lineStyle: { width: 2, color, type: measure.dashed ? 'dashed' : 'solid', opacity: fade },
          }),
    }
  }

  const upper = upperSeries.map((measure) => drawn(measure, 0, !!panel.bars))
  const rolled = upperSeries.flatMap((measure) => {
    const column = smoothing(measure)
    if (!column) return []
    const color = measure.color(palette)
    return [
      {
        id: `roll-${measure.column}`,
        name: rolledName(measure, roll!, !!panel.bars),
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: days.map((day) => rounded(shown(table, units, column, day))),
        symbol: 'none',
        connectNulls: false,
        lineStyle: { width: 2.5, color, type: measure.dashed ? 'dashed' : 'solid' },
        itemStyle: { color },
      },
    ]
  })
  if (upper[0]) {
    Object.assign(upper[0], {
      markLine: marks.length ? { silent: true, symbol: 'none', data: marks } : undefined,
      markArea: forecastLabel,
    })
  }

  const below = lowerSeries.map((measure) => {
    if (!panel.totals) return drawn(measure, 1, lowerBars)
    const color = measure.color(palette)
    return {
      id: `total-${measure.column}`,
      name: `${measure.name} total`,
      type: 'line',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: runningTotal(days, (day) => shown(table, units, measure.column, day) ?? 0, view),
      symbol: 'none',
      lineStyle: { width: 2, color },
      itemStyle: { color },
    }
  })

  const legendNames = [...upper, ...rolled, ...below].map((series) => series.name)
  const legendShown = legendNames.length > 1
  const top = legendShown ? 32 : 14
  const axisLabel = {
    ...base.axisLabel,
    formatter: (date: string) => rowLabel(date, timeZone, { short: true }),
  }
  const upperUnit = unitLabel(table, units, upperSeries[0]?.column ?? firstColumn)
  const lowerUnit = lowerSeries[0] ? unitLabel(table, units, lowerSeries[0].column) : ''

  const grids = lower.length
    ? [
        { left: 44, right: 16, top, height: '44%' },
        { left: 44, right: 16, top: '72%', bottom: 24 },
      ]
    : [{ left: 44, right: 16, top, bottom: 24 }]

  const formats = new Map<string, { unit: string; digits: number }>()
  for (const measure of upperSeries) {
    const format = { unit: upperUnit, digits: digitsOf(table, units, measure.column) }
    formats.set(measure.name, format)
    formats.set(rolledName(measure, roll ?? 0, !!panel.bars), format)
  }
  for (const measure of lowerSeries) {
    const format = { unit: lowerUnit, digits: digitsOf(table, units, measure.column) }
    formats.set(panel.totals ? `${measure.name} total` : measure.name, format)
  }
  const estimatedOn = (index: number, name: string) => {
    const measure = allMeasures(panel).find((m) => m.name === name)
    return !!measure && !!days[index]?.estimated.has(measure.column)
  }

  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: legendShown
      ? {
          type: 'scroll',
          top: 0,
          left: 0,
          right: 0,
          data: legendNames,
          textStyle: { color: palette.ink, fontSize: 11 },
          itemWidth: 14,
        }
      : undefined,
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => tooltip(params, { formats, timeZone, days, estimatedOn }),
    },
    axisPointer: lower.length ? { link: [{ xAxisIndex: 'all' }] } : undefined,
    grid: grids,
    xAxis: [
      ...(lower.length
        ? [
            {
              type: 'category',
              data: dates,
              gridIndex: 0,
              axisLabel: { show: false },
              axisLine: base.axisLine,
              axisTick: { show: false },
            },
            { type: 'category', data: dates, gridIndex: 1, axisLabel, axisLine: base.axisLine },
          ]
        : [{ type: 'category', data: dates, axisLabel, axisLine: base.axisLine }]),
      ...shading.xAxis,
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        scale: !panel.bars,
        min: panel.bars ? 0 : undefined,
        name: upperUnit,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        splitNumber: lower.length ? 3 : 4,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...(lower.length
        ? [
            {
              type: 'value',
              gridIndex: 1,
              scale: !panel.totals && !lowerBars,
              min: panel.totals || lowerBars ? 0 : undefined,
              splitNumber: 2,
              name: `${panel.totals ? 'Total in view' : panel.below!.title}${lowerUnit ? ` (${lowerUnit})` : ''}`,
              nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
              nameGap: 6,
              axisLabel: base.axisLabel,
              splitLine: base.splitLine,
            },
          ]
        : []),
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [...(lower.length ? [0, 1] : [0]), ...shading.xAxisIndexes] }],
    series: [...upper, ...rolled, ...below, ...shading.series],
  }
}

type TooltipParam = { dataIndex: number; seriesIndex: number; seriesName: string; marker: string; value: unknown }

function tooltip(
  params: unknown,
  {
    formats,
    timeZone,
    days,
    estimatedOn,
  }: {
    formats: Map<string, { unit: string; digits: number }>
    timeZone?: string
    days: Day[]
    estimatedOn: (index: number, name: string) => boolean
  },
): string {
  const all = ((Array.isArray(params) ? params : [params]) as TooltipParam[])
    .filter((param) => formats.has(param.seriesName))
    .toSorted((a, b) => a.seriesIndex - b.seriesIndex)
  if (!all.length) return ''
  const index = all[0].dataIndex
  const day = days[index]
  const rows = all.map((param) => {
    const { unit, digits } = formats.get(param.seriesName)!
    const raw =
      typeof param.value === 'object' && param.value !== null ? (param.value as { value?: unknown }).value : param.value
    const value = typeof raw === 'number' ? `${raw.toFixed(digits)}${unit ? ` ${unit}` : ''}` : 'Missing'
    const note = estimatedOn(index, param.seriesName) ? ' (estimated)' : ''
    return `<tr><td style="padding-right:12px">${param.marker}${param.seriesName}</td><td style="text-align:right"><strong>${value}</strong>${note}</td></tr>`
  })
  const kind = day && isForecast(day) ? (day.kind === 'partial' ? ' (today, partly forecast)' : ' (forecast)') : ''
  const heading = day ? `${rowLabel(day.date, timeZone)}${kind}` : ''
  return `<strong>${heading}</strong><table>${rows.join('')}</table>`
}

/** The measures a panel's table and summary list: its own, then the lower grid's related measure */
const listed = (panel: WeatherPanel, table: Table) =>
  allMeasures(panel).filter((measure) => table.days.some((day) => day.values[measure.column] != null))

/**
 * The panel in words, for its text alternative and "Summary and data": for each measure the highest and lowest
 * observed values with their dates (amounts: the observed total and the forecast's), then how many values are
 * estimated or missing (D45: "includes N estimated days").
 */
export function panelSummary(panel: WeatherPanel, table: Table, units: Units): string {
  const timeZone = table.location?.timezone ?? undefined
  const word = table.hourly ? 'hour' : 'day'
  const plural = (count: number) => `${count} ${word}${count === 1 ? '' : 's'}`
  const observed = table.days.filter((day) => !isForecast(day) && day.kind !== 'projection')
  const ahead = table.days.filter((day) => isForecast(day))
  const sentences: string[] = []
  if (table.days.length) {
    const first = table.days[0].date
    const last = table.days[table.days.length - 1].date
    sentences.push(`From ${rowLabel(first, timeZone)} to ${rowLabel(last, timeZone)}.`)
  }
  for (const measure of listed(panel, table)) {
    const unit = unitLabel(table, units, measure.column)
    const digits = digitsOf(table, units, measure.column)
    const text = (value: number) => `${value.toFixed(digits)}${unit ? ` ${unit}` : ''}`
    const known = (period: Day[]) =>
      period
        .map((day) => ({ day, value: shown(table, units, measure.column, day) }))
        .filter((entry): entry is { day: Day; value: number } => entry.value !== null)
    const isAmount = panel.bars || (panel.below?.bars && panel.below.series.includes(measure))
    const past = known(observed)
    if (isAmount) {
      const total = (period: { value: number }[]) => period.reduce((sum, entry) => sum + entry.value, 0)
      const parts = []
      if (past.length) parts.push(`${text(total(past))} observed`)
      const next = known(ahead)
      if (next.length) parts.push(`${text(total(next))} forecast`)
      if (parts.length) sentences.push(`${measure.name}: ${parts.join(', ')}.`)
    } else if (past.length) {
      const high = past.reduce((a, b) => (b.value > a.value ? b : a))
      const low = past.reduce((a, b) => (b.value < a.value ? b : a))
      sentences.push(
        `${measure.name}: highest ${text(high.value)} on ${rowLabel(high.day.date, timeZone)}, lowest ${text(low.value)} on ${rowLabel(low.day.date, timeZone)}.`,
      )
    }
    const estimated = observed.filter((day) => day.estimated.has(measure.column)).length
    const missing = observed.filter((day) => day.missing.has(measure.column)).length
    if (estimated) sentences.push(`${measure.name} includes ${plural(estimated)} estimated.`)
    if (missing) sentences.push(`${measure.name} is missing on ${plural(missing)}.`)
  }
  return sentences.length > (table.days.length ? 1 : 0) ? sentences.join(' ') : 'No values for these days yet.'
}

/** The panel's values as a table, newest first: a column per measure (and smoothing window shown), with its unit */
export function panelTable(panel: WeatherPanel, table: Table, units: Units, roll?: number | null) {
  const timeZone = table.location?.timezone ?? undefined
  const measures = listed(panel, table)
  const columns: { column: string; title: string; digits: number }[] = []
  for (const measure of measures) {
    const unit = unitLabel(table, units, measure.column)
    const digits = digitsOf(table, units, measure.column)
    columns.push({ column: measure.column, title: `${measure.name}${unit ? ` (${unit})` : ''}`, digits })
    const rolled = panel.series.includes(measure) ? rolledColumn(table, measure, roll) : null
    if (rolled) {
      const name = rolledName(measure, roll!, !!panel.bars)
      columns.push({ column: rolled, title: `${name}${unit ? ` (${unit})` : ''}`, digits })
    }
  }
  return {
    columns: columns.map((c) => c.title),
    rows: table.days.toReversed().map((day) => ({
      date: day.date,
      label: table.hourly ? rowLabel(day.date, timeZone) : undefined,
      forecast: isForecast(day),
      values: columns.map(({ column, digits }) => {
        const value = shown(table, units, column, day)
        if (value === null) return null
        return `${value.toFixed(digits)}${day.estimated.has(column) ? ' (estimated)' : ''}`
      }),
    })),
  }
}

/** The panel's values for a CSV file, oldest first: Date (or Time, UTC), Kind, then each measure in the
 * reader's units; a missing value is blank */
export function panelCsvRows(panel: WeatherPanel, table: Table, units: Units): CsvValue[][] {
  const measures = listed(panel, table)
  const header = (measure: Measure) => {
    const unit = unitLabel(table, units, measure.column)
    return `${measure.name}${unit ? ` (${unit})` : ''}`
  }
  return [
    [table.hourly ? 'Time (UTC)' : 'Date', 'Kind', ...measures.map(header)],
    ...table.days.map((day) => [
      day.date,
      day.kind,
      ...measures.map((measure) => {
        const value = shown(table, units, measure.column, day)
        return value === null ? null : Number(value.toFixed(digitsOf(table, units, measure.column) + 1))
      }),
    ]),
  ]
}

/** A table as tab-separated text for the clipboard (a spreadsheet pastes it into cells): ISO dates, as shown otherwise */
export function tableTsv(table: {
  columns: string[]
  rows: { date: string; forecast: boolean; values: (string | null)[] }[]
}) {
  const clean = (text: string) => text.replace(/[\t\r\n]+/g, ' ')
  return [
    ['Date', 'Forecast', ...table.columns],
    ...table.rows.map((row) => [row.date, row.forecast ? 'yes' : 'no', ...row.values.map((value) => value ?? '')]),
  ]
    .map((cells) => cells.map(clean).join('\t'))
    .join('\n')
}
