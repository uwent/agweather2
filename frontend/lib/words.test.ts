import { describe, expect, it } from 'vitest'

import { plural } from './words'

describe('plural', () => {
  it('names one in the singular and every other count in the plural', () => {
    expect(plural(1, 'day')).toBe('1 day')
    expect(plural(0, 'day')).toBe('0 days')
    expect(plural(3, 'past year')).toBe('3 past years')
  })

  it('takes an irregular plural', () => {
    expect(plural(2, 'entry', 'entries')).toBe('2 entries')
  })
})
