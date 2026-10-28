// Display units (PLAN.md D18). Values arrive in the unit they're stored in (SI, or °F·d for most degree
// days), named by symbol; this module is the only place the frontend converts them, at the display and
// input edge. It mirrors packages/agdata/src/agdata/units.py, and both are tested against
// packages/agdata/tests/fixtures/units_cases.json so they can't drift.

export type UnitSystem = 'metric' | 'imperial'

type Unit = {
  label: string
  dimension: string
  /** base = value * factor + offset */
  factor: number
  offset: number
  digits: number
}

const u = (label: string, dimension: string, digits: number, factor = 1, offset = 0): Unit => ({
  label,
  dimension,
  factor,
  offset,
  digits,
})

export const UNITS: Record<string, Unit> = {
  degC: u('°C', 'temperature', 1),
  degF: u('°F', 'temperature', 0, 5 / 9, (-32 * 5) / 9),
  K: u('K', 'temperature', 1, 1, -273.15),
  degC_day: u('°C·d', 'degree_days', 0),
  degF_day: u('°F·d', 'degree_days', 0, 5 / 9),
  mm: u('mm', 'depth', 1),
  kg_m2: u('kg/m²', 'depth', 1),
  cm: u('cm', 'depth', 1, 10),
  in: u('in', 'depth', 2, 25.4),
  m_s: u('m/s', 'speed', 1),
  km_h: u('km/h', 'speed', 0, 1 / 3.6),
  mph: u('mph', 'speed', 0, 0.44704),
  kn: u('kn', 'speed', 0, 1852 / 3600),
  kPa: u('kPa', 'pressure', 1),
  Pa: u('Pa', 'pressure', 0, 0.001),
  hPa: u('hPa', 'pressure', 0, 0.1),
  inHg: u('inHg', 'pressure', 2, 3.386389),
  W_m2: u('W/m²', 'irradiance', 0),
  MJ_m2: u('MJ/m²', 'radiant_exposure', 1),
  kWh_m2: u('kWh/m²', 'radiant_exposure', 2, 3.6),
  ly: u('ly', 'radiant_exposure', 0, 0.041868),
  percent: u('%', 'fraction', 0),
  deg: u('°', 'angle', 0),
}

const DISPLAY: Record<UnitSystem, Record<string, string>> = {
  metric: {
    temperature: 'degC',
    degree_days: 'degC_day',
    depth: 'mm',
    speed: 'km_h',
    pressure: 'kPa',
    radiant_exposure: 'MJ_m2',
  },
  imperial: {
    temperature: 'degF',
    degree_days: 'degF_day',
    depth: 'in',
    speed: 'mph',
    pressure: 'inHg',
    radiant_exposure: 'MJ_m2',
  },
}

export const MISSING = '—'

function unit(symbol: string): Unit {
  const found = UNITS[symbol]
  if (!found) throw new Error(`unknown unit ${symbol}`)
  return found
}

/** A value between units of one dimension; null, undefined and NaN become null */
export function convert(value: number | null | undefined, from: string, to: string): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  if (from === to) return value
  const source = unit(from)
  const target = unit(to)
  if (source.dimension !== target.dimension) throw new Error(`can't convert ${source.label} to ${target.label}`)
  return (value * source.factor + source.offset - target.offset) / target.factor
}

/** The unit a value stored in `stored` is shown in */
export function displayUnit(stored: string, system: UnitSystem): string {
  return DISPLAY[system][unit(stored).dimension] ?? stored
}

export type ParseResult = { ok: true; value: number | null } | { ok: false; error: string }

export type Units = {
  system: UnitSystem
  /** "°F" for a value stored in degC */
  label: (stored: string) => string
  /** The stored value in display units (unrounded), or null */
  toDisplay: (stored: string, value: number | null | undefined) => number | null
  /** "72 °F", or "72" with unit: false; "—" for missing values */
  format: (stored: string, value: number | null | undefined, options?: { digits?: number; unit?: boolean }) => string
  /** A display value for an input box: rounded, no unit, '' for null */
  input: (stored: string, value: number | null | undefined, digits?: number) => string
  /** Text typed in display units → the stored unit; blank is null (not entered), "0" is 0 */
  parse: (stored: string, text: string) => ParseResult
}

export function units(system: UnitSystem = 'imperial'): Units {
  const shown = (stored: string) => unit(displayUnit(stored, system))
  const toDisplay = (stored: string, value: number | null | undefined) =>
    convert(value, stored, displayUnit(stored, system))

  return {
    system,
    label: (stored) => shown(stored).label,
    toDisplay,
    format(stored, value, { digits, unit: withUnit = true } = {}) {
      const display = toDisplay(stored, value)
      if (display === null) return MISSING
      const text = formatNumber(display, digits ?? shown(stored).digits)
      return withUnit ? `${text} ${shown(stored).label}` : text
    },
    input(stored, value, digits) {
      const display = toDisplay(stored, value)
      return display === null ? '' : trimZeros(display.toFixed(digits ?? shown(stored).digits + 1))
    },
    parse(stored, text) {
      const parsed = parseNumber(text)
      if (!parsed.ok || parsed.value === null) return parsed
      return { ok: true, value: convert(parsed.value, displayUnit(stored, system), stored) }
    },
  }
}

/** A plain number typed by the user: blank is null */
export function parseNumber(text: string): ParseResult {
  const trimmed = text.trim().replace(/,/g, '')
  if (trimmed === '') return { ok: true, value: null }
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { ok: false, error: 'Enter a number, such as 0.5' }
  return { ok: true, value }
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return MISSING
  // Avoid "-0.00"
  const rounded = Number(value.toFixed(digits))
  return (Object.is(rounded, -0) ? 0 : rounded).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function trimZeros(text: string) {
  return text.includes('.') ? text.replace(/0+$/, '').replace(/\.$/, '') : text
}
