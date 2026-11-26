import { describe, expect, it } from 'vitest'

import {
  clockHour,
  countText,
  dateSpan,
  degreeDaysText,
  kmText,
  normalsHref,
  scoreText,
  settingText,
  totalText,
  valueText,
  variableAnchor,
  yearsText,
} from '@/lib/methods'
import { units } from '@/lib/units'

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

describe('the words for how normals are made', () => {
  const us = units('imperial')
  const metric = units('metric')

  it('writes years as runs', () => {
    expect(yearsText([1996, 1997, 1998])).toBe('1996–1998')
    expect(yearsText([2020, 2016, 2018, 2019])).toBe('2016, 2018–2020')
    expect(yearsText([])).toBe('')
  })

  it('gives values, counts and degree days in the reader’s units', () => {
    expect(valueText(93.2, 'degF', us)).toBe('93.2 °F')
    expect(valueText(86, 'degF', metric)).toBe('30 °C')
    expect(countText({ variable: 'air_temperature_max', above: 86, below: null, unit: 'degF' }, us)).toBe(
      'Days with a high of 86 °F or more',
    )
    expect(countText({ variable: 'precipitation_sum', above: null, below: 0.01, unit: 'in' }, metric)).toBe(
      'Days with precipitation of 0.254 mm or less',
    )
    expect(degreeDaysText(1500, us)).toBe('1,500 °F degree days')
    expect(degreeDaysText(395, metric)).toBe('219 °C degree days')
  })

  it('names degree-day settings and the totals kept with percentiles', () => {
    expect(settingText('modified', 50, 86, us)).toBe('modified average, 50 to 86 °F')
    expect(settingText('sine', 52, null, metric)).toBe('single sine, base 11.1 °C')
    expect(totalText('dd_sine_41_86', us)).toBe('degree days (single sine, 41 to 86 °F) since January 1')
    expect(totalText('precipitation', us, 'Precipitation since Jan 1')).toBe('precipitation since January 1')
    expect(normalsHref()).toBe('/methods#normals')
  })
})
