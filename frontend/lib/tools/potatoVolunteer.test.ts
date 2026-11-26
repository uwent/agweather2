import { describe, expect, it } from 'vitest'

import { modelRun, type ModelRun } from '@/lib/charts/modelCharts'
import { units as unitsFor } from '@/lib/units'
import body from '@/test/fixtures/tools/potato-volunteer.json'
import air from '@/test/fixtures/tools/potato-volunteer-air.json'
import type { TableResponse } from '@/types/api'

import {
  beforeMap,
  currentWinter,
  depthRows,
  mapWinter,
  potatoAnswer,
  potatoGuides,
  potatoPanels,
  potatoWords,
  seasonOf,
  winterChoices,
  winterCodec,
  withAir,
} from './potatoVolunteer'

// Hancock's cell, winter 2025–26 (November 1 to March 31), recorded in metric: 2 and 4 in reached 120 hours on
// January 22 and 8 in on January 24, ending at 547, 536 and 480 hours (Low).
const us = unitsFor('imperial')
const metric = unitsFor('metric')
const full = () => modelRun(body as unknown as TableResponse)
const season = seasonOf(body as unknown as TableResponse)

/** The run as it was seen on `today`, a winter under way: days after it forecast, and none past `last` */
function seenOn(today: string, last: string): ModelRun {
  const run = full()
  run.table.days = run.table.days
    .filter((day) => day.date <= last)
    .map((day) => (day.date > today ? { ...day, kind: 'forecast' as const } : day))
  const n = run.table.days.length
  return { ...run, level: run.level.slice(0, n), label: run.label.slice(0, n) }
}
const underWay = { name: '2025-26', label: '2025–26', final: false }

describe('winters', () => {
  it('belong to November on, and April to October to the one just past', () => {
    expect(currentWinter('2026-11-26')).toBe('2026-27')
    expect(currentWinter('2027-02-10')).toBe('2026-27')
    expect(currentWinter('2026-07-04')).toBe('2025-26')
    expect(currentWinter('2026-10-31')).toBe('2025-26')
  })

  it('lists the winters newest first, back to 2016–17', () => {
    const choices = winterChoices('2026-11-26', 2016)
    expect(choices[0]).toBe('2026-27')
    expect(choices.at(-1)).toBe('2016-17')
    expect(choices).toHaveLength(11)
    expect(winterChoices('2026-07-04', 2010)[0]).toBe('2025-26')
    expect(winterChoices('2026-07-04', 2010).at(-1)).toBe('2016-17')
  })

  it('shows last winter’s map until this winter’s appears on January 1', () => {
    expect(beforeMap('2026-27', '2026-11-26')).toBe(true)
    expect(mapWinter('2026-27', '2026-11-26')).toBe('2025-26')
    expect(mapWinter('2026-27', '2027-01-01')).toBe('2026-27')
    expect(mapWinter('2019-20', '2026-11-26')).toBe('2019-20')
  })

  it('reads only a winter whose second year follows its first', () => {
    expect(winterCodec.parse('2025-26')).toBe('2025-26')
    expect(winterCodec.parse('2099-00')).toBe('2099-00')
    expect(winterCodec.parse('2025-27')).toBeUndefined()
    expect(winterCodec.parse('2025')).toBeUndefined()
  })
})

describe('potatoAnswer', () => {
  it('gives a past winter’s final counts, its level and when each depth reached 120 hours', () => {
    const answer = potatoAnswer({ run: full(), season, today: '2026-11-26' })
    expect(answer.final).toBe(true)
    expect(answer.label).toBe('2025–26')
    expect(answer.date).toBe('2026-03-31')
    expect(answer.depths.map((d) => d.hours)).toEqual([547, 536, 480])
    expect(answer.depths.map((d) => d.reached?.date)).toEqual(['2026-01-22', '2026-01-22', '2026-01-24'])
    expect(answer.levelName).toBe('Low')
    const words = potatoWords(answer, us, 'near Hancock')
    expect(words.headline).toBe(
      'Winter 2025–26 near Hancock: hours of soil below 27 °F at 2 in: 547; 4 in: 536; 8 in: 480. Tuber survival: Low.',
    )
    expect(words.details[0]).toBe(
      'The soil had at least 120 hours below 27 °F at all three depths, so tubers left in the field are unlikely to survive.',
    )
    expect(words.details).toContain(
      'The count reached 120 hours at 2 in on January 22, 4 in on January 22 and 8 in on January 24.',
    )
  })

  it('says plainly that the risk falls as a winter under way builds its hours', () => {
    const answer = potatoAnswer({ run: seenOn('2026-01-15', '2026-01-25'), season: underWay, today: '2026-01-15' })
    expect(answer.final).toBe(false)
    expect(answer.date).toBe('2026-01-15')
    expect(answer.levelName).toBe('Very high')
    expect(answer.depths.map((d) => d.reached?.forecast)).toEqual([true, true, true])
    const words = potatoWords(answer, us, null)
    expect(words.headline).toMatch(/^Winter 2025–26 so far \(November 1 to January 15\): hours of soil below 27 °F/)
    expect(words.headline).toMatch(/Tuber survival so far: Very high\.$/)
    expect(words.details[0]).toBe(
      'No depth has had 120 hours below 27 °F, so tubers left in the field are likely to survive so far.',
    )
    expect(words.details).toContain(
      'By the forecast, it reaches 120 hours at 2 in on January 22, 4 in on January 22 and 8 in on January 24.',
    )
    expect(words.details.at(-1)).toMatch(/risk falls a level as each depth reaches 120 hours\. It can only fall/)
  })

  it('names the depths still short of 120 hours', () => {
    const answer = potatoAnswer({ run: seenOn('2026-01-23', '2026-01-23'), season: underWay, today: '2026-01-23' })
    expect(answer.levelName).toBe('Moderate')
    expect(potatoWords(answer, metric, null).details[0]).toBe(
      'The soil has had at least 120 hours below -2.8 °C at 2 in and 4 in but not at 8 in, so tubers at that depth may survive.',
    )
    expect(depthRows(answer, metric).map((r) => [r.depth, r.reached])).toEqual([
      ['2 in (4 cm)', 'January 22'],
      ['4 in (10 cm)', 'January 22'],
      ['8 in (20 cm)', 'Not yet'],
    ])
  })
})

describe('the chart', () => {
  it('stacks the risk, the hours at each depth, the soil’s lows and the air’s', () => {
    const run = withAir(full(), air as unknown as TableResponse)
    const panels = potatoPanels(run, us)
    expect(panels.map((p) => p.key)).toEqual(['risk', 'hours', 'soil', 'air'])
    expect(panels[1].title).toBe('Hours below 27 °F since November 1')
    const jan = run.table.days.find((day) => day.date === '2026-01-22')!
    expect(jan.values.air_temperature_min).toBeTypeOf('number')
    expect(run.table.units.air_temperature_min).toBe('degC')
    // Without the air's answer, no air panel
    expect(potatoPanels(withAir(full(), null), us).map((p) => p.key)).toEqual(['risk', 'hours', 'soil'])
  })

  it('draws 120 hours and 32 and 27 °F, in °C as the run is stored', () => {
    const guides = potatoGuides(us).values!
    expect(guides[0]).toEqual({ column: 'killing_hours_4cm', value: 120, label: '120 hours' })
    const soil = guides.filter((g) => g.column === 'soil_temperature_4cm_min')
    expect(soil.map((g) => g.label)).toEqual(['32 °F', '27 °F'])
    expect(soil[1].value).toBeCloseTo(-2.78, 2)
  })
})
