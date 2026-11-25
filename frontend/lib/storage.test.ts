// Ported from WISP 3: app/frontend/lib/storage.test.ts
import { afterEach, describe, expect, it, vi } from 'vitest'

import { readStored, writeStored } from './storage'

describe('stored settings', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('reads back what was written', () => {
    expect(writeStored('a', { north: true })).toBe(true)
    expect(readStored('a')).toEqual({ north: true })
    writeStored('b', false)
    expect(readStored('b')).toBe(false)
  })

  it('is undefined when nothing is saved', () => {
    expect(readStored('missing')).toBeUndefined()
  })

  it('reads text saved before settings were JSON as that text', () => {
    localStorage.setItem('order', 'name')
    expect(readStored('order')).toBe('name')
    localStorage.setItem('open', 'true')
    expect(readStored('open')).toBe(true)
  })

  it('carries on when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(readStored('a')).toBeUndefined()
    expect(writeStored('a', 1)).toBe(false)
  })
})
