// Saved sites as CSV: `name,lat,lng,groups`, groups separated by semicolons. Import also reads the Crop Risk Tool's
// files (its export `id,name,lat,lng`, and the column names its upload took: location, latitude, long, longitude)
// and a spreadsheet's: a byte order mark, quoted cells, any column order, extra columns ignored.

import { toCsv } from './csv'
import { roundCoord, validCoords } from './siteKey'

export const MAX_NAME_LENGTH = 60

export type CsvSite = { name: string; lat: number; lng: number; groups: string[] }

/** A row left out, in a sentence for the reader; `row` is its line as a spreadsheet numbers it (the header is 1) */
export type SkippedRow = { row: number; message: string }

/** A site read from a file, with its row as a spreadsheet numbers it */
export type ParsedSite = CsvSite & { row: number }

export type ParsedCsv = { sites: ParsedSite[]; skipped: SkippedRow[]; error: string | null }

// Each column's names, as a header cleaned to lowercase letters and underscores reads (janitor::clean_names)
const ALIASES: Record<'name' | 'lat' | 'lng' | 'groups', string[]> = {
  name: ['name', 'location', 'site', 'site_name', 'location_name'],
  lat: ['lat', 'latitude'],
  lng: ['lng', 'lon', 'long', 'longitude'],
  groups: ['groups', 'group'],
}

/** RFC 4180 rows: quoted cells may hold commas, quotes ("") and line breaks; CRLF, LF or CR end a row */
export function parseCsvRows(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  const input = text.replace(/^\uFEFF/, '')
  for (let k = 0; k < input.length; k++) {
    const c = input[k]
    if (quoted) {
      if (c === '"' && input[k + 1] === '"') {
        cell += '"'
        k++
      } else if (c === '"') {
        quoted = false
      } else {
        cell += c
      }
    } else if (c === '"' && cell === '') {
      quoted = true
    } else if (c === ',') {
      row.push(cell)
      cell = ''
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && input[k + 1] === '\n') k++
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
    } else {
      cell += c
    }
  }
  if (cell !== '' || row.length) {
    row.push(cell)
    rows.push(row)
  }
  return rows
}

const cleanHeader = (text: string) =>
  text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')

/** A name as saved: tags removed (a file may hold anything), spaces collapsed, at most MAX_NAME_LENGTH characters */
export function cleanName(text: string): string {
  const plain = text
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.length > MAX_NAME_LENGTH ? `${plain.slice(0, MAX_NAME_LENGTH - 1).trimEnd()}…` : plain
}

/** `name`, or `name (2)`, `name (3)`… if `taken` has it (compared ignoring case); adds what it returns to `taken` */
export function uniqueName(name: string, taken: Set<string>): string {
  if (!name) return name
  let candidate = name
  for (let n = 2; taken.has(candidate.toLowerCase()); n++) candidate = `${name} (${n})`
  taken.add(candidate.toLowerCase())
  return candidate
}

const quote = (value: string) => `'${value}'`

/** A coordinate typed in a file: a number, with a comma for a decimal point read too ('43,07' from some locales'
 * spreadsheets, when the cell was quoted) */
function coordinate(text: string): number | null {
  const trimmed = text.trim().replace(/^(-?\d+),(\d+)$/, '$1.$2')
  if (!/^[-+]?\d+(\.\d+)?$|^[-+]?\.\d+$/.test(trimmed)) return null
  return Number(trimmed)
}

/** The sites in a CSV file, with the rows left out and why. `error` is set (and nothing read) when the file has no
 * rows or lacks a latitude or longitude column. */
export function parseSitesCsv(text: string): ParsedCsv {
  // Each row with its number, blank ones left out
  const rows = parseCsvRows(text)
    .map((cells, k) => ({ cells, row: k + 1 }))
    .filter(({ cells }) => cells.some((cell) => cell.trim() !== ''))
  if (rows.length === 0) return { sites: [], skipped: [], error: 'The file is empty.' }
  const header = rows[0].cells.map(cleanHeader)
  const column = (names: string[]) => header.findIndex((h) => names.includes(h))
  const at = {
    name: column(ALIASES.name),
    lat: column(ALIASES.lat),
    lng: column(ALIASES.lng),
    groups: column(ALIASES.groups),
  }
  if (at.lat < 0 || at.lng < 0) {
    return {
      sites: [],
      skipped: [],
      error:
        'We couldn’t find latitude and longitude columns. The first row should name the columns, such as name, lat, lng.',
    }
  }
  const sites: ParsedSite[] = []
  const skipped: SkippedRow[] = []
  for (const { cells, row } of rows.slice(1)) {
    const latText = (cells[at.lat] ?? '').trim()
    const lngText = (cells[at.lng] ?? '').trim()
    const lat = coordinate(latText)
    const lng = coordinate(lngText)
    if (lat === null || lng === null) {
      const which = lat === null ? `latitude ${quote(latText)}` : `longitude ${quote(lngText)}`
      skipped.push({
        row,
        message: `Row ${row} was skipped: its ${latText === '' || lngText === '' ? 'latitude or longitude is blank' : `${which} isn’t a number in decimal degrees`}.`,
      })
      continue
    }
    if (!validCoords(lat, lng)) {
      skipped.push({
        row,
        message: `Row ${row} was skipped: ${lat}, ${lng} isn’t a place on Earth. Latitude runs from -90 to 90 and longitude from -180 to 180.`,
      })
      continue
    }
    const groups = at.groups >= 0 ? (cells[at.groups] ?? '').split(';').map(cleanName).filter(Boolean) : []
    sites.push({
      name: at.name >= 0 ? cleanName(cells[at.name] ?? '') : '',
      lat: roundCoord(lat),
      lng: roundCoord(lng),
      groups: [...new Set(groups)],
      row,
    })
  }
  return { sites, skipped, error: null }
}

/** The CSV a reader downloads: a row per site in their order, its groups by name */
export function sitesToCsv(sites: readonly CsvSite[]): string {
  return toCsv([['name', 'lat', 'lng', 'groups'], ...sites.map((s) => [s.name, s.lat, s.lng, s.groups.join(';')])])
}
