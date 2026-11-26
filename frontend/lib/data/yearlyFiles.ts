// /data's yearly files (track 7 step 7.1): `/downloads`' list as a table of variables by year, grouped as the
// location builder groups its variables, with the current year's last day (its files are rebuilt weekly).

import type { DownloadFile, VariableInfo } from '@/types/api'

import { groupVariables } from '../sites/dataRequest'

export type YearlyRow = {
  name: string
  longName: string
  /** By year, as `years` lists them; null where there's no file */
  files: (DownloadFile | null)[]
}

export type YearlyTable = {
  years: number[]
  groups: { label: string; rows: YearlyRow[] }[]
  /** The newest year's last day, when its files aren't whole years yet */
  through: string | null
  files: number
  bytes: number
}

/** The files as a table: a row per variable (in the catalog's order within each group), a column per year */
export function yearlyTable(files: DownloadFile[], variables: VariableInfo[]): YearlyTable {
  const years = [...new Set(files.map((f) => f.year))].sort((a, b) => a - b)
  const byVariable = new Map<string, Map<number, DownloadFile>>()
  for (const file of files) {
    if (!byVariable.has(file.variable)) byVariable.set(file.variable, new Map())
    byVariable.get(file.variable)!.set(file.year, file)
  }
  const daily = variables.filter((v) => v.kind === 'daily' && byVariable.has(v.name))
  const named = new Set(daily.map((v) => v.name))
  // A file whose variable /variables doesn't list (it shouldn't happen) still shows, under its own name
  const unnamed = [...byVariable.keys()].filter((name) => !named.has(name))
  const shown: Pick<VariableInfo, 'name' | 'long_name'>[] = [
    ...daily,
    ...unnamed.map((name) => ({ name, long_name: name })),
  ]
  const groups = groupVariables(shown as VariableInfo[]).map((group) => ({
    label: group.label,
    rows: group.variables.map((v) => ({
      name: v.name,
      longName: v.long_name,
      files: years.map((year) => byVariable.get(v.name)?.get(year) ?? null),
    })),
  }))
  const newest = files.filter((f) => f.year === years.at(-1))
  const through = newest.some((f) => !f.complete) ? newest.map((f) => f.last).sort().at(-1)! : null
  return { years, groups, through, files: files.length, bytes: files.reduce((sum, f) => sum + f.bytes, 0) }
}

/** A file's size as its cell shows it: "12 MB", "850 KB" */
export function shortSize(bytes: number): string {
  if (bytes < 1e6) return `${Math.max(1, Math.round(bytes / 1000))} KB`
  return `${Math.round(bytes / 1e6).toLocaleString('en-US')} MB`
}
