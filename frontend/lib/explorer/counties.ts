// The map's county table (Phase 7 track 2 step 7): the map's values summarized over each county of a state, from
// `/summaries/{layer}` with the same settings as the tiles, so the table is the map's accessible equivalent. Pure
// helpers, tested in counties.test.ts; CountyTable.svelte fetches and shows them.

import type { TileCategory } from '@/lib/map/dataTiles'
import { categoryCode } from '@/lib/map/dataTiles'
import type { Column } from '@/lib/table'
import { formatNumber, MISSING, type Units, units as unitsOf } from '@/lib/units'

import type { TileRequest } from './view'

/** The states of the area AgWeather maps (D105: the 12 Midwest states and Kentucky), by postal code */
export const COVERAGE_STATES: { code: string; name: string }[] = [
  { code: 'IL', name: 'Illinois' },
  { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' },
  { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' },
  { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' },
  { code: 'MO', name: 'Missouri' },
  { code: 'NE', name: 'Nebraska' },
  { code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' },
  { code: 'SD', name: 'South Dakota' },
  { code: 'WI', name: 'Wisconsin' },
]

/** A state's postal code from /locate's `state` ("WI"), if it's one the table offers */
export function stateCode(state: string | null | undefined): string | null {
  if (!state) return null
  const found = COVERAGE_STATES.find((s) => s.code === state.toUpperCase() || s.name === state)
  return found?.code ?? null
}

/** `/summaries/{layer}`'s query for the tiles' request: `{time}` as `date`, `time` or `start` and `end` */
export function summaryParams(tiles: TileRequest, region: string): Record<string, string | number> {
  const params: Record<string, string | number> = { region }
  for (const [name, value] of Object.entries(tiles.params)) if (value !== null) params[name] = value
  const { time } = tiles
  if (time.includes('..')) {
    const [start, end] = time.split('..')
    Object.assign(params, { start, end })
  } else if (time.includes('T')) params.time = time
  else if (time !== 'latest') params.date = time
  if (tiles.stat) params.stat = tiles.stat
  return params
}

/** One county's row as the table shows it */
export type CountyRow = {
  fips: string
  name: string
  /** The percent of its land with data */
  coverage: number | null
  /** In the stored unit */
  mean: number | null
  min: number | null
  max: number | null
  /** A map of levels': the highest level found, and the percent of cells at each level by its column name */
  highest: string | null
  levels: Record<string, number | null>
}

/** `/summaries`' columns as the API sends them (`orient=columns`) */
export type SummaryColumns = Record<string, (string | number | boolean | null)[]>

const numberOrNull = (value: unknown): number | null => (typeof value === 'number' ? value : null)

/**
 * The rows of a summary: one per county (the map's one step). Values come in US units (`units=us`, as the tiles
 * are asked) and are kept in `storedUnit`, so the table shows them in the reader's units.
 */
export function countyRows(data: SummaryColumns, storedUnit: string): CountyRow[] {
  const us = unitsOf('imperial')
  const stored = (value: unknown) => {
    const n = numberOrNull(value)
    return n === null || storedUnit === 'index' || storedUnit === 'date' ? n : us.toStored(storedUnit, n)
  }
  const levelColumns = Object.keys(data).filter((name) => name.startsWith('pct_'))
  return (data.fips ?? []).map((fips, k) => ({
    fips: String(fips),
    name: String(data.name?.[k] ?? ''),
    coverage: numberOrNull(data.coverage?.[k]),
    mean: stored(data.mean?.[k]),
    min: stored(data.min?.[k]),
    max: stored(data.max?.[k]),
    highest: (data.highest?.[k] as string | null | undefined) ?? null,
    levels: Object.fromEntries(levelColumns.map((name) => [name, numberOrNull(data[name][k])])),
  }))
}

/** The table's columns: the county, then its mean, lowest and highest (or a map of levels' highest level and the
 * percent of its land at each), and its coverage */
export function countyColumns(
  rows: CountyRow[],
  { unit, units, categories }: { unit: string; units: Units; categories: TileCategory[] | null },
): Column<CountyRow>[] {
  const columns: Column<CountyRow>[] = [
    { key: 'name', label: 'County', value: (r) => r.name, searchable: true, pin: 'left', wrap: true },
  ]
  const stages = categories?.some((c) => c.value < 0) ? categories : null
  const levelled = rows.some((r) => Object.keys(r.levels).length > 0)
  if (levelled) {
    const order = categories?.map((c) => c.name) ?? []
    columns.push({
      key: 'highest',
      label: 'Highest level',
      value: (r) => (r.highest === null ? null : order.indexOf(r.highest)),
      text: (r) => r.highest ?? MISSING,
      firstDirection: 'desc',
    })
    const names = Object.keys(rows[0]?.levels ?? {})
    for (const name of names) {
      const code = name.slice('pct_'.length)
      const label = categories?.find((c) => c.code === code)?.name ?? code.replaceAll('_', ' ')
      columns.push({
        key: name,
        label: `${label} (% of land)`,
        value: (r) => r.levels[name],
        text: (r) => (r.levels[name] === null ? MISSING : formatNumber(r.levels[name], 0)),
        align: 'right',
        firstDirection: 'desc',
      })
    }
  } else {
    const show = (value: number | null) => {
      if (value === null) return MISSING
      if (stages) return categoryCode(stages, value) || formatNumber(value, 0)
      if (unit === 'index') return formatNumber(value, 0)
      return units.format(unit, value, { unit: false })
    }
    const label = stages || unit === 'index' || unit === 'date' ? '' : ` (${units.label(unit)})`
    const stat = (key: 'mean' | 'min' | 'max', name: string): Column<CountyRow> => ({
      key,
      label: `${name}${label}`,
      value: (r) => r[key],
      text: (r) => show(r[key]),
      align: 'right',
      firstDirection: 'desc',
    })
    columns.push(stat('mean', 'Average'), stat('min', 'Lowest'), stat('max', 'Highest'))
  }
  columns.push({
    key: 'coverage',
    label: 'Land with data (%)',
    value: (r) => r.coverage,
    text: (r) => (r.coverage === null ? MISSING : formatNumber(r.coverage, 0)),
    align: 'right',
  })
  return columns
}
