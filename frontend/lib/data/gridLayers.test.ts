import { describe, expect, it } from 'vitest'

import layersAnswer from '@/test/fixtures/layers.json'
import type { LayerInfo } from '@/types/api'

import { layerGroups } from './gridLayers'

const layers = layersAnswer.data as unknown as LayerInfo[]

describe('the layers offered as files', () => {
  it('groups daily weather first, then running totals, models, terrain and hourly weather', () => {
    const groups = layerGroups(layers)
    const labels = groups.map((g) => g.label)
    expect(labels[0]).toBe('Temperature')
    expect(labels).toContain('Running totals')
    expect(labels).toContain('Models')
    expect(labels.indexOf('Models')).toBeLessThan(labels.findIndex((l) => l.endsWith(', hourly')))
    const ids = groups.flatMap((g) => g.layers.map((l) => l.id))
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toContain('air_temperature_max')
    expect(ids).toContain('late-blight-dsv')
    // The setting-driven degree-day layer and the climate layers stay on the map explorer
    expect(ids).not.toContain('degree_days')
    expect(ids.some((id) => layers.find((l) => l.id === id)?.group === 'climate')).toBe(false)
  })
})
