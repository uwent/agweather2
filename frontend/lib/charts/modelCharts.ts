// A model at a site as one chart (frontend.md, Charts; track 3 step 6): stacked grids on a shared time axis, so a
// day lines up from the answer down to the weather that made it. From the top: the risk as a strip coloured by level
// (muted out of season and outside the crop's susceptible stages), each action window as a strip (D36), the crop's
// stages as labelled bands, the outputs (daily amounts as bars, totals and curves as lines) and the inputs, grouped
// by unit (never two units on one axis). The forecast is shaded across every grid, a dashed Today line runs through
// them, a projection (D63) continues each line dashed over its P10–P90 band, estimated values are hollow and
// missing values gaps (kinds.ts).
//
//   const run = modelRun(body)                 // the /models/{id}/run answer, with its text columns and summary
//   const panels = modelPanels(model, run)     // what the chart stacks, from the spec and what the run has
//   build = (palette, view) => modelOption({ model, run, panels, units, palette, today })
//   modelSummary({ model, run, units, today })  // the chart in words: its text alternative and summary
//   modelTable({ model, run, panels, units })   // "Summary and data"'s table, newest first

import type { SiteModelInfo } from '@/types'
import type { TableResponse } from '@/types/api'

import { formatDate } from '../dates'
import { riskStep, type RiskScale } from '../riskLevels'
import { tableRows, type Day, type Table } from '../tableRows'
import type { Units } from '../units'
import type { EChartsCoreOption } from './echarts'
import { band, bar, forecastBand, isForecast, lineStyle, point, rounded } from './kinds'
import { baseOption, type Palette } from './palette'

// --- The run ------------------------------------------------------------------------------------------------------

/** When a risk level, crop stage or action window is first reached (`meta.summary.milestones`; with a projection,
 * `meta.summary.projection.milestones`) */
export type Milestone = {
  what: string
  name: string
  date: string | null
  day_kind: string | null
  before_start: boolean
}

/** An action window (D36): a named span of days, such as "Scout and treat young larvae before they bore in" */
export type ActionWindow = { name: string; start: string; end: string }

export type ModelRun = {
  table: Table
  /** Each day's risk word, null without one */
  label: (string | null)[]
  /** Each day's risk level (0 the lowest), null without one */
  level: (number | null)[]
  /** Whether each day is in the model's season; null for a model without a season */
  inSeason: (boolean | null)[] | null
  /** Each day's place in the crop's susceptible window (`susceptible`, `margin`, `not susceptible`); null when the
   * run has none (no planting date) */
  susceptibility: (string | null)[] | null
  /** A crop model's stage code each day; null for other models */
  stage: (string | null)[] | null
  milestones: Milestone[]
  windows: ActionWindow[]
  /** The run as resolved: its biofix, planting date, start and end */
  request: { biofix: string | null; planting: string | null; start: string | null; end: string | null }
  estimatedByInput: Record<string, number>
  missingByInput: Record<string, number>
  warnings: string[]
}

type Raw = Record<string, (number | string | boolean | null)[]>

/** A text or flag column aligned with the table's days (`tableRows` keeps only numbers, and drops rows without a
 * kind); null when the answer hasn't the column */
function aligned<T>(data: Raw, table: Table, name: string, read: (value: unknown) => T): T[] | null {
  const column = data[name]
  if (!column) return null
  const at = new Map(((data.date ?? []) as string[]).map((date, i) => [date, i]))
  return table.days.map((day) => read(column[at.get(day.date) ?? -1]))
}

const text = (value: unknown) => (typeof value === 'string' ? value : null)
const flag = (value: unknown) => (typeof value === 'boolean' ? value : null)
const record = (value: unknown) => (value && typeof value === 'object' ? (value as Record<string, unknown>) : {})

/** A model run's answer as what the chart, its words and the table read */
export function modelRun(body: Pick<TableResponse, 'meta' | 'data'>): ModelRun {
  const table = tableRows(body)
  const data = (Array.isArray(body.data) ? {} : body.data) as Raw
  const summary = record(body.meta.summary)
  const projection = record(summary.projection)
  const found = (projection.milestones ?? summary.milestones ?? []) as Milestone[]
  const windows: ActionWindow[] = []
  for (const entry of (summary.windows ?? []) as { windows?: Record<string, [string, string][]> }[]) {
    for (const [name, spans] of Object.entries(entry.windows ?? {})) {
      for (const [start, end] of spans) windows.push({ name, start, end })
    }
  }
  const request = record(body.meta.request)
  const planting = request.planting_date
  return {
    table,
    label: aligned(data, table, 'risk_label', text) ?? table.days.map(() => null),
    level: table.days.map((day) => day.values.risk_level ?? null),
    inSeason: aligned(data, table, 'in_season', flag),
    susceptibility: aligned(data, table, 'susceptibility', text),
    stage: aligned(data, table, 'stage_code', text),
    milestones: found.filter((m) => m && typeof m.name === 'string'),
    windows,
    request: {
      biofix: text(request.biofix),
      planting: typeof planting === 'string' ? planting : text(record(planting).date),
      start: text(request.start),
      end: text(request.end),
    },
    estimatedByInput: record(summary.estimated_by_input) as Record<string, number>,
    missingByInput: record(summary.missing_by_input) as Record<string, number>,
    warnings: body.meta.warnings ?? [],
  }
}

// --- What the chart stacks ----------------------------------------------------------------------------------------

export type ModelSeries = { column: string; name: string; color: (palette: Palette) => string }

export type ModelPanel =
  | { kind: 'risk'; key: string; title: string }
  | { kind: 'window'; key: string; title: string; spans: ActionWindow[] }
  | { kind: 'stages'; key: string; title: string }
  | { kind: 'values'; key: string; title: string; series: ModelSeries[]; bars: boolean; input: boolean }

const OUTPUT_COLORS: ((p: Palette) => string)[] = [
  (p) => p.degreeDays,
  (p) => p.precipitation,
  (p) => p.et,
  (p) => p.temperature.max,
  (p) => p.projection,
  (p) => p.temperature.min,
]

/** An input's color by what it measures: temperatures in the temperature colors (high, low, mean), humidity and
 * wetness in the precipitation color, anything else in turn */
function inputColor(name: string, k: number): (p: Palette) => string {
  if (/temperature.*_max|_max$/.test(name) && /temperature/.test(name)) return (p) => p.temperature.max
  if (/temperature.*_min|_min$/.test(name) && /temperature/.test(name)) return (p) => p.temperature.min
  if (/temperature|dew_point/.test(name)) return (p) => p.temperature.mean
  if (/humid|rh_|wet|precip/.test(name)) return (p) => p.precipitation
  return OUTPUT_COLORS[k % OUTPUT_COLORS.length]
}

const hasValues = (table: Table, column: string) => table.days.some((day) => day.values[column] != null)

/**
 * What the chart stacks, top to bottom: the risk strip (a model with risk levels), a strip per action window, the
 * crop's stages (a crop model), the outputs and the inputs. Outputs are grouped as readers read them: daily amounts
 * with a running total (`dsv` beside `dsv_total`) as bars; the totals (`_total`, and `_14_day` sums) together; an
 * insect's life-stage activity curves together; the primary output (the spec's first) on its own otherwise.
 * Bookkeeping outputs (generations, window flags, normals, freeze factors) stay out of the chart (the CSV has them).
 * Inputs are grouped by unit. A group without values in the run isn't drawn.
 */
export function modelPanels(model: Pick<SiteModelInfo, 'inputs' | 'outputs' | 'risk_levels'>, run: ModelRun) {
  const { table } = run
  const panels: ModelPanel[] = []
  if (model.risk_levels.length && run.level.some((level) => level !== null))
    panels.push({ kind: 'risk', key: 'risk', title: 'Risk' })
  const names = [...new Set(run.windows.map((w) => w.name))]
  names.forEach((name, k) =>
    panels.push({ kind: 'window', key: `window-${k}`, title: name, spans: run.windows.filter((w) => w.name === name) }),
  )
  if (run.stage?.some((code) => code !== null)) panels.push({ kind: 'stages', key: 'stages', title: 'Crop stage' })

  const outputs = model.outputs.filter((q) => q.name !== 'stage' && hasValues(table, q.name))
  const names_ = new Set(outputs.map((q) => q.name))
  const totals = outputs.filter((q) => /_total$|_\d+_day$/.test(q.name))
  const daily = outputs.filter((q) => names_.has(`${q.name}_total`))
  const activity = outputs.filter((q) => q.name.startsWith('activity_'))
  const primary = model.outputs[0]
  const groups: { key: string; title: string; members: typeof outputs; bars: boolean }[] = []
  const add = (key: string, members: typeof outputs, bars: boolean, title?: string) => {
    if (members.length) groups.push({ key, members, bars, title: title ?? members.map((q) => q.label).join(' and ') })
  }
  add('activity', activity, false, 'Activity of each life stage (1 at the first generation’s peak)')
  add('totals', totals, false)
  add('daily', daily, true)
  const grouped = new Set(groups.flatMap((g) => g.members.map((q) => q.name)))
  if (primary && names_.has(primary.name) && !grouped.has(primary.name)) add('primary', [primary], false)
  // The primary output's group first
  groups.sort((a, b) => Number(b.members.includes(primary)) - Number(a.members.includes(primary)))
  let color = 0
  for (const group of groups) {
    panels.push({
      kind: 'values',
      key: `output-${group.key}`,
      title: group.title,
      bars: group.bars,
      input: false,
      series: group.members.map((q) => ({ column: q.name, name: q.label, color: OUTPUT_COLORS[color++ % 6] })),
    })
  }

  const byUnit = new Map<string, SiteModelInfo['inputs']>()
  for (const q of model.inputs.filter((q) => hasValues(table, q.name))) {
    byUnit.set(q.unit, [...(byUnit.get(q.unit) ?? []), q])
  }
  let k = 0
  for (const [unit, members] of byUnit) {
    const temperatures = members.length > 1 && members.every((q) => /temperature/.test(q.name))
    panels.push({
      kind: 'values',
      key: `input-${unit}`,
      title: temperatures ? 'Air temperature' : members.map((q) => q.label).join(' and '),
      bars: false,
      input: true,
      series: members.map((q) => ({ column: q.name, name: q.label, color: inputColor(q.name, k++) })),
    })
  }
  return panels
}

// --- Display helpers -----------------------------------------------------------------------------------------------

/** A column's value on a day in the reader's units */
export function shownValue(table: Table, units: Units, column: string, day: Day): number | null {
  const value = day.values[column] ?? null
  const symbol = table.units[column.replace(/_p(10|90)$/, '')]
  return symbol ? units.toDisplay(symbol, value) : value
}

/** A column's unit in the reader's units ('' for an index or a count) */
export function shownUnit(table: Table, units: Units, column: string): string {
  const symbol = table.units[column]
  return symbol ? units.label(symbol) : ''
}

/** Decimals for a column: its unit's, or for a unitless one none if every value is whole, else 2 */
export function shownDigits(table: Table, units: Units, column: string): number {
  const symbol = table.units[column]
  if (symbol) return units.digits(symbol)
  return table.days.every((day) => {
    const v = day.values[column]
    return v === null || v === undefined || Number.isInteger(v)
  })
    ? 0
    : 2
}

/** A column's value as text with its unit, "—" when missing */
export function formatValue(table: Table, units: Units, column: string, day: Day): string {
  const value = shownValue(table, units, column, day)
  if (value === null) return '—'
  const unit = shownUnit(table, units, column)
  const digits = shownDigits(table, units, column)
  const number = value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  return unit ? `${number} ${unit}` : number
}

/** The color of level `level` on a scale, from the palette's five risk levels (lib/riskLevels' steps) */
export function levelColor(level: number, scale: RiskScale, palette: Palette): string {
  return palette.severity[riskStep(level, scale) ?? 0]
}

/** Whether a day's risk counts: in season and, where the run has the crop's stages, in its susceptible window */
export function riskCounts(run: ModelRun, index: number): boolean {
  if (run.inSeason && run.inSeason[index] === false) return false
  if (run.susceptibility && run.susceptibility[index] !== null && run.susceptibility[index] !== 'susceptible')
    return false
  return true
}

/** The crop's stages as spans of days (indexes into the table's days, inclusive) */
export function stageSpans(stage: (string | null)[]): { code: string; start: number; end: number }[] {
  const spans: { code: string; start: number; end: number }[] = []
  stage.forEach((code, i) => {
    const last = spans.at(-1)
    if (code === null) return
    if (last && last.code === code && last.end === i - 1) last.end = i
    else spans.push({ code, start: i, end: i })
  })
  return spans
}

// --- The chart -----------------------------------------------------------------------------------------------------

const VALUES_HEIGHT = 96
const STRIP_HEIGHT = 14
const TITLE = 24
// A grid whose series need a legend has it on a line of its own under the title, so neither crowds the other on a phone
const LEGEND = 14
const GAP = 8
const BOTTOM = 26

/** Each grid's top and height in pixels, and the chart's height */
export function layout(panels: ModelPanel[]): {
  grids: { top: number; height: number; head: number }[]
  height: number
} {
  let y = 4
  const grids = panels.map((panel) => {
    const height = panel.kind === 'values' ? VALUES_HEIGHT : STRIP_HEIGHT
    const head = TITLE + (panel.kind === 'values' && panel.series.length > 1 ? LEGEND : 0)
    const grid = { top: y + head, height, head }
    y += head + height + GAP
    return grid
  })
  return { grids, height: y - GAP + BOTTOM }
}

export type ModelChartOptions = {
  model: Pick<SiteModelInfo, 'risk_levels' | 'stages'>
  run: ModelRun
  panels: ModelPanel[]
  units: Units
  palette: Palette
  /** The grid's today (ISO date), for the dashed Today line */
  today: string
  /** Reference lines: a labelled vertical line through every grid on each date, and a horizontal line at a value
   * (in the column's stored unit) on the grid that draws the column, whose axis then reaches it */
  guides?: ChartGuides
}

export type ChartGuides = {
  dates?: { date: string; label: string }[]
  values?: { column: string; value: number; label: string }[]
}

/** The ECharts option: a grid per panel, stacked on one time axis */
export function modelOption({
  model,
  run,
  panels,
  units,
  palette,
  today,
  guides = {},
}: ModelChartOptions): EChartsCoreOption {
  const { table } = run
  const days = table.days
  const dates = days.map((day) => day.date)
  const base = baseOption(palette)
  const { grids } = layout(panels)
  const count = panels.length
  const { shading, label: forecastLabel } = forecastBand({ dates, days, grids: count, axisOffset: count, palette })
  const projected = days.map((day) => day.kind === 'projection')
  const firstProjected = projected.indexOf(true)
  const todayAt = dates.indexOf(today)
  // Today's and the forecast's labels go on the first grid tall enough for them
  const labelled = Math.max(
    0,
    panels.findIndex((panel) => panel.kind === 'values'),
  )

  const series: object[] = []
  const legends: object[] = []
  const titles: object[] = []
  const guideStyle = { color: palette.inkMuted, type: 'dotted', width: 1.5 }
  const guideLabel = (text: string, position: string, show: boolean) =>
    show ? { formatter: text, position, color: palette.inkMuted, fontSize: 10 } : { show: false }
  const dateGuides = (guides.dates ?? []).filter((guide) => dates.includes(guide.date))
  // Each values grid's horizontal guides, in the reader's units
  const valueGuides = panels.map((panel) =>
    panel.kind === 'values'
      ? (guides.values ?? []).flatMap((guide) => {
          if (!panel.series.some((m) => m.column === guide.column)) return []
          const symbol = table.units[guide.column]
          const value = symbol ? units.toDisplay(symbol, guide.value) : guide.value
          return value === null ? [] : [{ ...guide, value }]
        })
      : [],
  )

  panels.forEach((panel, g) => {
    const top = grids[g].top
    titles.push({
      text: panel.kind === 'values' ? valuesTitle(panel, table, units) : panel.title,
      top: top - grids[g].head + 2,
      left: 0,
      textStyle: { fontSize: 11, fontWeight: 'normal', color: palette.inkMuted, width: 900, overflow: 'truncate' },
    })
    const marks: { silent: boolean; symbol: string; data: object[] } = {
      silent: true,
      symbol: 'none',
      data:
        todayAt >= 0
          ? [
              {
                xAxis: today,
                lineStyle: { color: palette.ink, type: 'dashed', width: 1, opacity: 0.6 },
                label:
                  g === labelled
                    ? { formatter: 'Today', position: 'insideEndTop', color: palette.inkMuted, fontSize: 10 }
                    : { show: false },
              },
            ]
          : [],
    }
    for (const guide of dateGuides)
      marks.data.push({
        xAxis: guide.date,
        lineStyle: guideStyle,
        label: guideLabel(guide.label, 'insideEndTop', g === labelled),
      })
    for (const guide of valueGuides[g])
      marks.data.push({
        yAxis: guide.value,
        lineStyle: guideStyle,
        label: guideLabel(guide.label, 'insideStartTop', true),
      })
    const first = { markLine: marks, markArea: g === labelled ? forecastLabel : undefined }
    const common = { xAxisIndex: g, yAxisIndex: g }

    if (panel.kind === 'risk') {
      series.push({
        ...common,
        ...first,
        id: 'risk',
        name: 'Risk',
        type: 'bar',
        barWidth: '100%',
        data: run.level.map((level, i) =>
          level === null
            ? null
            : {
                value: 1,
                itemStyle: {
                  color: levelColor(level, model.risk_levels, palette),
                  opacity: riskCounts(run, i) ? 1 : 0.3,
                },
              },
        ),
      })
    } else if (panel.kind === 'window') {
      series.push({
        ...common,
        ...first,
        id: panel.key,
        name: panel.title,
        type: 'bar',
        barWidth: '100%',
        itemStyle: { color: palette.degreeDays },
        data: dates.map((date) => (panel.spans.some((w) => w.start <= date && date <= w.end) ? 1 : null)),
      })
    } else if (panel.kind === 'stages') {
      const spans = stageSpans(run.stage ?? [])
      series.push({
        ...common,
        ...first,
        id: 'stages',
        name: 'Crop stage',
        type: 'bar',
        barWidth: '100%',
        data: days.map((_, i) => {
          const k = spans.findIndex((s) => s.start <= i && i <= s.end)
          return k < 0 ? null : { value: 1, itemStyle: { color: k % 2 ? palette.line : palette.surface } }
        }),
        label: {
          show: true,
          position: 'inside',
          fontSize: 9,
          color: palette.ink,
          // Each stage's code on its first day
          // Each stage's code on its first day, for stages long enough to hold it (the tooltip names every one)
          formatter: (p: { dataIndex: number }) =>
            spans.find((s) => s.start === p.dataIndex && s.end - s.start >= 4)?.code ?? '',
        },
        labelLayout: { hideOverlap: true },
      })
    } else {
      panel.series.forEach((measure, k) => {
        const color = measure.color(palette)
        const values = days.map((day) => rounded(shownValue(table, units, measure.column, day)))
        const head = k === 0 ? first : {}
        if (panel.bars) {
          series.push({
            ...common,
            ...head,
            id: `${panel.key}-${measure.column}`,
            name: measure.name,
            type: 'bar',
            barMaxWidth: 8,
            itemStyle: { color },
            data: days.map((day, i) => {
              const item = bar(values[i], day.estimated.has(measure.column), color, palette)
              return projected[i] && item !== null ? { value: values[i], itemStyle: { color, opacity: 0.45 } } : item
            }),
          })
          return
        }
        const line = {
          ...common,
          type: 'line',
          symbol: 'circle',
          showSymbol: false,
          symbolSize: 4,
          connectNulls: false,
          itemStyle: { color },
        }
        series.push({
          ...line,
          ...head,
          id: `${panel.key}-${measure.column}`,
          name: measure.name,
          lineStyle: lineStyle(color),
          data: days.map((day, i) =>
            projected[i] ? null : point(values[i], day.estimated.has(measure.column), palette),
          ),
        })
        if (firstProjected >= 0) {
          // The P50 dashed from the last day before it, over its P10–P90 band
          series.push({
            ...line,
            id: `${panel.key}-${measure.column}-projection`,
            name: `${measure.name} (projection)`,
            lineStyle: lineStyle(color, 'projection'),
            data: values.map((value, i) =>
              i >= firstProjected - 1 && (projected[i] || i === firstProjected - 1) ? value : null,
            ),
          })
          const low = days.map((day, i) =>
            projected[i] ? rounded(shownValue(table, units, `${measure.column}_p10`, day)) : null,
          )
          const high = days.map((day, i) =>
            projected[i] ? rounded(shownValue(table, units, `${measure.column}_p90`, day)) : null,
          )
          if (low.some((v) => v !== null))
            series.push(
              ...band({
                id: `${panel.key}-${measure.column}`,
                lower: low,
                upper: high,
                color: palette.projection,
                xAxisIndex: g,
                yAxisIndex: g,
              }),
            )
        }
      })
      if (panel.series.length > 1)
        legends.push({
          top: top - grids[g].head + 16,
          left: 0,
          data: panel.series.map((m) => m.name),
          textStyle: { color: palette.inkMuted, fontSize: 10 },
          itemWidth: 12,
          itemHeight: 8,
          selectedMode: false,
        })
    }
  })

  const last = count - 1
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    title: titles,
    legend: legends,
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        return list.length ? dayTooltip({ model, run, panels, units, index: list[0].dataIndex }) : ''
      },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: grids.map((grid) => ({ left: 44, right: 12, top: grid.top, height: grid.height })),
    xAxis: [
      ...panels.map((_, g) => ({
        type: 'category',
        data: dates,
        gridIndex: g,
        axisLabel: g === last ? { ...base.axisLabel, formatter: (date: string) => formatDate(date) } : { show: false },
        axisTick: { show: g === last },
        axisLine: base.axisLine,
      })),
      ...shading.xAxis,
    ],
    yAxis: [
      ...panels.map((panel, g) =>
        panel.kind === 'values'
          ? {
              type: 'value',
              gridIndex: g,
              scale: !panel.bars,
              min: panel.bars ? 0 : undefined,
              // An axis reaches its guides, so a threshold not yet reached still shows (left to ECharts otherwise)
              max: valueGuides[g].length
                ? (extent: { max: number }) => {
                    const top = Math.max(...valueGuides[g].map((guide) => guide.value))
                    return top > extent.max ? top : undefined
                  }
                : undefined,
              splitNumber: 2,
              axisLabel: base.axisLabel,
              splitLine: base.splitLine,
            }
          : { type: 'value', gridIndex: g, min: 0, max: 1, show: false },
      ),
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [...panels.map((_, g) => g), ...shading.xAxisIndexes] }],
    series: [...series, ...shading.series],
  }
}

function valuesTitle(panel: Extract<ModelPanel, { kind: 'values' }>, table: Table, units: Units): string {
  const unit = shownUnit(table, units, panel.series[0].column)
  return unit ? `${panel.title} (${unit})` : panel.title
}

/** A day's tooltip: its date and kind, the risk, stage and windows, then each value drawn */
export function dayTooltip({
  model,
  run,
  panels,
  units,
  index,
}: Pick<ModelChartOptions, 'model' | 'run' | 'panels' | 'units'> & { index: number }): string {
  const day = run.table.days[index]
  if (!day) return ''
  const kind =
    day.kind === 'projection'
      ? ' (projection: the middle of past years)'
      : isForecast(day)
        ? day.kind === 'partial'
          ? ' (today, partly forecast)'
          : ' (forecast)'
        : ''
  const rows: [string, string][] = []
  const risk = riskWords(run, index)
  if (risk) rows.push(['Risk', risk])
  const code = run.stage?.[index]
  if (code) {
    const stage = model.stages.find((s) => s.code === code)
    rows.push(['Crop stage', stage ? `${code}, ${stage.name}` : code])
  }
  for (const w of run.windows) if (w.start <= day.date && day.date <= w.end) rows.push(['Action window', w.name])
  for (const panel of panels) {
    if (panel.kind !== 'values') continue
    for (const measure of panel.series) {
      let value = formatValue(run.table, units, measure.column, day)
      if (day.estimated.has(measure.column)) value += ' (estimated)'
      if (day.kind === 'projection' && day.values[`${measure.column}_p10`] != null)
        value += ` (P10–P90 ${formatValue(run.table, units, `${measure.column}_p10`, day)} to ${formatValue(run.table, units, `${measure.column}_p90`, day)})`
      rows.push([measure.name, value === '—' ? 'Missing' : value])
    }
  }
  const cells = rows
    .map(
      ([name, value]) =>
        `<tr><td style="padding-right:12px">${escape(name)}</td><td><strong>${escape(value)}</strong></td></tr>`,
    )
    .join('')
  return `<strong>${formatDate(day.date, { weekday: true })}${kind}</strong><table>${cells}</table>`
}

const escape = (text: string) =>
  text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

/** A day's risk in words: "High", "High (out of season)", "High (crop not susceptible)"; null without one */
export function riskWords(run: ModelRun, index: number): string | null {
  const label = run.label[index]
  if (!label) return null
  if (run.inSeason && run.inSeason[index] === false) return `${label} (out of season)`
  const gate = run.susceptibility?.[index]
  if (gate && gate !== 'susceptible')
    return `${label} (crop ${gate === 'margin' ? 'near its susceptible stages' : 'not susceptible'})`
  return label
}

// --- In words and as a table ---------------------------------------------------------------------------------------

const list = (items: string[]) =>
  items.length <= 1 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`

/**
 * The chart in words, for its text alternative and "Summary and data": the days shown, when each risk level, stage
 * and action window was first reached, the primary output's highest and latest values, and how many days are
 * estimated or missing (D45, D56).
 */
export function modelSummary({
  model,
  run,
  units,
}: {
  model: Pick<SiteModelInfo, 'outputs' | 'inputs'>
  run: ModelRun
  units: Units
}): string {
  const { days } = run.table
  if (!days.length) return 'The model has no results for these days.'
  const sentences = [
    `From ${formatDate(days[0].date, { year: true })} to ${formatDate(days.at(-1)!.date, { year: true })}.`,
  ]
  const reached = (what: string) =>
    run.milestones
      .filter((m) => m.what === what && m.date)
      .map(
        (m) =>
          `${m.name} on ${formatDate(m.date)}${m.day_kind === 'projection' ? ' (projected)' : m.day_kind === 'forecast' || m.day_kind === 'partial' ? ' (forecast)' : ''}`,
      )
  const risks = reached('risk')
  if (risks.length) sentences.push(`Risk first reached ${list(risks)}.`)
  const stages = reached('stage')
  if (stages.length) sentences.push(`The crop reached ${list(stages)}.`)
  for (const name of new Set(run.windows.map((w) => w.name))) {
    const spans = run.windows
      .filter((w) => w.name === name)
      .map((w) => `${formatDate(w.start)} to ${formatDate(w.end)}`)
    sentences.push(`${name}: ${list(spans)}.`)
  }
  const primary = model.outputs.find((q) => q.name !== 'stage' && days.some((d) => d.values[q.name] != null))
  if (primary) {
    const known = days.filter((d) => d.values[primary.name] != null && d.kind !== 'projection')
    if (known.length) {
      const high = known.reduce((a, b) => (b.values[primary.name]! > a.values[primary.name]! ? b : a))
      const latest = known.at(-1)!
      sentences.push(
        `${primary.label}: highest ${formatValue(run.table, units, primary.name, high)} on ${formatDate(high.date)}, ${formatValue(run.table, units, primary.name, latest)} on ${formatDate(latest.date)}.`,
      )
    }
  }
  const label = (name: string) => model.inputs.find((q) => q.name === name)?.label.toLowerCase() ?? name
  const plural = (n: number) => `${n} ${n === 1 ? 'day' : 'days'}`
  // Counted from the rows: an input with no value on a day (a mean over no humid hours) isn't an estimate shown
  for (const q of model.inputs) {
    const n = days.filter((d) => d.kind !== 'projection' && d.estimated.has(q.name) && d.values[q.name] != null).length
    if (n) sentences.push(`Includes ${plural(n)} of estimated ${label(q.name)}.`)
  }
  for (const [name, n] of Object.entries(run.missingByInput))
    if (n) sentences.push(`${plural(n)} of ${label(name)} are missing.`)
  return sentences.join(' ')
}

/** The chart's values as a table, newest first: the risk, the stage and each value drawn, with its unit */
export function modelTable({
  model,
  run,
  panels,
  units,
}: Pick<ModelChartOptions, 'model' | 'run' | 'panels' | 'units'>) {
  const measures = panels.flatMap((panel) => (panel.kind === 'values' ? panel.series : []))
  const columns = [
    ...(model.risk_levels.length ? ['Risk'] : []),
    ...(run.stage ? ['Crop stage'] : []),
    ...measures.map((m) => {
      const unit = shownUnit(run.table, units, m.column)
      return unit ? `${m.name} (${unit})` : m.name
    }),
  ]
  const rows = run.table.days.map((day, i) => ({
    date: day.date,
    forecast: isForecast(day) || day.kind === 'projection',
    values: [
      ...(model.risk_levels.length ? [riskWords(run, i)] : []),
      ...(run.stage ? [run.stage[i]] : []),
      ...measures.map((m) => {
        const value = shownValue(run.table, units, m.column, day)
        if (value === null) return null
        const digits = shownDigits(run.table, units, m.column)
        return `${value.toFixed(digits)}${day.estimated.has(m.column) ? ' (estimated)' : ''}`
      }),
    ],
  }))
  return { columns, rows: rows.toReversed() }
}
