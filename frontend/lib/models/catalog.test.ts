import { describe, expect, it } from 'vitest'

import type { CatalogModel } from '@/types'

import { catalogSections, matchesQuery, modelCount } from './catalog'

const model = (id: string, group: CatalogModel['group'], crops: string[], summary = ''): CatalogModel => ({
  id,
  name: id.replace(/-/g, ' '),
  group,
  crops,
  summary,
  status: 'beta',
})

const MODELS = [
  model('late-blight', 'disease', ['potato', 'tomato'], 'Late blight risk from leaf wetness.'),
  model('potato-stages', 'crop', ['potato']),
  model('colorado-potato-beetle', 'insect', ['potato', 'tomato']),
  model('oak-wilt', 'insect', []),
]
const CROPS = [
  { id: 'potato', name: 'Potato' },
  { id: 'tomato', name: 'Tomato' },
]
const GROUPS = [
  { id: 'disease', name: 'Diseases' },
  { id: 'insect', name: 'Insects' },
  { id: 'crop', name: 'Crop growth stages' },
]
const ALL = { crop: '', group: '', query: '' }

describe('the model catalog', () => {
  it('lists models by crop, then group, with no-crop models last', () => {
    const sections = catalogSections(MODELS, CROPS, GROUPS, ALL)
    expect(sections.map((s) => s.name)).toEqual(['Potato', 'Tomato', 'Other models'])
    expect(sections[0].groups.map((g) => [g.group.id, g.models.map((m) => m.id)])).toEqual([
      ['disease', ['late-blight']],
      ['insect', ['colorado-potato-beetle']],
      ['crop', ['potato-stages']],
    ])
    expect(modelCount(sections)).toBe(4)
  })

  it('filters by crop, group and every word typed', () => {
    expect(catalogSections(MODELS, CROPS, GROUPS, { ...ALL, crop: 'tomato' }).map((s) => s.id)).toEqual(['tomato'])
    const insects = catalogSections(MODELS, CROPS, GROUPS, { ...ALL, group: 'insect' })
    expect(modelCount(insects)).toBe(2)
    expect(matchesQuery(MODELS[0], 'LEAF blight')).toBe(true)
    expect(matchesQuery(MODELS[0], 'leaf beetle')).toBe(false)
    expect(catalogSections(MODELS, CROPS, GROUPS, { ...ALL, query: 'nothing like this' })).toEqual([])
  })
})
