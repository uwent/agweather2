import { describe, expect, it } from 'vitest'

import { imageLegendOf, type DataLegendSpec } from './DataLegend.svelte'
import {
  attributionText,
  fitText,
  footerLines,
  imageFileName,
  type ImageLegend,
  LEGEND_MARGIN,
  LEGEND_WIDTH,
  legendBox,
  legendLayout,
  titleHeight,
} from './exportImage'

// A stand-in for a canvas's text widths: 0.6 of the font size a character
const measure = (text: string, size: number) => text.length * size * 0.6

const bar: ImageLegend = {
  title: 'Air temperature (°F)',
  bar: { colors: ['#000', '#fff'], ticks: [{ at: 0, label: '20' }] },
  levels: [],
  none: null,
}
const levels: ImageLegend = {
  title: 'Late blight risk',
  bar: null,
  levels: ['Very low', 'Low', 'Moderate', 'High', 'Very high'].map((label, i) => ({ color: `#00000${i}`, label })),
  none: null,
}

describe('legendLayout', () => {
  it('puts a continuous legend’s bar under its title and its swatches below the ticks', () => {
    const layout = legendLayout(bar, measure)
    expect(layout.bar).not.toBeNull()
    expect(layout.bar!.y).toBeGreaterThan(layout.titleY)
    expect(layout.swatches.map((s) => s.label)).toEqual(['No data'])
    expect(layout.swatches[0].hatched).toBe(true)
    expect(layout.swatches[0].y).toBeGreaterThan(layout.bar!.ticksY)
    expect(layout.height).toBeGreaterThan(layout.swatches[0].y)
  })

  it('wraps levels’ swatches within the legend’s width', () => {
    const layout = legendLayout({ ...levels, none: '#dedede' }, measure)
    const labels = layout.swatches.map((s) => s.label)
    expect(labels).toEqual(['Very low', 'Low', 'Moderate', 'High', 'Very high', 'None', 'No data'])
    expect(new Set(layout.swatches.map((s) => s.y)).size).toBeGreaterThan(1)
    for (const swatch of layout.swatches) {
      expect(swatch.x + 12 + 4 + measure(swatch.label, 11)).toBeLessThanOrEqual(LEGEND_WIDTH)
    }
  })

  it('sits at the map’s lower left, as on screen', () => {
    const box = legendBox(bar, 500, measure)
    expect(box.x).toBe(LEGEND_MARGIN)
    expect(box.y + box.h).toBe(500 - LEGEND_MARGIN)
  })
})

describe('imageLegendOf', () => {
  const spec: DataLegendSpec = {
    title: 'Air temperature',
    unit: '°F',
    colors: ['#000', '#888', '#fff'],
    categorical: false,
    low: 10,
    high: 50,
    dates: false,
    none: false,
  }

  it('gives a continuous legend its unit, colors and the screen’s ticks', () => {
    const legend = imageLegendOf(spec)
    expect(legend.title).toBe('Air temperature (°F)')
    expect(legend.bar?.colors).toEqual(spec.colors)
    expect(legend.bar?.ticks.map((t) => t.label)).toEqual(['10', '20', '30', '40', '50'])
    expect(legend.levels).toEqual([])
  })

  it('names a risk map’s levels', () => {
    const legend = imageLegendOf({
      ...spec,
      title: 'Risk',
      categorical: true,
      colors: ['#0a0', '#a00'],
      categories: [
        { value: 0, code: null, name: 'Low' },
        { value: 1, code: null, name: 'High' },
      ],
      none: true,
    })
    expect(legend.title).toBe('Risk')
    expect(legend.bar).toBeNull()
    expect(legend.levels).toEqual([
      { color: '#0a0', label: 'Low' },
      { color: '#a00', label: 'High' },
    ])
    expect(legend.none).not.toBeNull()
  })
})

describe('the image’s text', () => {
  it('makes room for the data’s reach under the title', () => {
    expect(titleHeight('Observed through Nov 24, 2026')).toBeGreaterThan(titleHeight(''))
  })

  it('puts the sources under the credit on a narrow map, wrapped and whole', () => {
    const sources = ['AgWeather, UW–Madison; NOAA NDFD grid © OpenFreeMap © OpenStreetMap', 'agweather.example']
    expect(footerLines('AgWeather', sources, 1200, measure).oneLine).toBe(true)
    const narrow = footerLines('AgWeather', sources, 300, measure)
    expect(narrow.oneLine).toBe(false)
    expect(narrow.lines.length).toBeGreaterThan(1)
    expect(narrow.lines.join(' ')).toBe(sources.join('  ·  ').replace(/ {2}/g, '  '))
    for (const line of narrow.lines) expect(measure(line, 11)).toBeLessThanOrEqual(300 - 32)
    expect(narrow.height).toBeGreaterThan(footerLines('AgWeather', sources, 1200, measure).height)
  })

  it('cuts a long title with an ellipsis', () => {
    expect(fitText('Short', 200, 10, measure)).toBe('Short')
    const cut = fitText('A very long title that cannot fit', 60, 10, measure)
    expect(cut.endsWith('…')).toBe(true)
    expect(measure(cut, 10)).toBeLessThanOrEqual(60)
  })

  it('names the file for the layer and the date', () => {
    expect(imageFileName('air_temperature_max', '2026-11-24')).toBe('agweather-air_temperature_max-2026-11-24.png')
    expect(imageFileName('late-blight-dsv', '2026-07-01..2026-07-07')).toBe(
      'agweather-late-blight-dsv-2026-07-01_to_2026-07-07.png',
    )
    expect(imageFileName('air_temperature', '2026-11-24T15')).toBe('agweather-air_temperature-2026-11-24T15.png')
  })

  it('reduces the map’s credits to plain text, once each', () => {
    const html =
      '<a href="https://openfreemap.org">OpenFreeMap</a> <a href="https://www.openmaptiles.org/">&copy; OpenMapTiles</a>'
    expect(attributionText([html, html, ''])).toBe('OpenFreeMap © OpenMapTiles')
  })
})
