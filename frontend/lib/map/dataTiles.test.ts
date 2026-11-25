import { describe, expect, it } from 'vitest'

import type { PaletteInfo } from '@/types/api'

import {
  codeValue,
  colorExpression,
  decodePixel,
  findPalette,
  formatDays,
  fittedTicks,
  legendTicks,
  Lru,
  maplibreEncoding,
  NONE_COLOR,
  roundToStep,
  tileUrl,
  valueAt,
  valueTileAt,
  ZERO,
} from './dataTiles'

// The bytes agdata.tiles writes for a value: code = round(value / step) + 2²³
const bytes = (value: number, step: number) => {
  const code = Math.round(value / step) + ZERO
  return [code >> 16, (code >> 8) & 0xff, code & 0xff, 255] as const
}

describe('decoding a data tile pixel', () => {
  it('reads values in the stored unit at the layer step', () => {
    expect(decodePixel(...bytes(21.3, 0.1), 0.1)).toBe(21.3)
    expect(decodePixel(...bytes(-27.4, 0.1), 0.1)).toBe(-27.4) // a January low, °C
    expect(decodePixel(...bytes(3187.5, 0.5), 0.5)).toBe(3187.5) // degree days in the thousands
    expect(decodePixel(...bytes(3, 1), 1)).toBe(3) // a risk level
    expect(decodePixel(...bytes(0, 1), 1)).toBe(0)
    expect(decodePixel(...bytes(12.34, 0.02), 0.02)).toBe(12.34)
    expect(decodePixel(...bytes(0.287, 0.001), 0.001)).toBe(0.287)
  })

  it('matches the API docs formula', () => {
    // value = (R·65536 + G·256 + B) × step − 8,388,608 × step
    const [r, g, b] = [128, 0, 213]
    expect(decodePixel(r, g, b, 255, 0.1)).toBe(21.3)
    expect(decodePixel(127, 255, 255, 255, 1)).toBe(-1)
  })

  it('reads code 0 and alpha 0 as missing, code 1 as none', () => {
    expect(decodePixel(0, 0, 0, 0, 0.1)).toBeNull()
    expect(decodePixel(128, 0, 5, 0, 0.1)).toBeNull()
    expect(decodePixel(0, 0, 1, 255, 1)).toBe('none')
  })

  it('reads a pixel of a decoded tile by its place', () => {
    const data = new Uint8ClampedArray(2 * 2 * 4)
    data.set(bytes(-3.2, 0.1), 3 * 4) // x 1, y 1
    expect(valueAt({ data, width: 2 }, 1, 1, 0.1)).toBe(-3.2)
    expect(valueAt({ data, width: 2 }, 0, 1, 0.1)).toBeNull()
  })

  it('rounds to the step without float noise', () => {
    expect(roundToStep(0.1 * 3, 0.1)).toBe(0.3)
    expect(roundToStep(1234.25, 0.5)).toBe(1234.5)
    expect(roundToStep(7.000000001, 1)).toBe(7)
  })
})

describe("MapLibre's encoding", () => {
  it("subtracts baseShift, as MapLibre's DEMData decodes", () => {
    const e = maplibreEncoding(0.1)
    const [r, g, b] = bytes(21.3, 0.1)
    expect(r * e.redFactor + g * e.greenFactor + b * e.blueFactor - e.baseShift).toBeCloseTo(21.3, 6)
  })
})

describe('the color-relief expression', () => {
  const sequential = { kind: 'sequential' as const, colors: ['#000000', '#808080', '#ffffff'] }

  it('spreads a continuous palette over the domain, missing transparent and none gray', () => {
    const expression = colorExpression(sequential, [0, 40], 0.1) as unknown[]
    expect(expression.slice(0, 3)).toEqual(['interpolate', ['linear'], ['elevation']])
    const stops = expression.slice(3)
    expect(stops).toEqual([
      codeValue(0, 0.1),
      'rgba(0, 0, 0, 0)',
      roundToStep(codeValue(1, 0.1), 0.1),
      NONE_COLOR,
      roundToStep(codeValue(2, 0.1), 0.1),
      '#000000',
      0,
      '#000000',
      20,
      '#808080',
      40,
      '#ffffff',
    ])
  })

  it('keeps stops strictly rising at the step, dropping any that meet', () => {
    const stops = (colorExpression(sequential, [0, 1], 1) as unknown[]).slice(3)
    const values = stops.filter((_, i) => i % 2 === 0) as number[]
    expect(values).toEqual([...values].sort((a, b) => a - b))
    expect(new Set(values).size).toBe(values.length)
    // 0.5 rounds onto 0 or 1 and is dropped: the low and high colors stay
    expect(stops.slice(-4)).toEqual([0, '#000000', 1, '#ffffff'])
  })

  it('handles degree days in the thousands and negative domains', () => {
    const stops = (colorExpression(sequential, [500, 3000], 0.5) as unknown[]).slice(3)
    expect(stops.slice(-6)).toEqual([500, '#000000', 1750, '#808080', 3000, '#ffffff'])
    const cold = (colorExpression(sequential, [-30, -10], 0.1) as unknown[]).slice(3)
    expect(cold.slice(-6)).toEqual([-30, '#000000', -20, '#808080', -10, '#ffffff'])
  })

  it('colors a categorical palette by level', () => {
    const levels = { kind: 'categorical' as const, colors: ['#0000ff', '#ffff00', '#ff0000'] }
    const stops = (colorExpression(levels, [0, 2], 1) as unknown[]).slice(3)
    expect(stops.slice(-6)).toEqual([0, '#0000ff', 1, '#ffff00', 2, '#ff0000'])
  })
})

describe('palettes', () => {
  const palettes: PaletteInfo[] = [
    {
      id: 'BuYlRd',
      kind: 'diverging',
      colors: ['#0000ff', '#ff0000'],
      description: '',
      source: '',
      colorblind_safe: true,
    },
  ]

  it('finds a palette and its reverse', () => {
    expect(findPalette('BuYlRd', palettes)?.colors).toEqual(['#0000ff', '#ff0000'])
    expect(findPalette('BuYlRd_r', palettes)?.colors).toEqual(['#ff0000', '#0000ff'])
    expect(findPalette('BuYlRd_r', palettes)?.id).toBe('BuYlRd_r')
    expect(findPalette('nope', palettes)).toBeUndefined()
  })
})

describe('date layers', () => {
  it('shows days since 1970 as dates', () => {
    expect(formatDays(20_718)).toBe('Sep 22, 2026')
    expect(formatDays(20_718, false)).toBe('Sep 22')
    expect(formatDays(0)).toBe('Jan 1, 1970')
  })
})

describe('legend ticks', () => {
  it('picks round values inside the range', () => {
    expect(legendTicks(59, 99.5).map((t) => t.value)).toEqual([60, 70, 80, 90])
    expect(legendTicks(0, 3000).map((t) => t.value)).toEqual([0, 1000, 2000, 3000])
    expect(legendTicks(0, 2.26).map((t) => t.value)).toEqual([0, 0.5, 1, 1.5, 2])
    expect(legendTicks(-22, 8).map((t) => t.value)).toEqual([-20, -10, 0])
  })

  it('fits as many as the bar holds', () => {
    const format = (value: number, digits: number) =>
      value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    expect(fittedTicks(500, 3000, format).map((t) => t.label)).toEqual(['1,000', '2,000', '3,000'])
    expect(fittedTicks(59, 99.5, format).map((t) => t.label)).toEqual(['60', '70', '80', '90'])
    expect(fittedTicks(0, 2.26, format).map((t) => t.label)).toEqual(['0.0', '0.5', '1.0', '1.5', '2.0'])
  })

  it('places them along the bar', () => {
    const ticks = legendTicks(0, 100)
    expect(ticks[0]).toEqual({ value: 0, at: 0 })
    expect(ticks.at(-1)).toEqual({ value: 100, at: 1 })
  })
})

describe('tiles under a point', () => {
  it('finds the z8 tile as agdata.tiles.tile_of does', () => {
    // Madison: agdata.tiles.tile_of(-89.4, 43.07, 8) == (64, 93)
    const at = valueTileAt(-89.4, 43.07)
    expect([at.z, at.x, at.y]).toEqual([8, 64, 93])
  })

  it('fills a tile template', () => {
    expect(tileUrl('/api/v2/tiles/x/latest/{z}/{x}/{y}.png?dd=50', 8, 64, 93)).toBe(
      '/api/v2/tiles/x/latest/8/64/93.png?dd=50',
    )
  })
})

describe('Lru', () => {
  it('forgets the least recently used past its size', () => {
    const lru = new Lru<string, number>(2)
    lru.set('a', 1)
    lru.set('b', 2)
    lru.get('a')
    lru.set('c', 3)
    expect(lru.has('a')).toBe(true)
    expect(lru.has('b')).toBe(false)
    expect(lru.count).toBe(2)
  })
})
