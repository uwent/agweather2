// The layers /data offers as map files (track 7 step 7.1), grouped for a select: daily weather by the explorer's
// groups, running totals (degree days among them), each model, elevation, then hourly weather. The `degree_days`
// layer (any setting) and the climate layers, which need settings of their own, are left to the map explorer.

import type { LayerInfo } from '@/types/api'

import { shortTitle, weatherGroups } from '../explorer/catalog'

export type LayerGroup = { label: string; layers: { id: string; title: string }[] }

export function layerGroups(layers: readonly LayerInfo[]): LayerGroup[] {
  const titled = (list: readonly LayerInfo[]) => list.map((l) => ({ id: l.id, title: shortTitle(l) }))
  const byTitle = (list: LayerInfo[]) => list.sort((a, b) => a.title.localeCompare(b.title))
  const weather = layers.filter((l) => l.group === 'weather')
  const groups: LayerGroup[] = weatherGroups(weather, 'day').map((g) => ({ label: g.label, layers: titled(g.layers) }))
  groups.push({ label: 'Running totals', layers: titled(layers.filter((l) => l.group === 'running_total')) })
  groups.push({ label: 'Models', layers: titled(byTitle(layers.filter((l) => l.group === 'model'))) })
  groups.push({ label: 'Terrain', layers: titled(layers.filter((l) => l.group === 'terrain')) })
  for (const g of weatherGroups(weather, 'hour'))
    groups.push({ label: `${g.label}, hourly`, layers: titled(g.layers) })
  return groups.filter((g) => g.layers.length)
}
