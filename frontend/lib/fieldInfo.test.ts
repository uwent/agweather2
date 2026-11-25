// Ported from WISP 3 (adapted): app/frontend/lib/fieldInfo.test.ts
import { describe, expect, it } from 'vitest'

import { FIELD_INFO, fieldInfo, type FieldInfoKey } from './fieldInfo'
import { units } from './units'

const keys = Object.keys(FIELD_INFO) as FieldInfoKey[]

// Every .svelte and .ts file under frontend/ except this module and its test (read through Vite, which
// the frontend's types know, where WISP 3 reads them with node:fs)
const files = import.meta.glob<string>(['../**/*.{svelte,ts}', '!./fieldInfo.ts', '!./fieldInfo.test.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
})
const sources = Object.values(files).join('\n')

describe('fieldInfo', () => {
  it.each(keys)('%s is at most two sentences, in either unit system', (key) => {
    for (const system of ['imperial', 'metric'] as const) {
      const { text } = fieldInfo(key, units(system))
      const sentences = text.split(/[.!?](?:\s|$)/).filter((part) => part.trim())
      expect(sentences.length).toBeLessThanOrEqual(2)
      expect(text).toMatch(/[.!?]$/)
    }
  })

  it.each(keys)('%s is used in a form', (key) => {
    expect(sources).toMatch(new RegExp(`['"]${key.replace('.', '\\.')}['"]`))
  })

  it('names glossary terms that exist', () => {
    for (const key of keys) expect(() => fieldInfo(key, units('imperial'))).not.toThrow()
  })
})
