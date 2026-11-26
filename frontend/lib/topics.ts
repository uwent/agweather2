// The topics index's sections (`/topics`): topic pages by crop, then kind (the crop itself first, then diseases,
// insects and field management), filtered by crop and words. A topic for several crops is listed under each; one
// for no crop goes under "Other topics" at the end.

import type { NamedId, TopicEntry } from '@/types'

export type TopicGroup = { kind: NamedId; topics: TopicEntry[] }
export type TopicSection = { id: string; name: string; groups: TopicGroup[] }
export type TopicFilter = { crop: string; query: string }

export const NO_CROP = 'other'

/** Whether a topic's title or scientific name holds every word typed, ignoring case */
export function matchesQuery(topic: TopicEntry, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const text = `${topic.title} ${topic.scientific_name ?? ''}`.toLowerCase()
  return words.every((word) => text.includes(word))
}

export function topicSections(
  topics: TopicEntry[],
  crops: NamedId[],
  kinds: NamedId[],
  filter: TopicFilter,
): TopicSection[] {
  const shown = topics.filter((t) => matchesQuery(t, filter.query))
  const places = [...crops, { id: NO_CROP, name: 'Other topics' }]
  return places
    .filter((crop) => !filter.crop || crop.id === filter.crop)
    .map((crop) => {
      const forCrop = shown.filter((t) => (crop.id === NO_CROP ? t.crops.length === 0 : t.crops.includes(crop.id)))
      return {
        id: crop.id,
        name: crop.name,
        groups: kinds
          .map((kind) => ({ kind, topics: forCrop.filter((t) => t.kind === kind.id) }))
          .filter((g) => g.topics.length > 0),
      }
    })
    .filter((section) => section.groups.length > 0)
}

/** How many different topics the sections list (a topic under two crops counts once) */
export function topicCount(sections: TopicSection[]): number {
  return new Set(sections.flatMap((s) => s.groups.flatMap((g) => g.topics.map((t) => t.id)))).size
}
