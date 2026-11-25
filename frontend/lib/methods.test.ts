import { describe, expect, it } from 'vitest'

import { clockHour, dateSpan, kmText, scoreText, variableAnchor } from '@/lib/methods'

describe('the methods page’s words', () => {
  it('gives a daily variable the anchor model pages link to, and others their kind', () => {
    expect(variableAnchor('air_temperature_min')).toBe('variable-air_temperature_min')
    expect(variableAnchor('precipitation', 'hourly')).toBe('variable-hourly-precipitation')
    expect(variableAnchor('precipitation', 'cumulative')).toBe('variable-total-precipitation')
  })

  it('writes clock hours and date spans out', () => {
    expect([clockHour(0), clockHour(12), clockHour(18), clockHour(30), clockHour(1)]).toEqual([
      'midnight',
      'noon',
      '6 p.m.',
      '6 a.m.',
      '1 a.m.',
    ])
    expect(dateSpan('2017-12-05', null)).toBe('From December 5, 2017 on.')
    expect(dateSpan(null, '2017-12-04')).toBe('Through December 4, 2017.')
    expect(dateSpan(null, null)).toBe('')
  })

  it('gives scores in the reader’s units', () => {
    expect(scoreText(0.45, 'delta_degC', 'metric')).toBe('0.45 °C')
    expect(scoreText(0.45, 'delta_degC', 'imperial')).toBe('0.81 °F')
    expect(scoreText(1.175, 'index', 'imperial')).toBe('1.18')
    expect(scoreText(2.8, 'MJ_m2', 'imperial')).toBe('2.8 MJ/m²')
    expect(scoreText(-0.67, 'hour', 'imperial')).toBe('−0.67 h')
    expect(kmText(2.5)).toBe('2.5 km (1.6 mi)')
  })
})
