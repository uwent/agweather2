// The model catalog's sections (`/models`): models by crop, then group, filtered by crop, group and words. A model
// for several crops is listed under each; one for no crop goes under "Other models" at the end.

import type { CatalogModel, NamedId } from '@/types'

export type CatalogGroup = { group: NamedId; models: CatalogModel[] }
export type CatalogSection = { id: string; name: string; groups: CatalogGroup[] }
export type CatalogFilter = { crop: string; group: string; query: string }

export const NO_CROP = 'other'

/** Whether a model's name or summary holds every word typed, ignoring case */
export function matchesQuery(model: CatalogModel, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const text = `${model.name} ${model.summary}`.toLowerCase()
  return words.every((word) => text.includes(word))
}

export function catalogSections(
  models: CatalogModel[],
  crops: NamedId[],
  groups: NamedId[],
  filter: CatalogFilter,
): CatalogSection[] {
  const shown = models.filter((m) => (!filter.group || m.group === filter.group) && matchesQuery(m, filter.query))
  const places = [...crops, { id: NO_CROP, name: 'Other models' }]
  return places
    .filter((crop) => !filter.crop || crop.id === filter.crop)
    .map((crop) => {
      const forCrop = shown.filter((m) => (crop.id === NO_CROP ? m.crops.length === 0 : m.crops.includes(crop.id)))
      return {
        id: crop.id,
        name: crop.name,
        groups: groups
          .map((group) => ({ group, models: forCrop.filter((m) => m.group === group.id) }))
          .filter((g) => g.models.length > 0),
      }
    })
    .filter((section) => section.groups.length > 0)
}

/** How many different models the sections list (a model under two crops counts once) */
export function modelCount(sections: CatalogSection[]): number {
  return new Set(sections.flatMap((s) => s.groups.flatMap((g) => g.models.map((m) => m.id)))).size
}
