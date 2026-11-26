<script lang="ts">
  import { untrack } from 'svelte'

  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import type { LayerInfo } from '@/types/api'

  import {
    cropModels,
    cropsWithModels,
    type CropSummary,
    type DegreeDayPreset,
    filterLayers,
    type ModelSummary,
    shortTitle,
    type Tab,
    tabOf,
    weatherGroups,
  } from './catalog'
  import DegreeDays from './DegreeDays.svelte'
  import type { ExplorerView } from './view'

  // What the map shows (Phase 7 track 2 step 2): weather by group (daily or hourly), degree days for any setting,
  // or a crop's diseases, insects and stages; a filter over every title finds any of them.
  let {
    view,
    layers,
    models,
    crops,
    presets,
    onchange,
  }: {
    view: ExplorerView
    layers: LayerInfo[]
    models: ModelSummary[]
    crops: CropSummary[]
    presets: DegreeDayPreset[]
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const current = $derived(layers.find((l) => l.id === view.layer))
  // A crop-stage model counting degree days from planting belongs to the Degree days tab
  const currentTab = $derived<Tab>(
    current
      ? current.group === 'model' && view.dd && /^g?dd_total$/.test(view.output ?? '')
        ? 'degree_days'
        : tabOf(current)
      : 'weather',
  )
  let tab = $derived<Tab>(currentTab)

  let axis = $state<'day' | 'hour'>(untrack(() => (current?.time_axis === 'hour' ? 'hour' : 'day')))
  const groups = $derived(weatherGroups(layers, axis))

  const cropList = $derived(cropsWithModels(crops))
  // The view's crop, else (a shared link to a model) the first crop the map's model is for, else corn
  const crop = $derived(
    cropList.find((c) => c.id === view.crop) ??
      (current?.group === 'model'
        ? cropList.find((c) => Object.values(c.models).some((ids) => ids.includes(current.id)))
        : undefined) ??
      cropList.find((c) => c.id === 'corn') ??
      cropList[0],
  )
  const cropGroups = $derived(crop ? cropModels(crop, models, layers) : [])

  let filter = $state('')
  const found = $derived(
    filterLayers(
      layers.filter((l) => tabOf(l) !== 'degree_days' || l.id === 'degree_days'),
      filter,
    ).slice(0, 12),
  )

  function pick(layer: LayerInfo) {
    const changes: Partial<ExplorerView> = { layer: layer.id, output: null }
    if (layer.group === 'degree_days') changes.dd = view.dd ?? 'modified_50_86'
    onchange(changes)
    filter = ''
  }

  function pickWeather(id: string) {
    const layer = layers.find((l) => l.id === id)
    if (layer) pick(layer)
  }

  function switchAxis(next: 'day' | 'hour') {
    axis = next
    const first = weatherGroups(layers, next)[0]?.layers[0]
    // The same measure on the other axis where there's one (air temperature, daily minimum → hourly)
    const stem = (id: string) => id.replace(/_(hourly|min|max|mean|sum)$/, '')
    const twin =
      current && groups.flatMap((g) => g.layers).length
        ? weatherGroups(layers, next)
            .flatMap((g) => g.layers)
            .find((l) => stem(l.id) === stem(current.id))
        : undefined
    const target = twin ?? first
    if (target) pick(target)
  }

  const tabs: { value: Tab; label: string }[] = [
    { value: 'weather', label: 'Weather' },
    { value: 'degree_days', label: 'Degree days' },
    { value: 'models', label: 'Crops and pests' },
  ]
</script>

<section class="space-y-3" aria-labelledby="picker-heading">
  <h2 id="picker-heading" class="text-base font-semibold">What to map</h2>

  <div class="space-y-1">
    <label for="layer-filter" class="block text-sm font-medium">Find a map</label>
    <input
      id="layer-filter"
      type="search"
      class="block w-full rounded-md sm:text-sm"
      placeholder="Such as rain, frost or tar spot"
      bind:value={filter}
      aria-controls={filter.trim() ? 'layer-filter-results' : undefined}
    />
    {#if filter.trim()}
      <ul id="layer-filter-results" class="divide-y divide-line rounded-md border border-line bg-surface text-sm">
        {#each found as layer (layer.id)}
          <li>
            <button type="button" class="w-full px-2 py-1.5 text-left hover:bg-brand-50" onclick={() => pick(layer)}>
              {layer.title}
            </button>
          </li>
        {:else}
          <li class="px-2 py-1.5 text-ink-muted">No map's name has all of those words.</li>
        {/each}
      </ul>
    {/if}
  </div>

  <SegmentedChoice
    legend="Kind of map"
    name="picker-tab"
    options={tabs}
    value={tab}
    onchange={(next) => (tab = next)}
  />

  {#if tab === 'weather'}
    <div class="space-y-2">
      <SegmentedChoice
        legend="Daily or hourly"
        name="picker-axis"
        options={[
          { value: 'day', label: 'Daily' },
          { value: 'hour', label: 'Hourly' },
        ]}
        value={axis}
        onchange={switchAxis}
      />
      <div class="space-y-1">
        <label for="weather-layer" class="block text-sm font-medium">Weather</label>
        <select
          id="weather-layer"
          class="block w-full rounded-md sm:text-sm"
          value={current && tabOf(current) === 'weather' ? current.id : ''}
          onchange={(event) => pickWeather(event.currentTarget.value)}
        >
          {#if !current || tabOf(current) !== 'weather'}<option value="" disabled>Choose a measure</option>{/if}
          {#each groups as group (group.id)}
            <optgroup label={group.label}>
              {#each group.layers as layer (layer.id)}<option value={layer.id}>{shortTitle(layer)}</option>{/each}
            </optgroup>
          {/each}
        </select>
      </div>
    </div>
  {:else if tab === 'degree_days'}
    <DegreeDays {view} {presets} {layers} {onchange} />
  {:else}
    <div class="space-y-2">
      <div class="space-y-1">
        <label for="picker-crop" class="block text-sm font-medium">Crop</label>
        <select
          id="picker-crop"
          class="block w-full rounded-md sm:text-sm"
          value={crop?.id}
          onchange={(event) => onchange({ crop: event.currentTarget.value })}
        >
          {#each cropList as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </div>
      {#each cropGroups as group (group.id)}
        <fieldset>
          <legend class="text-sm font-medium">{group.label}</legend>
          <ul class="mt-1 space-y-0.5 text-sm">
            {#each group.models as model (model.id)}
              <li>
                {#if model.mapped}
                  <label class="flex items-center gap-2">
                    <input
                      type="radio"
                      name="picker-model"
                      checked={view.layer === model.id}
                      onchange={() => onchange({ layer: model.id, output: null, crop: crop?.id ?? null })}
                    />
                    {model.name}
                  </label>
                {:else}
                  <span class="flex items-center gap-2 pl-6 text-ink-muted">
                    {model.name}<span class="text-xs">(available at a site)</span>
                  </span>
                {/if}
              </li>
            {/each}
          </ul>
        </fieldset>
      {/each}
    </div>
  {/if}
</section>
