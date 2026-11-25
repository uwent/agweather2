// Ported from WISP 3 (adapted): app/frontend/lib/csv.test.ts
import { describe, expect, it } from 'vitest'

import { exportedAt, frontmatter, toCsv } from './csv'

describe('CSV files', () => {
  it('quotes commas and quotes, leaves missing values blank, and escapes formulas but not numbers', () => {
    expect(
      toCsv([
        ['a,b', 'say "hi"', null, 1.5],
        ['=SUM(A1)', '-4.5', '@x', -2],
      ]),
    ).toBe('"a,b","say ""hi""",,1.5\r\n\'=SUM(A1),-4.5,\'@x,-2\r\n')
  })

  it('opens with a title, the details that have a value, and a blank line', () => {
    expect(frontmatter('AgWeather data', { Site: 'Hancock', Group: null, Units: 'in' })).toEqual([
      ['AgWeather data'],
      ['Site: Hancock'],
      ['Units: in'],
      [],
    ])
  })

  it("writes the time in the browser's zone", () => {
    expect(exportedAt(new Date(2026, 6, 10, 9, 5))).toBe('2026-07-10 09:05')
  })
})
