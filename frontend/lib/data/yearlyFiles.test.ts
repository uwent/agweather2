import { describe, expect, it } from 'vitest'

import variablesAnswer from '@/test/fixtures/site/variables.json'
import type { DownloadFile, VariableInfo } from '@/types/api'

import { shortSize, yearlyTable } from './yearlyFiles'

const variables = variablesAnswer.data as VariableInfo[]

function file(variable: string, year: number, last = `${year}-12-31`): DownloadFile {
  return {
    variable,
    year,
    url: `http://testserver/downloads/daily/${year}/${variable}_${year}.nc`,
    bytes: 12_000_000,
    first: `${year}-01-01`,
    last,
    complete: last.endsWith('12-31'),
    built_at: '2026-11-23T02:00:00+00:00',
  }
}

describe('the yearly files', () => {
  it('lays them out by variable and year, grouped as the location builder groups them', () => {
    const files = [
      file('precipitation_sum', 2025),
      file('air_temperature_max', 2025),
      file('air_temperature_max', 2026, '2026-11-24'),
      file('precipitation_sum', 2026, '2026-11-23'),
    ]
    const table = yearlyTable(files, variables)
    expect(table.years).toEqual([2025, 2026])
    expect(table.groups[0].label).toBe('Temperature')
    const tmax = table.groups[0].rows.find((r) => r.name === 'air_temperature_max')!
    expect(tmax.longName).toBe('Air temperature at 2 m, daily max')
    expect(tmax.files.map((f) => f?.year)).toEqual([2025, 2026])
    expect(table.through).toBe('2026-11-24')
    expect(table).toMatchObject({ files: 4, bytes: 48_000_000 })
  })

  it('leaves a missing year empty, and shows a variable /variables doesn’t name under its own name', () => {
    const table = yearlyTable([file('precipitation_sum', 2024), file('air_temperature_max', 2025), file('new_one', 2025)], variables)
    const rows = table.groups.flatMap((g) => g.rows)
    expect(rows.find((r) => r.name === 'precipitation_sum')!.files.map((f) => f?.year ?? null)).toEqual([2024, null])
    expect(rows.find((r) => r.name === 'new_one')!.longName).toBe('new_one')
    expect(table.through).toBeNull()
  })

  it('gives sizes in whole kilobytes or megabytes', () => {
    expect(shortSize(12_754_505)).toBe('13 MB')
    expect(shortSize(850_000)).toBe('850 KB')
    expect(shortSize(200)).toBe('1 KB')
  })
})
