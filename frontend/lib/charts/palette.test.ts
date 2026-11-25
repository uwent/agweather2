// WISP 3: app/frontend/lib/charts/palette.test.ts (adapted: readPalette's tokens, and the risk colors held to the API's)
import { afterEach, describe, expect, it, vi } from 'vitest'

import { hex, readPalette } from './palette'

// Read with Node's fs, which tests run in (Vite's ?raw gives CSS as empty under vitest), without Node's types in
// the frontend's program
type Fs = { readFileSync: (path: URL, encoding: 'utf8') => string }
const fs = (globalThis as unknown as { process: { getBuiltinModule: (id: string) => Fs } }).process.getBuiltinModule(
  'node:fs',
)
const read = (path: string) => fs.readFileSync(new URL(path, import.meta.url), 'utf8')
const dataCss = read('../../entrypoints/data.css')
const palettesPy = read('../../../packages/agdata/src/agdata/palettes.py')

// jsdom has no matchMedia
vi.mock('../theme', () => ({ currentTheme: () => 'light' }))

/** A categorical palette's colors in agdata's palettes.py, by id */
function apiPalette(id: string): string[] {
  const block = palettesPy.match(new RegExp(`id="${id}",[\\s\\S]*?colors=\\[([^\\]]*)\\]`))
  if (!block) throw new Error(`no palette ${id} in palettes.py`)
  return [...block[1].matchAll(/"(#[0-9a-f]{6})"/gi)].map((m) => m[1].toLowerCase())
}

/** A token's value in data.css's @theme static block (light mode) */
function token(name: string): string | undefined {
  return dataCss.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6});`, 'i'))?.[1].toLowerCase()
}

afterEach(() => {
  document.documentElement.removeAttribute('style')
  vi.restoreAllMocks()
})

describe('hex', () => {
  it("writes readPalette's rgb as #rrggbb, and leaves hex as it is", () => {
    expect(hex('rgb(46, 196, 240)')).toBe('#2ec4f0')
    expect(hex('rgb(0, 0, 0)')).toBe('#000000')
    expect(hex('#888888')).toBe('#888888')
  })
})

describe('risk colors', () => {
  it("are the API's categorical palettes, level by level", () => {
    const severity = [1, 2, 3, 4, 5].map((i) => token(`color-risk-severity-${i}`))
    const probability = [1, 2, 3, 4].map((i) => token(`color-risk-probability-${i}`))
    expect(severity).toEqual(apiPalette('BuYlRd_5'))
    expect(probability).toEqual(apiPalette('BuYlRd_4'))
  })
})

describe('readPalette', () => {
  it('reads the chart tokens and the risk levels, and falls back to gray for one not set', () => {
    // jsdom has no canvas: colors come back as written
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
    const root = document.documentElement
    root.style.setProperty('--color-chart-temperature-max', '#eb6834')
    root.style.setProperty('--color-chart-precipitation', '#1c5cab')
    root.style.setProperty('--color-risk-severity-5', '#a50026')
    root.style.setProperty('--color-risk-probability-1', '#4575b4')
    const palette = readPalette()
    expect(palette.temperature.max).toBe('#eb6834')
    expect(palette.precipitation).toBe('#1c5cab')
    expect(palette.severity).toHaveLength(5)
    expect(palette.severity[4]).toBe('#a50026')
    expect(palette.probability).toHaveLength(4)
    expect(palette.probability[0]).toBe('#4575b4')
    expect(palette.et).toBe('#888888')
  })
})
