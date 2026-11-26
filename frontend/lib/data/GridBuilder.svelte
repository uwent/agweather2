<!-- /data's maps as data files (track 7 step 7.1): a layer over the whole area, a state, a county or a box, on a day
     or over a range (each day, or combined into one map), as NetCDF, GeoTIFF, CSV or JSON, on the native grid or a
     latitude and longitude grid. The size, and whether the API takes the request, are said first (./gridSize.ts). -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { DataAreas, DataLimits, GridProjection } from '@/types'
  import type { LayerInfo, LayersResponse } from '@/types/api'

  import { get } from '../api'
  import SegmentedChoice from '../components/SegmentedChoice.svelte'
  import { addDays } from '../dates'
  import Failed from '../components/Failed.svelte'
  import { request } from '../request.svelte'
  import { currentUnits } from '../units'
  import { layerGroups } from './gridLayers'
  import {
    describeEstimate,
    gridEstimate,
    gridUrl,
    parseBox,
    type AreaChoice,
    type GridChoice,
    type GridFormat,
  } from './gridSize'

  let {
    today,
    limits,
    projection,
    areas,
  }: {
    today: string
    limits: DataLimits
    projection: GridProjection
    /** Undefined while they load (a deferred prop), null before the archive has a year */
    areas: DataAreas | null | undefined
  } = $props()

  const id = $props.id()
  const catalog = request<LayersResponse>()
  const loadCatalog = () => catalog.load((signal) => get<LayersResponse>('/layers', undefined, { signal }))
  loadCatalog()
  onDestroy(() => catalog.cancel())

  const layers = $derived<LayerInfo[]>(catalog.value.data?.data ?? [])
  const groups = $derived(layerGroups(layers))
  let layerId = $state('air_temperature_max')
  const layer = $derived(layers.find((l) => l.id === layerId))
  const hourly = $derived(layer?.time_axis === 'hour')
  const timeless = $derived(layer?.time_axis === 'none')

  const yesterday = untrack(() => addDays(today, -1))
  let span = $state<'day' | 'range'>('day')
  let start = $state(yesterday)
  let rangeStart = $state(addDays(yesterday, -29))
  let end = $state(yesterday)
  let combine = $state(false)
  let stat = $state('mean')
  const stats = $derived(layer?.stats ?? [])
  $effect(() => {
    // A layer without the chosen statistic takes its first
    if (stats.length && !stats.includes(untrack(() => stat))) stat = stats[0]
  })

  let areaKind = $state<AreaChoice['kind']>('whole')
  let stateId = $state('')
  let countyId = $state('')
  let box = $state({ south: '', west: '', north: '', east: '' })
  let clip = $state(false)
  const states = $derived(areas?.states ?? [])
  const counties = $derived((areas?.counties ?? []).filter((c) => c.state === stateId))
  $effect(() => {
    // The first state (the only one over a development box) until the reader picks
    if (!stateId && states.length) stateId = states.find((s) => s.id === 'WI')?.id ?? states[0].id
  })
  $effect(() => {
    if (counties.length && !counties.some((c) => c.id === untrack(() => countyId))) countyId = counties[0].id
  })
  const area = $derived<AreaChoice>(
    areaKind === 'state'
      ? { kind: 'state', id: stateId }
      : areaKind === 'county'
        ? { kind: 'county', id: countyId }
        : areaKind === 'box'
          ? { kind: 'box', box: parseBox(box) }
          : { kind: 'whole' },
  )

  let format = $state<GridFormat>('netcdf')
  let grid = $state<'native' | 'latlon'>('native')
  let res = $state(0.1)
  let units = $state<'us' | 'metric'>(currentUnits().system === 'metric' ? 'metric' : 'us')

  const choice = $derived<GridChoice | null>(
    layer
      ? {
          layer: { id: layer.id, time_axis: layer.time_axis, stats: layer.stats },
          span,
          start: span === 'day' ? start : rangeStart,
          end,
          stat: span === 'range' && combine && stats.length ? stat : null,
          area,
          clip: areaKind !== 'whole' && clip,
          format,
          grid,
          res,
          stride: 1,
          units,
        }
      : null,
  )
  const estimate = $derived(
    choice && areas ? gridEstimate(choice, { limits, projection, areas }) : null,
  )
  const url = $derived(choice ? gridUrl(choice) : '')
  const fullUrl = $derived(typeof window === 'undefined' ? url : `${window.location.origin}${url}`)
  const waiting = $derived(
    areas === undefined
      ? 'Loading the states and counties…'
      : areas === null
        ? 'Map files aren’t available yet: the archive has no data.'
        : area.kind === 'box' && !area.box
          ? 'Enter the box’s south, west, north and east edges in degrees, south below north and west below east.'
          : null,
  )

  let copied = $state<'yes' | 'failed' | null>(null)
  async function copy() {
    try {
      await navigator.clipboard.writeText(fullUrl)
      copied = 'yes'
    } catch {
      copied = 'failed'
    }
  }
  $effect(() => {
    void fullUrl
    copied = null
  })

  const STAT_LABELS: Record<string, string> = {
    mean: 'Mean',
    min: 'Lowest',
    max: 'Highest',
    sum: 'Total',
    count: 'Days counted',
  }
  const inputClass = 'rounded-md border border-line bg-surface px-2 py-1 text-sm'
  const AREAS: { value: AreaChoice['kind']; label: string }[] = [
    { value: 'whole', label: 'Everything we cover' },
    { value: 'state', label: 'A state' },
    { value: 'county', label: 'A county' },
    { value: 'box', label: 'A box' },
  ]
  const FORMATS: { value: GridFormat; label: string }[] = [
    { value: 'netcdf', label: 'NetCDF' },
    { value: 'geotiff', label: 'GeoTIFF' },
    { value: 'csv', label: 'CSV' },
    { value: 'json', label: 'JSON' },
  ]
</script>

<div class="max-w-4xl space-y-5">
  <label class="flex flex-col gap-1 text-sm">
    <span class="font-medium">Map</span>
    {#if catalog.value.status === 'failed'}
      <Failed {...catalog.value} retry={loadCatalog} />
    {/if}
    <select class="{inputClass} max-w-md" bind:value={layerId} disabled={!layers.length}>
      {#if !layers.length}<option value={layerId}>Loading the maps…</option>{/if}
      {#each groups as group (group.label)}
        <optgroup label={group.label}>
          {#each group.layers as option (option.id)}<option value={option.id}>{option.title}</option>{/each}
        </optgroup>
      {/each}
    </select>
    {#if layer?.description}<span class="max-w-prose text-xs text-ink-muted">{layer.description}</span>{/if}
  </label>

  {#if !timeless}
    <fieldset class="space-y-2">
      <legend class="text-sm font-medium">Days</legend>
      <SegmentedChoice
        legend="Days"
        name="{id}-span"
        options={[
          { value: 'day', label: hourly ? 'One day’s hours' : 'One day' },
          { value: 'range', label: 'A range of days' },
        ]}
        value={span}
        onchange={(next) => (span = next)}
      />
      <div class="flex flex-wrap items-end gap-3 text-sm">
        {#if span === 'day'}
          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-muted">Day</span>
            <input type="date" class={inputClass} bind:value={start} />
          </label>
        {:else}
          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-muted">Start date</span>
            <input type="date" class={inputClass} bind:value={rangeStart} />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-muted">End date</span>
            <input type="date" class={inputClass} bind:value={end} />
          </label>
        {/if}
      </div>
      {#if span === 'range' && stats.length}
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <label class="flex items-center gap-2">
            <input type="checkbox" class="size-4 accent-brand-600" bind:checked={combine} />
            {hourly ? 'Combine the hours into one map:' : 'Combine the days into one map:'}
          </label>
          <select class={inputClass} bind:value={stat} disabled={!combine} aria-label="How to combine them">
            {#each stats as s (s)}<option value={s}>{STAT_LABELS[s] ?? s}</option>{/each}
          </select>
        </div>
      {/if}
      <p class="text-xs text-ink-muted">
        {hourly
          ? 'Each day runs midnight to midnight Central Standard Time. Hours are labeled in UTC, each by the end of its hour.'
          : 'Each day runs midnight to midnight Central Standard Time, the same hours in every cell. Days still to come are the forecast.'}
      </p>
    </fieldset>
  {/if}

  <fieldset class="space-y-2">
    <legend class="text-sm font-medium">Area</legend>
    <div class="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      {#each AREAS as option (option.value)}
        <label class="flex items-center gap-2">
          <input
            type="radio"
            name="{id}-area"
            class="accent-brand-600"
            value={option.value}
            checked={areaKind === option.value}
            onchange={() => (areaKind = option.value)}
          />
          {option.label}
        </label>
      {/each}
    </div>
    {#if areaKind === 'state' || areaKind === 'county'}
      <div class="flex flex-wrap items-end gap-3 text-sm">
        <label class="flex flex-col gap-1">
          <span class="text-xs text-ink-muted">State</span>
          <select class={inputClass} bind:value={stateId} disabled={!states.length}>
            {#each states as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
          </select>
        </label>
        {#if areaKind === 'county'}
          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-muted">County</span>
            <select class={inputClass} bind:value={countyId} disabled={!counties.length}>
              {#each counties as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
            </select>
          </label>
        {/if}
      </div>
    {:else if areaKind === 'box'}
      <div class="grid max-w-xl grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        {#each [['south', 'South'], ['west', 'West'], ['north', 'North'], ['east', 'East']] as [key, label] (key)}
          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-muted">{`${label} edge (°)`}</span>
            <input
              type="text"
              inputmode="decimal"
              class="{inputClass} w-full"
              bind:value={box[key as keyof typeof box]}
              placeholder={{ south: '42.5', west: '-92.9', north: '47.1', east: '-86.8' }[key]}
            />
          </label>
        {/each}
      </div>
      <p class="text-xs text-ink-muted">Latitudes and longitudes in decimal degrees; longitudes west of Greenwich are negative.</p>
    {/if}
    {#if areaKind !== 'whole'}
      <label class="flex items-start gap-2 text-sm">
        <input type="checkbox" class="mt-0.5 size-4 accent-brand-600" bind:checked={clip} />
        <span>
          Only the cells in the area
          <span class="block text-xs text-ink-muted">
            A file covers the rectangle around the area; with this, the cells outside it are left empty, and CSV and JSON
            leave them out.
          </span>
        </span>
      </label>
    {/if}
  </fieldset>

  <div class="flex flex-wrap gap-x-6 gap-y-3">
    <SegmentedChoice legend="Format" name="{id}-format" showLegend options={FORMATS} value={format} onchange={(next) => (format = next)} />
    <SegmentedChoice
      legend="Grid"
      name="{id}-grid"
      showLegend
      options={[
        { value: 'native', label: '2.5 km (as stored)' },
        { value: 'latlon', label: 'Latitude and longitude' },
      ]}
      value={grid}
      onchange={(next) => (grid = next)}
    />
    {#if grid === 'latlon'}
      <label class="flex items-center gap-2 text-xs text-ink-muted">
        Spacing
        <select class={inputClass} bind:value={res}>
          <option value={0.05}>0.05°</option>
          <option value={0.1}>0.1°</option>
          <option value={0.25}>0.25°</option>
        </select>
      </label>
    {/if}
    <SegmentedChoice
      legend="Units"
      name="{id}-units"
      showLegend
      options={[
        { value: 'us', label: 'US (°F, inches)' },
        { value: 'metric', label: 'Metric (°C, mm)' },
      ]}
      value={units}
      onchange={(next) => (units = next)}
    />
  </div>

  <section class="space-y-2 rounded-md border border-line bg-surface-raised p-3" aria-labelledby="{id}-request">
    <h3 id="{id}-request" class="text-sm font-medium">Your file</h3>
    {#if waiting}
      <p class="text-sm text-ink-muted" role="status">{waiting}</p>
    {:else if estimate?.problem}
      <p class="text-sm text-danger-ink" role="alert">{estimate.problem}</p>
    {:else if estimate}
      <p class="text-sm" data-testid="file-size">{`About ${describeEstimate(estimate, format)}`}</p>
      <div class="flex flex-wrap items-center gap-3">
        <a
          href={url}
          download
          class="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 dark:text-surface"
        >
          {`Download ${FORMATS.find((f) => f.value === format)?.label}`}
        </a>
        <button
          type="button"
          class="cursor-pointer rounded-md border border-line bg-surface px-3 py-2 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
          onclick={copy}
        >
          Copy the address
        </button>
        <span class="text-xs text-ink-muted" role="status">
          {copied === 'yes'
            ? 'Copied.'
            : copied === 'failed'
              ? 'Your browser didn’t allow copying. Select the address and copy it.'
              : ''}
        </span>
      </div>
    {:else}
      <p class="text-sm text-ink-muted">Choose the days to see how large the file is.</p>
    {/if}
    {#if url}
      <label class="block text-xs text-ink-muted" for="{id}-url">The request’s address, for a script</label>
      <textarea
        id="{id}-url"
        readonly
        rows="3"
        class="w-full resize-y rounded-md border border-line bg-surface p-2 font-mono text-xs break-all"
        onfocus={(event) => event.currentTarget.select()}>{fullUrl}</textarea
      >
    {/if}
    <p class="text-xs text-ink-muted">
      {'NetCDF and GeoTIFF keep the grid’s own projection, which GIS software, R’s terra and Python’s xarray read; CSV and JSON give a row for each cell with its latitude and longitude. A large file takes a while to make, and a request that takes longer than 30 seconds is stopped: if that happens, choose a smaller area or fewer days. '}
      <a href="/api/v2/docs" class="underline hover:text-ink">Read the API documentation</a>
      {' for every option.'}
    </p>
  </section>
</div>
