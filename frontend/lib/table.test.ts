// Ported from WISP 3: app/frontend/lib/table.test.ts
import { describe, expect, it } from 'vitest'

import { matchesQuery, sortRows } from './table'

const rows = [
  { email: 'b@example.com', farms: 2, signedIn: '2026-07-01' },
  { email: 'a@example.com', farms: 10, signedIn: null },
  { email: 'C@example.com', farms: 0, signedIn: '2026-08-01' },
]

describe('table', () => {
  it('sorts strings ignoring case and numbers by value', () => {
    expect(sortRows(rows, (r) => r.email, 'asc').map((r) => r.email)).toEqual([
      'a@example.com',
      'b@example.com',
      'C@example.com',
    ])
    expect(sortRows(rows, (r) => r.farms, 'desc').map((r) => r.farms)).toEqual([10, 2, 0])
  })

  it('puts missing values last in both directions', () => {
    expect(sortRows(rows, (r) => r.signedIn, 'asc').map((r) => r.signedIn)).toEqual(['2026-07-01', '2026-08-01', null])
    expect(sortRows(rows, (r) => r.signedIn, 'desc').map((r) => r.signedIn)).toEqual(['2026-08-01', '2026-07-01', null])
  })

  it('matches every word of the query in any text', () => {
    expect(matchesQuery('', ['anything'])).toBe(true)
    expect(matchesQuery('PAT grow', ['Pat Grower', 'pat@example.com'])).toBe(true)
    expect(matchesQuery('pat smith', ['Pat Grower', null])).toBe(false)
    expect(matchesQuery('12', [12])).toBe(true)
  })
})
