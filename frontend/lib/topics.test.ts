import { describe, expect, it } from 'vitest'

import { NO_CROP, topicCount, topicSections } from '@/lib/topics'
import type { NamedId, TopicEntry } from '@/types'

const topics: TopicEntry[] = [
  { id: 'corn', title: 'Corn', kind: 'crop', scientific_name: 'Zea mays', crops: ['corn'] },
  { id: 'tar-spot', title: 'Tar Spot', kind: 'disease', scientific_name: 'Phyllachora maydis', crops: ['corn'] },
  {
    id: 'european-corn-borer',
    title: 'European Corn Borer',
    kind: 'insect',
    scientific_name: 'Ostrinia nubilalis',
    crops: ['corn', 'potato'],
  },
  { id: 'degree-days', title: 'Degree Days', kind: 'weather', scientific_name: null, crops: [] },
]
const crops: NamedId[] = [
  { id: 'corn', name: 'Corn' },
  { id: 'potato', name: 'Potato' },
]
const kinds: NamedId[] = [
  { id: 'crop', name: 'The crop' },
  { id: 'disease', name: 'Diseases' },
  { id: 'insect', name: 'Insects' },
  { id: 'weather', name: 'Weather' },
]

describe('topicSections', () => {
  it('lists topics by crop, then kind, and topics of no crop last', () => {
    const sections = topicSections(topics, crops, kinds, { crop: '', query: '' })
    expect(sections.map((s) => s.id)).toEqual(['corn', 'potato', NO_CROP])
    expect(sections[0].groups.map((g) => g.kind.id)).toEqual(['crop', 'disease', 'insect'])
    expect(sections[1].groups.flatMap((g) => g.topics.map((t) => t.id))).toEqual(['european-corn-borer'])
    expect(topicCount(sections)).toBe(4)
  })

  it('filters by crop and by words in the title or scientific name', () => {
    expect(topicSections(topics, crops, kinds, { crop: 'potato', query: '' }).map((s) => s.id)).toEqual(['potato'])
    const found = topicSections(topics, crops, kinds, { crop: '', query: 'ostrinia' })
    expect(topicCount(found)).toBe(1)
    expect(found.map((s) => s.id)).toEqual(['corn', 'potato'])
    expect(topicSections(topics, crops, kinds, { crop: '', query: 'nothing here' })).toEqual([])
  })
})
