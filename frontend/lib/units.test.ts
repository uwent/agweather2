import { describe, expect, it } from 'vitest'

import cases from '../../packages/agdata/tests/fixtures/units_cases.json'
import { convert, displayUnit, MISSING, units, type UnitSystem } from './units'

describe('the table shared with agdata.units', () => {
  it.each(cases.convert)('converts $value $from to $to', ({ value, from, to, expected }) => {
    expect(convert(value, from, to)).toBeCloseTo(expected, 6)
  })

  it.each(cases.display)('shows $stored as $unit in $system', ({ stored, system, unit }) => {
    expect(displayUnit(stored, system as UnitSystem)).toBe(unit)
  })
})

describe('units', () => {
  const imperial = units('imperial')
  const metric = units('metric')

  it('formats stored SI values in the display system', () => {
    expect(imperial.format('degC', 20)).toBe('68 °F')
    expect(metric.format('degC', 20)).toBe('20.0 °C')
    expect(imperial.format('mm', 25.4)).toBe('1.00 in')
    expect(metric.format('m_s', 10)).toBe('36 km/h')
    expect(imperial.format('W_m2', 512.4)).toBe('512 W/m²')
  })

  it('keeps degree days in °F·d for imperial, whatever they are stored in', () => {
    expect(imperial.format('degF_day', 1234)).toBe('1,234 °F·d')
    expect(metric.format('degF_day', 1800)).toBe('1,000 °C·d')
  })

  it('shows missing values as a dash, not zero', () => {
    expect(imperial.format('degC', null)).toBe(MISSING)
    expect(imperial.format('degC', Number.NaN)).toBe(MISSING)
    expect(imperial.format('mm', 0)).toBe('0.00 in')
    expect(imperial.input('mm', null)).toBe('')
  })

  it('parses typed display values back to the stored unit', () => {
    const parsed = imperial.parse('degC', '68')
    expect(parsed.ok && parsed.value).toBeCloseTo(20, 9)
    expect(imperial.parse('mm', ' ')).toEqual({ ok: true, value: null })
    expect(imperial.parse('mm', 'lots').ok).toBe(false)
  })
})
