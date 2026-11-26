// Ported from WISP 3 (adapted): app/frontend/lib/csv.ts
// CSV files built in the browser (a chart's data). They open with frontmatter: a title line,
// "Label: value" lines, then a blank line before the data. Values are as shown on the page.

export type CsvValue = string | number | null | undefined

export const SOURCE = 'AgWeather, University of Wisconsin–Madison'

/**
 * Text a spreadsheet would read as a formula (=, +, -, @, or a leading tab or return) gets a quote;
 * numbers written as text ("-4.5") don't, as they can't run anything. Same rule as WISP 3's CsvExport#text.
 */
const escaped = (value: string) => (/^[=+\-@\t\r]/.test(value) && !/^-?\d+(\.\d+)?$/.test(value) ? `'${value}` : value)

function cell(value: CsvValue): string {
  if (value === null || value === undefined) return ''
  const text = typeof value === 'number' ? String(value) : escaped(value)
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function toCsv(rows: CsvValue[][]): string {
  return rows.map((row) => row.map(cell).join(',')).join('\r\n') + '\r\n'
}

/** "2026-07-10 14:30" in the browser's time zone, for an "Exported" line */
export function exportedAt(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}

/** The title row, then a row per detail ("Label: value"; a null value leaves its line out), then a blank row */
export function frontmatter(title: string, details: Record<string, string | null | undefined>): CsvValue[][] {
  const lines = Object.entries(details).flatMap(([label, value]) => (value == null ? [] : [[`${label}: ${value}`]]))
  return [[title], ...lines, []]
}

/** Saves text as a file from the browser, after a UTF-8 byte order mark (Excel reads it as Windows-1252 without) */
export function downloadCsv(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob(['\uFEFF', text], { type: 'text/csv;charset=utf-8' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
