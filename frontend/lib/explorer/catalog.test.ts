import { describe, expect, it } from 'vitest'

import crops from '@/test/fixtures/crops.json'
import layers from '@/test/fixtures/layers.json'
import models from '@/test/fixtures/models.json'
import type { LayerInfo } from '@/types/api'

import {
  cropModels,
  cropOf,
  CLIMATE_GROUP,
  cropsWithModels,
  type CropSummary,
  ddLabel,
  ddParts,
  ddSetting,
  filterLayers,
  LAND_GROUP,
  OTHER_GROUP,
  orderedOutputs,
  placeOf,
  tabOf,
  WEATHER_GROUPS,
  weatherGroups,
} from './catalog'

const LAYERS = layers.data as LayerInfo[]
const CROPS = crops.data as CropSummary[]

describe('the layer catalog', () => {
  it('puts every layer of /layers somewhere', () => {
    const places = new Set([
      ...[...WEATHER_GROUPS, OTHER_GROUP, CLIMATE_GROUP, LAND_GROUP].map((g) => g.id),
      'models',
      'degree_days',
    ])
    for (const layer of LAYERS) expect(places, layer.id).toContain(placeOf(layer))
  })

  it('needs no Other group for today’s weather layers, and still shows a new one there', () => {
    const others = LAYERS.filter((layer) => placeOf(layer) === OTHER_GROUP.id).map((l) => l.id)
    expect(others).toEqual([])
    const added = { ...LAYERS[0], id: 'leaf_wetness_hours', title: 'Leaf wetness' }
    const groups = weatherGroups([...LAYERS, added], 'day')
    expect(groups.find((g) => g.label === 'Other')?.layers.map((l) => l.id)).toEqual(['leaf_wetness_hours'])
  })

  it('lists the freeze maps in a Climate group and elevation under Land, after the daily weather', () => {
    const groups = weatherGroups(LAYERS, 'day')
    expect(groups.slice(-2).map((g) => [g.label, g.layers.map((l) => l.id)])).toEqual([
      ['Climate', ['freeze_chance', 'freeze_dates']],
      ['Land', ['elevation']],
    ])
    expect(weatherGroups(LAYERS, 'hour').some((g) => g.id === 'climate')).toBe(false)
    expect(tabOf(LAYERS.find((l) => l.id === 'freeze_dates')!)).toBe('weather')
  })

  it('lists every daily and hourly weather layer once, and no degree-day total', () => {
    const daily = weatherGroups(LAYERS, 'day').flatMap((g) => g.layers.map((l) => l.id))
    const hourly = weatherGroups(LAYERS, 'hour').flatMap((g) => g.layers.map((l) => l.id))
    expect(new Set(daily).size).toBe(daily.length)
    expect(daily).toContain('air_temperature_min')
    expect(daily).toContain('precipitation_total')
    expect(daily.some((id) => id.startsWith('dd_'))).toBe(false)
    expect(hourly).toHaveLength(LAYERS.filter((l) => l.time_axis === 'hour').length)
  })

  it('picks each layer from its tab', () => {
    const tab = (id: string) => tabOf(LAYERS.find((l) => l.id === id)!)
    expect(tab('air_temperature_max')).toBe('weather')
    expect(tab('degree_days')).toBe('degree_days')
    expect(tab('dd_modified_50_86')).toBe('degree_days')
    expect(tab('tar-spot')).toBe('models')
  })

  it('filters titles by every word typed', () => {
    const found = filterLayers(LAYERS, 'soil 10 cm min').map((l) => l.id)
    expect(found).toEqual(['soil_temperature_10cm_min'])
    expect(filterLayers(LAYERS, '  ')).toEqual([])
    expect(filterLayers(LAYERS, 'TAR SPOT').map((l) => l.id)).toEqual(['tar-spot'])
  })
})

describe('models by crop', () => {
  it('lists only crops with models, by name', () => {
    const listed = cropsWithModels(CROPS)
    expect(listed.length).toBeGreaterThan(20)
    expect(listed.map((c) => c.id)).not.toContain('barley')
    expect(listed.map((c) => c.name)).toEqual([...listed.map((c) => c.name)].sort((a, b) => a.localeCompare(b)))
  })

  it('groups a crop’s models, mapped first, and marks those without a map', () => {
    const corn = CROPS.find((c) => c.id === 'corn')!
    const groups = cropModels(corn, models.data, LAYERS)
    expect(groups.map((g) => g.id)).toEqual(['disease', 'insect', 'crop'])
    expect(groups[0].models.map((m) => m.id)).toContain('tar-spot')
    expect(groups.flatMap((g) => g.models).every((m) => m.mapped)).toBe(true)
    const unmapped = cropModels(
      corn,
      models.data,
      LAYERS.filter((l) => l.id !== 'tar-spot'),
    )
    expect(unmapped[0].models.at(-1)).toEqual({ id: 'tar-spot', name: 'Tar spot risk', mapped: false })
  })

  it('finds a crop for a model picked without one', () => {
    expect(cropOf('late-blight-dsv', CROPS)).toBe('potato')
    expect(cropOf('nothing', CROPS)).toBeNull()
  })

  it('puts the risk level or stage first among outputs', () => {
    const names = (list: { name: string }[]) => orderedOutputs(list).map((o) => o.name)
    expect(names([{ name: 'dd_total' }, { name: 'risk_value' }, { name: 'risk_level' }])).toEqual([
      'risk_level',
      'risk_value',
      'dd_total',
    ])
    expect(names([{ name: 'gdd' }, { name: 'stage' }])).toEqual(['stage', 'gdd'])
  })
})

describe('degree-day settings', () => {
  it('writes and reads a setting', () => {
    expect(ddSetting('modified', 50, 86)).toBe('modified_50_86')
    expect(ddSetting('sine', 39.2, null)).toBe('sine_39p2')
    expect(ddParts('average_39p2')).toEqual({ method: 'average', base: 39.2, upper: null })
    expect(ddParts('sine_50_86')).toEqual({ method: 'sine', base: 50, upper: 86 })
    expect(ddParts('nonsense')).toBeNull()
  })

  it('names a setting in words', () => {
    expect(ddLabel('modified_50_86')).toBe('Modified, 50 to 86 °F')
    expect(ddLabel('sine_41')).toBe('Single sine, base 41 °F')
  })
})
