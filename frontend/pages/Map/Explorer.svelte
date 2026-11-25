<!-- The map explorer, /map (Phase 7 track 2; D117–D119). The map on the left and the controls on the right, each the
     window's height below the header on wide screens; the clicked cell's chart and the map's notes below. -->
<script lang="ts">
  import type { GeoJSONSource, GeoJSONSourceSpecification, Map as MapLibreMap } from 'maplibre-gl'
  import { onDestroy, onMount, untrack } from 'svelte'

  import { ApiError, get, isAbort, latestRequests } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { readPalette } from '@/lib/charts/palette'
  import PlaceSearch from '@/lib/components/PlaceSearch.svelte'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { today as gridToday } from '@/lib/dates'
  import type { CropSummary, DegreeDayPreset, ModelSummary } from '@/lib/explorer/catalog'
  import CellPanel, { type CellPlace } from '@/lib/explorer/CellPanel.svelte'
  import { buildCellChart, cellSummary, cellTable, shownValues } from '@/lib/explorer/cellChart'
  import { type CellSeries, readSeries, seriesRequest } from '@/lib/explorer/cellSeries'
  import LayerPicker from '@/lib/explorer/LayerPicker.svelte'
  import LayerSettings, { type ModelOption } from '@/lib/explorer/LayerSettings.svelte'
  import MapOptions from '@/lib/explorer/MapOptions.svelte'
  import { prefetchTiles } from '@/lib/explorer/prefetch'
  import TimeControls from '@/lib/explorer/TimeControls.svelte'
  import TitleChip from '@/lib/explorer/TitleChip.svelte'
  import {
    type ExplorerView,
    firstView,
    latestOf,
    spanFor,
    stepDay,
    tileRequest,
    type TileRequest,
    VIEW_FIELDS,
  } from '@/lib/explorer/view'
  import { dataThrough, timeWords } from '@/lib/explorer/words'
  import DataMap, { type DataInfo, type DataPick, type DataScale } from '@/lib/map/DataMap.svelte'
  import { currentUnits } from '@/lib/units'
  import { viewState } from '@/lib/viewState'
  import type { LayerInfo, LayersResponse, PaletteInfo } from '@/types/api'

  const units = $derived(currentUnits())
  const today = gridToday()

  // --- The view (D118): kept for the tab, given whole by Share

  const view = viewState(VIEW_FIELDS, { key: '/map' })
  onDestroy(() => view.destroy())
  const change = (changes: Partial<ExplorerView>) => view.patch(changes)

  // --- What the page lists, fetched once a visit (D117)

  let layers = $state<LayerInfo[]>([])
  let palettes = $state<PaletteInfo[]>([])
  let models = $state<ModelSummary[]>([])
  let crops = $state<CropSummary[]>([])
  let presets = $state<DegreeDayPreset[]>([])
  let loadError = $state<string | null>(null)
  let layersAt = 0

  async function loadLayers() {
    layers = (await get<LayersResponse>('/layers')).data
    layersAt = Date.now()
  }

  async function load() {
    loadError = null
    try {
      const [, p, m, c, d] = await Promise.all([
        loadLayers(),
        get<PaletteInfo[]>('/palettes'),
        get<{ data: ModelSummary[] }>('/models'),
        get<{ data: CropSummary[] }>('/crops'),
        get<{ data: DegreeDayPreset[] }>('/degree-days/presets'),
      ])
      ;[palettes, models, crops, presets] = [p, m.data, c.data, d.data]
      // A first visit, or a link to a layer that's gone: the season's map
      if (!layers.some((l) => l.id === $view.layer)) change(firstView(today))
    } catch (error) {
      loadError = error instanceof ApiError ? error.message : String(error)
    }
  }

  // The newest hour moves on: /layers again when the page comes back after 10 minutes
  function refresh() {
    if (document.visibilityState === 'visible' && layersAt && Date.now() - layersAt > 10 * 60_000) {
      loadLayers().catch(() => {})
    }
  }

  onMount(() => {
    load()
    document.addEventListener('visibilitychange', refresh)
    return () => document.removeEventListener('visibilitychange', refresh)
  })

  const layer = $derived(layers.find((l) => l.id === $view.layer))
  const request = $derived(layer ? tileRequest($view, layer) : null)
  const hourly = $derived(layer?.time_axis === 'hour')

  // The tiles follow the view 300 ms after it settles, so stepping through days asks only for the last
  let shown = $state<TileRequest | null>(null)
  let settle: ReturnType<typeof setTimeout> | undefined
  $effect(() => {
    const next = request
    untrack(() => {
      clearTimeout(settle)
      if (!shown || !next) shown = next
      else settle = setTimeout(() => (shown = next), 300)
    })
  })
  onDestroy(() => clearTimeout(settle))
  const shownLayer = $derived(layers.find((l) => l.id === shown?.layer))

  const scale = $derived.by((): DataScale => {
    const text = $view.scale
    if (!text) return 'auto'
    if (text === 'default') return 'default'
    const [low, high] = text.split(',').map((part) => (part.trim() === '' ? null : Number(part)))
    return { low: Number.isFinite(low) ? low : null, high: Number.isFinite(high) ? high : null }
  })

  // --- A model's options and risk levels, from /models/{id}

  type ModelDetail = { options: ModelOption[]; risk: { levels: string[] } | null }
  let options = $state<ModelOption[]>([])
  let riskLevels = $state<string[] | null>(null)
  const detailRequests = latestRequests()
  $effect(() => {
    const id = layer?.group === 'model' ? layer.id : null
    untrack(() => {
      options = []
      riskLevels = null
      if (!id) return
      detailRequests
        .run('model', (signal) => get<{ data: ModelDetail }>(`/models/${id}`, {}, { signal }))
        .then((body) => {
          options = body.data.options ?? []
          riskLevels = body.data.risk?.levels ?? null
        })
        .catch(() => {})
    })
  })

  // --- The map

  let map: MapLibreMap | undefined = $state()
  let dataMap: ReturnType<typeof DataMap> | undefined = $state()
  let info = $state<DataInfo | null>(null)

  const title = $derived(info?.title ?? shownLayer?.title ?? layer?.title ?? 'Map')
  const when = $derived(shown && shownLayer ? timeWords(shown.time, shown.stat, latestOf(shownLayer), hourly) : '')
  const through = $derived(layer ? dataThrough(layer) : null)
  const announcement = $derived(shown ? `Map of ${title}, ${info?.subtitle || when}` : '')

  // A shared link's map view
  let placed = false
  $effect(() => {
    const m = map
    if (!m || placed) return
    placed = true
    const { c, z } = untrack(() => $view)
    if (view.fromLink && c && z !== null) m.jumpTo({ center: [c.lng, c.lat], zoom: z })
  })

  function shareUrl() {
    if (map) {
      const { lng, lat } = map.getCenter()
      view.patch({ c: { lat, lng }, z: Math.round(map.getZoom() * 100) / 100 })
    }
    return view.shareUrl()
  }

  // The next day's tiles once the map's are in (only the next: a model's map can take seconds to compute)
  let prefetching: AbortController | undefined
  function prefetchNext() {
    prefetching?.abort()
    const m = map
    if (!m || !layer || hourly || spanFor($view, layer) !== 'day' || !$view.date) return
    const next = stepDay($view.date, 1, layer)
    if (next === $view.date) return
    const request = tileRequest({ ...$view, date: next }, layer)
    if (!request) return
    prefetching = new AbortController()
    const b = m.getBounds()
    prefetchTiles(request, [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], m.getZoom(), prefetching.signal)
  }
  onDestroy(() => prefetching?.abort())

  // --- The cell clicked (or found by place search)

  let picked = $state<DataPick | null>(null)
  let place = $state<CellPlace | null>(null)
  let placeError = $state<string | null>(null)
  const cellRequests = latestRequests()

  function choose(lat: number, lng: number) {
    change({ at: { lat: Number(lat.toFixed(4)), lng: Number(lng.toFixed(4)) } })
  }

  async function readValue() {
    const at = $view.at
    if (!at || !dataMap) return
    picked = await dataMap.valueAt(at.lat, at.lng)
  }

  function updated() {
    readValue()
    prefetchNext()
  }

  $effect(() => {
    const at = $view.at
    untrack(() => {
      place = null
      placeError = null
      picked = null
      if (!at) return
      readValue()
      cellRequests
        .run('locate', (signal) => get<{ data: CellPlace }>('/locate', { lat: at.lat, lng: at.lng }, { signal }))
        .then((body) => (place = body.data))
        .catch((error) => {
          if (!isAbort(error)) placeError = error instanceof ApiError ? error.message : String(error)
        })
    })
  })

  // The cell's outline, above the data and the labels
  $effect(() => {
    const m = map
    const corners = place?.corners ?? null
    if (!m) return
    // A source can't be added while the style is still loading: then again once the map is idle
    const draw = () => {
      try {
        outline(m, corners)
      } catch {
        m.once('idle', draw)
      }
    }
    draw()
  })

  function outline(m: MapLibreMap, corners: [number, number][] | null) {
    const data: GeoJSONSourceSpecification['data'] = {
      type: 'FeatureCollection',
      features: corners
        ? [
            {
              type: 'Feature',
              properties: {},
              geometry: { type: 'Polygon', coordinates: [[...corners, corners[0]].map(([lat, lng]) => [lng, lat])] },
            },
          ]
        : [],
    }
    const source = m.getSource('data-cell') as GeoJSONSource | undefined
    if (source) return source.setData(data)
    const palette = readPalette()
    m.addSource('data-cell', { type: 'geojson', data })
    m.addLayer({
      id: 'data-cell-halo',
      type: 'line',
      source: 'data-cell',
      paint: { 'line-color': palette.surface, 'line-width': 5 },
    })
    m.addLayer({
      id: 'data-cell',
      type: 'line',
      source: 'data-cell',
      paint: { 'line-color': palette.ink, 'line-width': 2 },
    })
  }

  // The cell's days: the same settings as the map's tiles
  let series = $state<CellSeries | null>(null)
  let seriesError = $state<string | null>(null)
  let seriesLoading = $state(false)
  const seriesFor = $derived(shown && shownLayer && $view.at ? seriesRequest($view, shownLayer, shown, $view.at) : null)
  $effect(() => {
    const asked = seriesFor
    untrack(() => {
      series = null
      seriesError = null
      if (!asked) return
      seriesLoading = true
      cellRequests
        .run('series', (signal) => get<Parameters<typeof readSeries>[1]>(asked.path, asked.params, { signal }))
        .then((body) => (series = readSeries(asked, body)))
        .catch((error) => {
          if (!isAbort(error)) seriesError = error instanceof ApiError ? error.message : String(error)
        })
        .finally(() => (seriesLoading = false))
    })
  })
  onDestroy(() => {
    cellRequests.cancel()
    detailRequests.cancel()
  })

  // The series' stored unit, to show it in the reader's units
  const storedUnit = $derived.by(() => {
    if (!shownLayer || !seriesFor) return null
    if (shownLayer.group === 'degree_days') return 'degF_day'
    if (shownLayer.group === 'model') return shownLayer.outputs?.find((o) => o.name === seriesFor.column)?.unit ?? null
    if (seriesFor.daily) return layers.find((l) => l.id === seriesFor.column)?.unit ?? shownLayer.unit
    return shownLayer.unit
  })
  // A model's risk levels by name (the model's own list, else the names the run gave)
  const levels = $derived(series?.labels ? (riskLevels ?? levelNames(series)) : null)
  function levelNames(s: CellSeries): string[] {
    const names: string[] = []
    s.values.forEach((v, i) => {
      if (v !== null && s.labels?.[i]) names[v] = s.labels[i] as string
    })
    return Array.from(names, (name, i) => name ?? `Level ${i}`)
  }
  const chart = $derived.by(() => {
    if (!series || !seriesFor) return null
    const { values, unit } = shownValues(series, storedUnit, units)
    const digits = storedUnit ? units.digits(storedUnit) : 1
    const name = seriesFor.daily ? `${title}, each day` : title
    const marked = shown?.time === 'latest' ? null : (shown?.time.split('..').at(-1) ?? null)
    return {
      name,
      build: buildCellChart({ series, values, unit, name, marked, levels, digits }),
      summary: cellSummary(series, values, unit, levels, digits),
      table: () => cellTable(series!, values, unit ? `${name} (${unit})` : name, levels, digits),
    }
  })
</script>

<svelte:head>
  <title>Map · AgWeather</title>
</svelte:head>

<p class="sr-only" aria-live="polite">{announcement}</p>

<div class="lg:grid lg:h-[calc(100dvh-var(--chrome-h))] lg:grid-cols-2">
  <div class="h-[62svh] min-h-80 p-2 lg:h-full lg:min-h-0 lg:pr-1">
    {#if shown}
      <DataMap
        bind:this={dataMap}
        bind:map
        layer={shown.layer}
        time={shown.time}
        stat={shown.stat}
        params={shown.params}
        palette={$view.palette}
        {scale}
        label="Map of {title}, {when}"
        prefsKey="map-explorer"
        class="h-full"
        oninfo={(next) => (info = next)}
        onupdate={updated}
        onpick={(pick) => {
          picked = pick
          choose(pick.lat, pick.lng)
        }}
      >
        {#snippet header()}
          <TitleChip {title} subtitle={info?.subtitle} {when} {through} />
        {/snippet}
        {#snippet controls()}
          <PlaceSearch {map} onplace={(p) => choose(p.center[1], p.center[0])} />
        {/snippet}
      </DataMap>
    {:else}
      <div
        class="flex h-full items-center justify-center rounded-lg border border-line bg-surface text-sm text-ink-muted"
      >
        {loadError ?? 'Loading the map…'}
      </div>
    {/if}
  </div>

  <div class="space-y-5 p-4 lg:min-h-0 lg:overflow-y-auto">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold">Weather and pest maps</h1>
        <p class="text-sm text-ink-muted">Choose a map, a day and a place. Click the map for a cell's recent days.</p>
      </div>
      <ShareButton url={shareUrl} />
    </div>

    {#if loadError}
      <div class="rounded-md border border-danger p-3 text-sm" role="alert">
        <p>{loadError}</p>
        <button type="button" class="mt-2 underline" onclick={load}>Try again</button>
      </div>
    {/if}

    {#if $view.at}
      <CellPanel
        value={picked?.text ?? null}
        {title}
        when={info?.subtitle || when}
        {place}
        {placeError}
        onclear={() => change({ at: null })}
      />
    {/if}

    {#if layers.length}
      <LayerPicker view={$view} {layers} {models} {crops} {presets} onchange={change} />
      {#if layer?.group === 'model'}
        <LayerSettings view={$view} {layer} {options} onchange={change} />
      {/if}
      {#if layer}
        <TimeControls view={$view} {layer} {today} onchange={change} />
        <MapOptions view={$view} {layer} {info} {palettes} onchange={change} />
      {/if}
    {/if}
  </div>
</div>

<div class="mx-auto w-full max-w-6xl space-y-6 px-4 py-8">
  {#if $view.at}
    <section id="cell-chart" class="space-y-2" aria-labelledby="cell-chart-heading">
      <h2 id="cell-chart-heading" class="text-lg font-semibold">This cell's recent days</h2>
      {#if chart}
        <ChartCard
          title={chart.name}
          info="The days before the map's date at the cell you chose, and the forecast where it reaches past today. The shaded days are a forecast."
          build={chart.build}
          height="18rem"
          summary={chart.summary}
          table={chart.table}
        />
        {#each series?.warnings ?? [] as warning (warning)}<p class="text-sm text-ink-muted">{warning}</p>{/each}
      {:else if seriesError}
        <p class="text-sm text-danger-ink">{seriesError}</p>
      {:else if seriesLoading}
        <p class="text-sm text-ink-muted">Loading this cell's days…</p>
      {:else}
        <p class="text-sm text-ink-muted">This map has no chart of its days yet.</p>
      {/if}
    </section>
  {/if}

  {#if layer}
    <section class="space-y-2" aria-labelledby="about-heading">
      <h2 id="about-heading" class="text-lg font-semibold">About this map</h2>
      {#each info?.warnings ?? [] as warning (warning)}
        <p class="rounded-md border border-line bg-surface-raised p-2 text-sm" role="note">{warning}</p>
      {/each}
      <p class="max-w-prose text-sm">{layer.description}</p>
      {#if info?.caption}<p class="max-w-prose text-sm text-ink-muted">{info.caption}</p>{/if}
      {#if through}<p class="text-sm text-ink-muted">{through}.</p>{/if}
      <p class="max-w-prose text-sm text-ink-muted">
        Each cell of the map is 2.5 km (1.5 miles) across. Days run midnight to midnight Central Standard Time.
      </p>
    </section>
  {/if}
</div>
