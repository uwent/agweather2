import { describe, expect, it } from 'vitest'

import { RISK_STEPS, riskColor, riskRank, riskSteps } from './riskLevels'

// Read with Node's fs (as charts/palette.test.ts does), to hold these colors to the API's map palettes
type Fs = { readFileSync: (path: URL, encoding: 'utf8') => string }
const fs = (globalThis as unknown as { process: { getBuiltinModule: (id: string) => Fs } }).process.getBuiltinModule(
  'node:fs',
)
const read = (path: string) => fs.readFileSync(new URL(path, import.meta.url), 'utf8')
const dataCss = read('../entrypoints/data.css')
const palettesPy = read('../../packages/agdata/src/agdata/palettes.py')

function apiPalette(id: string): string[] {
  const block = palettesPy.match(new RegExp(`id="${id}",[\\s\\S]*?colors=\\[([^\\]]*)\\]`))
  if (!block) throw new Error(`no palette ${id} in palettes.py`)
  return [...block[1].matchAll(/"(#[0-9a-f]{6})"/gi)].map((m) => m[1].toLowerCase())
}

/** The color a riskColor() token stands for in data.css (light mode; the risk colors are the same in dark) */
function resolved(color: string | undefined): string | undefined {
  const name = color?.match(/^var\(--(.*)\)$/)?.[1]
  return name ? dataCss.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6});`, 'i'))?.[1].toLowerCase() : undefined
}

const five = ['Very low', 'Low', 'Moderate', 'High', 'Very high']
const colors = (scale: readonly string[]) => scale.map((_, k) => resolved(riskColor(k, scale)))

describe('risk colors', () => {
  it('give a scale of three levels a subset of the five levels’ colors, the same color for the same name', () => {
    const fiveColors = colors(five)
    expect(fiveColors).toEqual(apiPalette('BuYlRd_5'))
    for (const scale of [
      ['Low', 'Moderate', 'High'],
      ['Low', 'High', 'Extreme'],
      ['Low', 'Infection'],
    ]) {
      const found = colors(scale)
      expect(fiveColors).toEqual(expect.arrayContaining(found))
      scale.forEach((name, k) => {
        if (five.includes(name)) expect(found[k]).toBe(fiveColors[five.indexOf(name)])
      })
    }
  })

  it('match the map’s palettes for each scale', () => {
    expect(colors(['Low', 'Moderate', 'High'])).toEqual(apiPalette('LbYlOr_3'))
    expect(colors(['Low', 'High', 'Extreme'])).toEqual(apiPalette('LbOrRd_3'))
    expect(colors(['Low', 'Infection'])).toEqual(apiPalette('LbRd_2'))
    expect(colors(['Very low', 'Low', 'Moderate', 'High'])).toEqual(apiPalette('BuYlRd_4'))
  })

  it("follow agdata's table of steps by name", () => {
    const table = palettesPy.match(/RISK_STEPS = \{([^}]*)\}/)![1]
    const python = Object.fromEntries([...table.matchAll(/"([^"]+)": (\d)/g)].map((m) => [m[1], Number(m[2])]))
    expect(RISK_STEPS).toEqual(python)
  })

  it('read a count alone as Low, Moderate, High (or Low and Very high), and leave a missing level blank', () => {
    expect(riskSteps(3)).toEqual([1, 2, 3])
    expect(riskSteps(2)).toEqual([1, 4])
    expect(riskSteps(['Low', 'Unknown', 'High'])).toEqual([1, 2, 3])
    expect(riskColor(null, 5)).toBeUndefined()
    expect(riskColor(9, ['Low', 'High', 'Extreme'])).toBe('var(--color-risk-severity-5)')
    expect(riskRank(2, ['Low', 'High', 'Extreme'])).toBe(1)
  })
})
