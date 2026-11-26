import { describe, expect, it } from 'vitest'

import { andList, longDate, modelMapUrl, monthDay, seasonText, unitLabel } from './format'

describe('model page words', () => {
  it('writes dates out', () => {
    expect(monthDay('07-01')).toBe('July 1')
    expect(longDate('2026-11-18')).toBe('November 18, 2026')
  })

  it('joins lists in prose', () => {
    expect(andList([])).toBe('')
    expect(andList(['corn'])).toBe('corn')
    expect(andList(['potato', 'tomato'])).toBe('potato and tomato')
    expect(andList(['a', 'b', 'c'])).toBe('a, b and c')
  })

  it('says a season, all year, or one over New Year', () => {
    expect(seasonText(['07-01', '08-15'])).toBe('From July 1 to August 15 each year.')
    expect(seasonText(null)).toBe('All year.')
    expect(seasonText(['05-15', '09-30'], 'about a week before the first egg hatch in a typical year')).toBe(
      'Its season opens at each location about a week before the first egg hatch in a typical year, and runs to September 30. Where we don’t have the 30-year normal temperatures, it opens on May 15.',
    )
    expect(seasonText(['11-01', '03-31'])).toBe('From November 1 to March 31 each year, into the next year.')
  })

  it('labels units in the reader’s system', () => {
    expect(unitLabel('degC', 'imperial')).toBe('°F')
    expect(unitLabel('degC', 'metric')).toBe('°C')
    expect(unitLabel('degF_day', 'metric')).toBe('°C·d')
    expect(unitLabel('percent', 'imperial')).toBe('%')
    expect(unitLabel('index', 'imperial')).toBe('')
    expect(unitLabel('no-such-unit', 'imperial')).toBe('')
  })

  it('links to the model’s map', () => {
    expect(modelMapUrl('tar-spot')).toBe('/map?layer=tar-spot')
  })
})
