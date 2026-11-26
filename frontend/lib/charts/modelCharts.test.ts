import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'
import cornRun from '@/test/fixtures/site/model-corn-stages.json'
import ecbRun from '@/test/fixtures/site/model-ecb-2025.json'
import lateBlightRun from '@/test/fixtures/site/model-late-blight.json'
import oakWiltRun from '@/test/fixtures/site/model-oak-wilt.json'
import { testPalette as palette } from '@/test/palette'
import type { SiteModelInfo } from '@/types'
import type { TableResponse } from '@/types/api'

import {
  dayTooltip,
  layout,
  levelColor,
  modelOption,
  modelPanels,
  modelRun,
  modelSummary,
  modelTable,
  riskWords,
  stageSpans,
  type ModelPanel,
} from './modelCharts'

const us = unitsFor('imperial')
const q = (name: string, label: string, unit = 'index') => ({ name, label, unit, description: '' })
type Model = Pick<SiteModelInfo, 'inputs' | 'outputs' | 'risk_levels' | 'stages'>

const lateBlight: Model = {
  inputs: [
    q('hours_rh_over_90_from_6pm', 'Humid hours', 'hour'),
    q('temperature_mean_rh_over_90_from_6pm', 'Mean temperature in humid hours', 'degC'),
  ],
  outputs: [
    q('dsv', 'Disease severity values'),
    q('dsv_14_day', 'DSVs in the last 14 days'),
    q('dsv_total', 'DSVs since emergence'),
  ],
  risk_levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'],
  stages: [],
}
const ecb: Model = {
  inputs: [
    q('air_temperature_min', 'Minimum temperature', 'degC'),
    q('air_temperature_max', 'Maximum temperature', 'degC'),
  ],
  outputs: [
    q('dd_total', 'Degree days since the biofix', 'degF_day'),
    q('dd', 'Degree days', 'degF_day'),
    q('activity_adult_flight', 'Adult flight activity'),
    q('generations_adult_flight', 'Generations of adult flight complete'),
    q('activity_young_larvae', 'Young larvae activity'),
    q('window_scout_and_treat_young_larvae_before_they_bore_in', 'Scout and treat'),
    q('freeze_factor', 'Share left after fall freezes'),
  ],
  risk_levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'],
  stages: [],
}
const corn: Model = {
  inputs: [
    q('air_temperature_min', 'Minimum temperature', 'degC'),
    q('air_temperature_max', 'Maximum temperature', 'degC'),
  ],
  outputs: [
    q('stage', 'Stage'),
    q('gdd_total', 'Growing degree days since planting', 'degF_day'),
    q('gdd', 'Growing degree days', 'degF_day'),
  ],
  risk_levels: [],
  stages: [
    { code: 'VE', name: 'Emergence' },
    { code: 'V1', name: 'First leaf' },
  ],
}

type Option = {
  grid: { top: number; height: number }[]
  xAxis: { gridIndex: number; show?: boolean; axisLabel?: { show?: boolean } }[]
  title: { text: string }[]
  series: {
    id?: string
    name: string
    type: string
    xAxisIndex: number
    data: unknown[]
    markLine?: { data: { xAxis: string }[] }
    markArea?: object
    lineStyle?: { type?: string }
  }[]
}

const option = (model: Model, body: unknown, today = '2026-11-25') => {
  const run = modelRun(body as TableResponse)
  const panels = modelPanels(model, run)
  return { run, panels, option: modelOption({ model, run, panels, units: us, palette, today }) as unknown as Option }
}

const keys = (panels: ModelPanel[]) => panels.map((p) => p.key)

describe('modelRun', () => {
  it('reads the text columns, milestones and resolved request beside the numbers', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    expect(run.table.days.length).toBe(run.label.length)
    expect(run.label).toContain('High')
    expect(run.inSeason?.at(-1)).toBe(false)
    expect(run.stage).toBeNull()
    expect(run.susceptibility).toBeNull()
    expect(run.milestones.find((m) => m.name === 'Moderate')?.date).toBe('2026-06-29')
    expect(run.request.biofix).toBe('2026-05-15')
    expect(run.estimatedByInput.temperature_mean_rh_over_90_from_6pm).toBeGreaterThan(0)
  })

  it("flattens an insect's action windows", () => {
    const run = modelRun(ecbRun as TableResponse)
    expect(run.windows).toEqual([
      expect.objectContaining({ name: 'Scout and treat young larvae before they bore in' }),
      expect.objectContaining({ name: 'Scout and treat young larvae before they bore in' }),
    ])
    expect(run.windows[0].start < run.windows[0].end).toBe(true)
  })

  it("reads a crop model's stage codes", () => {
    const run = modelRun(cornRun as TableResponse)
    expect(run.stage?.some((code) => code === 'VE')).toBe(true)
    expect(run.level.every((level) => level === null)).toBe(true)
  })
})

describe('modelPanels', () => {
  it('stacks the risk, the outputs grouped as read, then the inputs by unit', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    const panels = modelPanels(lateBlight, run)
    expect(keys(panels)).toEqual(['risk', 'output-daily', 'output-totals', 'input-hour', 'input-degC'])
    const daily = panels[1] as Extract<ModelPanel, { kind: 'values' }>
    expect(daily.bars).toBe(true)
    expect(daily.series.map((s) => s.column)).toEqual(['dsv'])
    const totals = panels[2] as Extract<ModelPanel, { kind: 'values' }>
    expect(totals.series.map((s) => s.column)).toEqual(['dsv_14_day', 'dsv_total'])
  })

  it("adds an insect's action windows and activity curves, and leaves its bookkeeping out", () => {
    const panels = modelPanels(ecb, modelRun(ecbRun as TableResponse))
    expect(keys(panels)).toEqual(['risk', 'window-0', 'output-totals', 'output-activity', 'output-daily', 'input-degC'])
    const columns = panels.flatMap((p) => (p.kind === 'values' ? p.series.map((s) => s.column) : []))
    expect(columns).not.toContain('generations_adult_flight')
    expect(columns).not.toContain('freeze_factor')
    expect(panels.find((p) => p.key === 'input-degC')?.title).toBe('Air temperature')
  })

  it('gives a crop model its stages and no risk strip', () => {
    const panels = modelPanels(corn, modelRun(cornRun as TableResponse))
    expect(keys(panels)).toEqual(['stages', 'output-totals', 'output-daily', 'input-degC'])
  })
})

describe('modelOption', () => {
  it('draws a grid per panel on one time axis, labelled only at the bottom', () => {
    const { option: o, panels } = option(lateBlight, lateBlightRun)
    expect(o.grid.length).toBe(panels.length)
    const own = o.xAxis.filter((axis) => axis.show !== false)
    expect(own.length).toBe(panels.length)
    expect(own.slice(0, -1).every((axis) => axis.axisLabel?.show === false)).toBe(true)
    expect(o.title.map((t) => t.text)).toContain('Mean temperature in humid hours (°F)')
  })

  it('colors the risk strip by level and fades it out of season', () => {
    const { option: o, run } = option(lateBlight, lateBlightRun)
    const strip = o.series.find((s) => s.id === 'risk')!
    const items = strip.data as ({ itemStyle: { color: string; opacity: number } } | null)[]
    const high = run.label.indexOf('High')
    expect(items[high]!.itemStyle.color).toBe('s4')
    expect(items[high]!.itemStyle.opacity).toBe(1)
    expect(items.at(-1)!.itemStyle.opacity).toBeLessThan(1)
  })

  it('marks today, shades the forecast and draws estimated values hollow', () => {
    const body = structuredClone(lateBlightRun) as unknown as TableResponse
    const data = body.data as Record<string, unknown[]>
    data.temperature_mean_rh_over_90_from_6pm_estimated[0] = true
    const { option: o } = option(lateBlight, body)
    expect(o.series[0].markLine?.data[0].xAxis).toBe('2026-11-25')
    expect(o.series.some((s) => s.id?.startsWith('shading-'))).toBe(true)
    const temperature = o.series.find((s) => s.id === 'input-degC-temperature_mean_rh_over_90_from_6pm')!
    expect(temperature.data.some((d) => typeof d === 'object' && d !== null && 'symbol' in d)).toBe(true)
  })

  it('draws guides: a date through every grid and a value on the grid of its column, in the reader’s units', () => {
    const run = modelRun(oakWiltRun as unknown as TableResponse)
    const panels = modelPanels(ecb, run)
    const o = modelOption({
      model: ecb,
      run,
      panels,
      units: us,
      palette,
      today: '2026-11-25',
      guides: {
        dates: [
          { date: '2026-07-15', label: 'July 15' },
          { date: '2030-01-01', label: 'Not shown' },
        ],
        values: [{ column: 'dd_total', value: 231 / 1.8, label: '231' }],
      },
    }) as unknown as Option & { yAxis: { max?: (extent: { max: number }) => number | undefined }[] }
    const firsts = o.series.filter((s) => s.markLine)
    expect(firsts.length).toBe(panels.length)
    for (const s of firsts) expect(s.markLine!.data.map((d) => d.xAxis)).toContain('2026-07-15')
    expect(firsts.flatMap((s) => s.markLine!.data.map((d) => d.xAxis))).not.toContain('2030-01-01')
    const totals = o.series.find((s) => s.id === 'output-totals-dd_total')!
    const line = (totals.markLine!.data as { yAxis?: number }[]).find((d) => d.yAxis !== undefined)!
    expect(line.yAxis).toBeCloseTo(231)
    const g = panels.findIndex((p) => p.key === 'output-totals')
    expect(o.yAxis[g].max!({ max: 100 })).toBeCloseTo(231)
    expect(o.yAxis[g].max!({ max: 3000 })).toBeUndefined()
    expect(o.yAxis[g + 1].max).toBeUndefined()
  })

  it("shades each action window's days in its strip", () => {
    const { option: o, run } = option(ecb, ecbRun, '2025-07-01')
    const strip = o.series.find((s) => s.id === 'window-0')!
    const dates = run.table.days.map((d) => d.date)
    expect(strip.data[dates.indexOf(run.windows[0].start)]).toBe(1)
    expect(strip.data[dates.indexOf(run.windows[0].start) - 1]).toBeNull()
  })

  it("labels a crop's stages where each begins", () => {
    const { run } = option(corn, cornRun)
    const spans = stageSpans(run.stage!)
    expect(spans[0].code).toBe('VE')
    expect(spans.every((s, k) => k === 0 || s.start === spans[k - 1].end + 1 || s.start > spans[k - 1].end)).toBe(true)
  })

  it('continues a line dashed over its P10–P90 band through a projection', () => {
    const body = structuredClone(lateBlightRun) as unknown as TableResponse
    const data = body.data as Record<string, unknown[]>
    const n = data.date.length
    data.kind = data.kind.map((kind, i) => (i >= n - 5 ? 'projection' : kind))
    data.dsv_total_p10 = data.dsv_total.map((v, i) => (i >= n - 5 ? (v as number) - 2 : null))
    data.dsv_total_p90 = data.dsv_total.map((v, i) => (i >= n - 5 ? (v as number) + 3 : null))
    const { option: o } = option(lateBlight, body)
    const dashed = o.series.find((s) => s.id === 'output-totals-dsv_total-projection')!
    expect(dashed.lineStyle?.type).toBe('dashed')
    expect(dashed.data.filter((v) => v !== null).length).toBe(6) // the last day before it, then its 5
    const solid = o.series.find((s) => s.id === 'output-totals-dsv_total')!
    expect(solid.data.slice(-5).every((v) => v === null)).toBe(true)
    expect(o.series.some((s) => s.id === 'band-output-totals-dsv_total-upper')).toBe(true)
  })

  it('sizes the chart to its panels', () => {
    const { panels } = option(lateBlight, lateBlightRun)
    const { grids, height } = layout(panels)
    expect(grids[0].height).toBeLessThan(grids[1].height) // the strip is thin
    expect(height).toBeGreaterThan(grids.at(-1)!.top + grids.at(-1)!.height)
  })
})

describe('words and table', () => {
  it('says when each level was first reached and what is estimated', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    const text = modelSummary({ model: lateBlight, run, units: us })
    expect(text).toMatch(/^From May 15, 2026 to /)
    expect(text).toContain('Risk first reached Low on May 18, Moderate on Jun 29 and High on Aug 19.')
    // The API flags days without humid hours, whose mean has no value: not an estimate the reader sees
    expect(text).not.toContain('estimated')
    const body = structuredClone(lateBlightRun) as unknown as TableResponse
    ;(body.data as Record<string, unknown[]>).temperature_mean_rh_over_90_from_6pm_estimated[0] = true
    expect(modelSummary({ model: lateBlight, run: modelRun(body), units: us })).toContain(
      'Includes 1 day of estimated mean temperature in humid hours.',
    )
  })

  it("names a day's risk, its stage, its windows and its values in the tooltip", () => {
    const { run, panels } = option(ecb, ecbRun, '2025-07-01')
    const index = run.table.days.findIndex((d) => d.date === run.windows[0].start)
    const html = dayTooltip({ model: ecb, run, panels, units: us, index })
    expect(html).toContain('Action window')
    expect(html).toMatch(/Degree days since the biofix<\/td><td><strong>[\d,]+ °F·d/)
  })

  it('marks a risk out of season or outside the susceptible stages', () => {
    const run = modelRun(lateBlightRun as TableResponse)
    expect(riskWords(run, run.table.days.length - 1)).toMatch(/\(out of season\)$/)
    const gated = { ...run, inSeason: null, susceptibility: run.label.map(() => 'not susceptible') }
    expect(riskWords(gated, 0)).toMatch(/crop not susceptible/)
  })

  it('tables the values newest first', () => {
    const { run, panels } = option(lateBlight, lateBlightRun)
    const table = modelTable({ model: lateBlight, run, panels, units: us })
    expect(table.columns[0]).toBe('Risk')
    expect(table.rows[0].date).toBe(run.table.days.at(-1)!.date)
    expect(table.rows[0].forecast).toBe(true)
  })

  it('takes a scale of 2 to 5 levels in the palette', () => {
    expect(levelColor(4, 5, palette)).toBe('s5')
    expect([0, 1, 2, 3].map((l) => levelColor(l, 4, palette))).toEqual(['s1', 's3', 's4', 's5'])
    expect([0, 1, 2].map((l) => levelColor(l, ['Low', 'Moderate', 'High'], palette))).toEqual(['s2', 's3', 's4'])
    expect([0, 1, 2].map((l) => levelColor(l, ['Low', 'High', 'Extreme'], palette))).toEqual(['s2', 's4', 's5'])
    expect([0, 1].map((l) => levelColor(l, ['Low', 'Infection'], palette))).toEqual(['s2', 's5'])
  })
})
