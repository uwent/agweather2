// The map explorer's catalog of layers (Phase 7 track 2 step 2): `/layers` sorted into what the picker shows.
// Weather layers are grouped by their id's prefix, with an "Other" group so a layer added to the API still shows;
// the degree-day running totals aren't listed (the Degree days tab builds any setting on the `degree_days` layer,
// and the API reads the stored totals where they apply); models are picked by crop, then by group.

import type { LayerInfo } from '@/types/api'

export type Tab = 'weather' | 'degree_days' | 'models'

export type WeatherGroup = { id: string; label: string; layers: LayerInfo[] }

/** Weather groups, in the order shown; a layer goes to the first group with a matching prefix */
export const WEATHER_GROUPS: { id: string; label: string; prefixes: string[] }[] = [
  {
    id: 'temperature',
    label: 'Temperature',
    prefixes: ['air_temperature_', 'hours_temperature_', 'temperature_mean_'],
  },
  { id: 'moisture', label: 'Humidity and dew', prefixes: ['relative_humidity_', 'hours_rh_', 'dew_point_'] },
  {
    id: 'water',
    label: 'Rain and water',
    prefixes: ['precipitation_', 'et0_', 'water_balance'],
  },
  { id: 'soil', label: 'Soil', prefixes: ['soil_temperature_', 'soil_moisture_', 'hours_soil_'] },
  { id: 'snow', label: 'Snow', prefixes: ['snow_'] },
  { id: 'wind', label: 'Wind, sky and pressure', prefixes: ['wind_', 'cloud_', 'surface_pressure', 'shortwave_'] },
  {
    id: 'livestock-chill',
    label: 'Chill and livestock heat stress',
    prefixes: ['chill_', 'utah_chill', 'thi_', 'hours_thi_', 'cci_'],
  },
]

export const OTHER_GROUP = { id: 'other', label: 'Other' }

/** Where each layer of `/layers` goes in the picker: a weather group, the degree-day tab, the models, or (for
 * the climate and terrain layers, which wait for their increment) `later` */
export function placeOf(layer: Pick<LayerInfo, 'id' | 'group' | 'time_axis'>): string {
  if (layer.group === 'model') return 'models'
  if (layer.group === 'degree_days') return 'degree_days'
  if (layer.group === 'running_total' && layer.id.startsWith('dd_')) return 'degree_days'
  if (layer.group === 'climate' || layer.group === 'terrain' || layer.time_axis === 'none') return 'later'
  const group = WEATHER_GROUPS.find((g) => g.prefixes.some((prefix) => layer.id.startsWith(prefix)))
  return group?.id ?? OTHER_GROUP.id
}

/** The weather layers of one time axis (daily or hourly), by group, each group in `/layers`' order */
export function weatherGroups(layers: readonly LayerInfo[], axis: 'day' | 'hour'): WeatherGroup[] {
  const groups = [...WEATHER_GROUPS, OTHER_GROUP].map((g) => ({ id: g.id, label: g.label, layers: [] as LayerInfo[] }))
  for (const layer of layers) {
    if (layer.time_axis !== axis) continue
    const place = placeOf(layer)
    groups.find((g) => g.id === place)?.layers.push(layer)
  }
  return groups.filter((g) => g.layers.length)
}

/** The tab a layer is picked from */
export function tabOf(layer: Pick<LayerInfo, 'id' | 'group' | 'time_axis'>): Tab {
  const place = placeOf(layer)
  if (place === 'models') return 'models'
  if (place === 'degree_days') return 'degree_days'
  return 'weather'
}

/** A shorter name for a weather layer within its group: "Air temperature, daily minimum" stays, the hourly
 * suffix goes (the Daily/Hourly switch says it) */
export function shortTitle(layer: Pick<LayerInfo, 'title' | 'time_axis'>): string {
  return layer.time_axis === 'hour' ? layer.title.replace(/, hourly$/, '') : layer.title
}

/** Layers whose title has every word of `text` in it (any order, any case) */
export function filterLayers<L extends Pick<LayerInfo, 'title' | 'id'>>(layers: readonly L[], text: string): L[] {
  const words = text.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return []
  return layers.filter((layer) => {
    const haystack = `${layer.title} ${layer.id.replace(/[_-]/g, ' ')}`.toLowerCase()
    return words.every((word) => haystack.includes(word))
  })
}

/** A model as `/models` lists it (the fields the picker reads) */
export type ModelSummary = { id: string; name: string; group: string; crop_ids: string[]; summary: string }
/** A crop as `/crops` lists it */
export type CropSummary = { id: string; name: string; models: Record<string, string[]> }

export const MODEL_GROUPS: { id: string; label: string }[] = [
  { id: 'disease', label: 'Diseases' },
  { id: 'insect', label: 'Insects' },
  { id: 'crop', label: 'Crop stages' },
  { id: 'agronomic', label: 'Other' },
]

/** The crops that have at least one model, by name */
export function cropsWithModels(crops: readonly CropSummary[]): CropSummary[] {
  return crops
    .filter((crop) => Object.values(crop.models).some((ids) => ids.length))
    .sort((a, b) => a.name.localeCompare(b.name))
}

export type ModelChoice = { id: string; name: string; mapped: boolean }

/** A crop's models by group, each marked mapped (a layer exists) or not ("Available at a site") */
export function cropModels(
  crop: CropSummary,
  models: readonly ModelSummary[],
  layers: readonly Pick<LayerInfo, 'id'>[],
): { id: string; label: string; models: ModelChoice[] }[] {
  const mapped = new Set(layers.map((l) => l.id))
  return MODEL_GROUPS.map((group) => ({
    ...group,
    models: (crop.models[group.id] ?? [])
      .map((id) => ({
        id,
        name: models.find((m) => m.id === id)?.name ?? id,
        mapped: mapped.has(id),
      }))
      .sort((a, b) => Number(b.mapped) - Number(a.mapped) || a.name.localeCompare(b.name)),
  })).filter((group) => group.models.length)
}

/** A model layer's outputs in the order a reader wants them: the risk level or stage first, then the rest */
export function orderedOutputs<O extends { name: string }>(outputs: readonly O[]): O[] {
  const rank = (name: string) => (name === 'risk_level' ? 0 : name === 'stage' ? 1 : name === 'risk_value' ? 2 : 3)
  return [...outputs].sort((a, b) => rank(a.name) - rank(b.name))
}

/** The first crop that has a model, for a model layer picked without one */
export function cropOf(modelId: string, crops: readonly CropSummary[]): string | null {
  return crops.find((crop) => Object.values(crop.models).some((ids) => ids.includes(modelId)))?.id ?? null
}

/** A degree-day preset as `/degree-days/presets` gives it (the fields the builder reads) */
export type DegreeDayPreset = {
  id: string
  label: string
  method: string
  dd: { us: string; metric: string }
  base: { us: number; metric: number }
  upper: { us: number | null; metric: number | null } | null
  starts: string | null
  biofix: string | null
  model: string | null
}

/** A degree-day setting in °F from its parts: `modified_50_86`, `sine_48`, `average_39p2` */
export function ddSetting(method: string, base: number, upper: number | null): string {
  const part = (value: number) => String(Number(value.toFixed(1))).replace('.', 'p')
  return upper === null ? `${method}_${part(base)}` : `${method}_${part(base)}_${part(upper)}`
}

/** A setting's parts back: `modified_50_86` → modified, 50, 86 */
export function ddParts(setting: string): { method: string; base: number; upper: number | null } | null {
  const match = /^(sine|modified|average)_([\dp.]+)(?:_([\dp.]+))?$/.exec(setting)
  if (!match) return null
  const number = (text: string) => Number(text.replace('p', '.'))
  return { method: match[1], base: number(match[2]), upper: match[3] === undefined ? null : number(match[3]) }
}

export const DD_METHODS: { value: string; label: string }[] = [
  { value: 'sine', label: 'Single sine' },
  { value: 'modified', label: 'Modified (limited to the base and upper)' },
  { value: 'average', label: 'Simple average' },
]

/** "Modified, 50 to 86 °F" */
export function ddLabel(setting: string): string {
  const parts = ddParts(setting)
  if (!parts) return setting
  const method = { sine: 'Single sine', modified: 'Modified', average: 'Simple average' }[parts.method] ?? parts.method
  return parts.upper === null ? `${method}, base ${parts.base} °F` : `${method}, ${parts.base} to ${parts.upper} °F`
}
