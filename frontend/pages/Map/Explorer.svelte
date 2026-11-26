<!-- The map explorer, /map (Phase 7 track 2; D117–D119). On wide screens the map on the left and the controls on the
     right, each the window's height below the header; on phones the map first, a bar under it with "Layer and date"
     (the controls as a sheet from the bottom) and the day's stepper, and the clicked cell as a card over the map's
     foot. The cell's chart, the county table and the map's notes follow below. -->
<script lang="ts">
  import type { GeoJSONSource, GeoJSONSourceSpecification, Map as MapLibreMap } from 'maplibre-gl'
  import { Dialog } from 'bits-ui'
  import { onDestroy, onMount, tick, untrack } from 'svelte'
  import { MediaQuery } from 'svelte/reactivity'
  import { fly } from 'svelte/transition'

  import { ApiError, get, isAbort, latestRequests } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { readPalette } from '@/lib/charts/palette'
  import PlaceSearch from '@/lib/components/PlaceSearch.svelte'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { today as gridToday } from '@/lib/dates'
  import type { CropSummary, DegreeDayPreset, ModelSummary } from '@/lib/explorer/catalog'
  import CellPanel, { type CellPlace } from '@/lib/explorer/CellPanel.svelte'
  import { stateCode } from '@/lib/explorer/counties'
  import CountyTable from '@/lib/explorer/CountyTable.svelte'
  import { buildCellChart, cellSummary, cellTable, shownValues } from '@/lib/explorer/cellChart'
  import { type CellSeries, readSeries, seriesRequest } from '@/lib/explorer/cellSeries'
  import LayerPicker from '@/lib/explorer/LayerPicker.svelte'
  import LayerSettings, { type ModelOption } from '@/lib/explorer/LayerSettings.svelte'
  import SaveImageButton from '@/lib/explorer/SaveImageButton.svelte'
  import MapOptions from '@/lib/explorer/MapOptions.svelte'
  import { prefetchTiles } from '@/lib/explorer/prefetch'
  import TimeControls from '@/lib/explorer/TimeControls.svelte'
  import TimeStepper from '@/lib/explorer/TimeStepper.svelte'
  import TitleChip from '@/lib/explorer/TitleChip.svelte'
  import {
    type ExplorerView,
    firstView,
    latestOf,
    spanFor,
    stepDay,
    stepperWhen,
    stepTo,
    tileRequest,
    timeIsForecast,
    type TileRequest,
    VIEW_FIELDS,
  } from '@/lib/explorer/view'
  import { dataThrough, timeWords } from '@/lib/explorer/words'
  import { shortTitle } from '@/lib/explorer/catalog'
  import DataMap, { type DataInfo, type DataPick, type DataScale } from '@/lib/map/DataMap.svelte'
  import { imageFileName } from '@/lib/map/exportImage'
  import { motion } from '@/lib/motion'
  import { siteLabel, sites } from '@/lib/sites.svelte'
  import { drawGroup, groupBounds } from '@/lib/sites/groupMap'
  import { currentUnits } from '@/lib/units'
  import { viewState } from '@/lib/viewState'
  import type { LayerInfo, LayersResponse, PaletteInfo } from '@/types/api'

  const units = $derived(currentUnits())

  // The API's description of its degree-day layer is written for developers
  const DEGREE_DAYS_ABOUT =
    'Growing degree days measure the heat a crop or insect has had: each day adds the degrees by which its temperature rose above a base temperature, limited by an upper threshold where one is set. The map adds them up from January 1 or the date you choose, using each day’s low and high.'
  const today = gridToday()
  // Wide screens (Tailwind's lg) put the controls beside the map; narrower ones in a sheet
  const wide = new MediaQuery('min-width: 1024px', true)
  let sheetOpen = $state(false)

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

  // --- A model's options, from /models/{id} (its levels' names come with the map's TileJSON)

  type ModelDetail = { options: ModelOption[] }
  let options = $state<ModelOption[]>([])
  const detailRequests = latestRequests()
  $effect(() => {
    const id = layer?.group === 'model' ? layer.id : null
    untrack(() => {
      options = []
      if (!id) return
      detailRequests
        .run('model', (signal) => get<{ data: ModelDetail }>(`/models/${id}`, {}, { signal }))
        .then((body) => (options = body.data.options ?? []))
        .catch(() => {})
    })
  })
  const mapModel = $derived(
    shownLayer?.group === 'model'
      ? { id: shownLayer.id, name: models.find((m) => m.id === shownLayer.id)?.name ?? shownLayer.title }
      : null,
  )

  // --- The map

  let map: MapLibreMap | undefined = $state()
  let dataMap: ReturnType<typeof DataMap> | undefined = $state()
  let info = $state<DataInfo | null>(null)

  const title = $derived(info?.title ?? shownLayer?.title ?? layer?.title ?? 'Map')
  const when = $derived(shown && shownLayer ? timeWords(shown.time, shown.stat, latestOf(shownLayer), hourly) : '')
  const through = $derived(layer ? dataThrough(layer) : null)
  const shownForecast = $derived(shown && shownLayer ? timeIsForecast(shown.time, shownLayer) : false)
  // What the map shows beyond its name, in the API's words (its `subtitle`); the date in words only until it comes
  const subtitle = $derived(info?.subtitle ?? '')
  const announcement = $derived(shown ? `Map of ${title}, ${subtitle || when}${shownForecast ? ', forecast' : ''}` : '')

  // A shared link's map view and overlay
  let placed = false
  $effect(() => {
    const m = map
    if (!m || !dataMap || placed) return
    placed = true
    const { c, z, overlay } = untrack(() => $view)
    if (!view.fromLink) return
    if (c && z !== null) m.jumpTo({ center: [c.lng, c.lat], zoom: z })
    dataMap.showOverlay(overlay)
  })

  // A group's sites (F12): marked and named, and the map framed to them when the group arrives (not when a shared
  // link also gives the sharer's center and zoom, which the effect above shows)
  let framed: string | null = null
  $effect(() => {
    const m = map
    const group = $view.group
    if (!m) return
    untrack(() => {
      const draw = () => {
        try {
          drawGroup(m, group)
        } catch {
          m.once('idle', draw)
        }
      }
      draw()
      const key = group ? JSON.stringify(group) : null
      if (key === framed) return
      framed = key
      const bounds = group ? groupBounds(group) : null
      const { c, z } = $view
      if (bounds && !(view.fromLink && c && z !== null)) m.fitBounds(bounds, { padding: 80, maxZoom: 8, duration: 0 })
    })
  })
  // A basemap switch replaces the style, and the sites with it
  $effect(() => {
    const m = map
    if (!m) return
    const redraw = () => {
      if ($view.group) drawGroup(m, $view.group)
    }
    m.on('style.load', redraw)
    return () => {
      m.off('style.load', redraw)
    }
  })

  function shareUrl() {
    if (map) {
      const { lng, lat } = map.getCenter()
      view.patch({ c: { lat, lng }, z: Math.round(map.getZoom() * 100) / 100 })
    }
    view.patch({ overlay: dataMap?.currentOverlay() ?? null })
    return view.shareUrl()
  }

  // Save image (F13): the map as on screen, with the title chip's text, the data's reach and the saved sites in view
  async function saveImage({ labels }: { labels: boolean }) {
    if (!dataMap || !shown) throw new Error('The map is still loading. Try again when it has drawn.')
    const asked = info?.request ?? {}
    const date =
      typeof asked.date === 'string'
        ? asked.date
        : typeof asked.start === 'string' && typeof asked.end === 'string'
          ? `${asked.start}..${asked.end}`
          : shown.time
    await dataMap.saveImage({
      title,
      subtitle: `${subtitle || when}${shownForecast ? ' · Forecast' : ''}`,
      through: through ? `${through}.` : '',
      fileName: imageFileName(shown.layer, date),
      labels: labels
        ? sites.map((site) => ({ id: site.key, text: siteLabel(site), lat: site.lat, lng: site.lng }))
        : [],
    })
  }

  // The phone's stepper, under the map: the same steps as the controls'
  const stepWhen = $derived(layer ? stepperWhen($view, layer, today) : null)

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
  /** The place searched for, while its point is the one chosen */
  let searched = $state<{ name: string; lat: number; lng: number } | null>(null)
  const cellRequests = latestRequests()

  function choose(lat: number, lng: number) {
    change({ at: { lat: Number(lat.toFixed(4)), lng: Number(lng.toFixed(4)) } })
  }

  // A place found by search: its cell chosen, and the reader taken to the cell's answer
  async function chooseSearched(name: string, lat: number, lng: number) {
    choose(lat, lng)
    const at = $view.at
    searched = at ? { name: name.split(',')[0].trim(), lat: at.lat, lng: at.lng } : null
    await tick()
    document.querySelector<HTMLElement>('[data-testid="cell-panel"]')?.focus()
  }
  const searchedName = $derived(
    searched && $view.at && searched.lat === $view.at.lat && searched.lng === $view.at.lng ? searched.name : null,
  )

  // The county table's state: the chosen cell's, else the one at the map's center when the page opens
  let countyState = $state('WI')
  let countyStateChosen = false
  $effect(() => {
    const found = stateCode(place?.state)
    if (found && !countyStateChosen) untrack(() => (countyState = found))
  })
  let centerLocated = false
  $effect(() => {
    const m = map
    if (!m || centerLocated) return
    centerLocated = true
    untrack(() => {
      const { lat, lng } = m.getCenter()
      get<{ data: CellPlace }>('/locate', { lat: Number(lat.toFixed(4)), lng: Number(lng.toFixed(4)) })
        .then((body) => {
          const found = stateCode(body.data.state)
          if (found && !countyStateChosen && !place) countyState = found
        })
        .catch(() => {})
    })
  })

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
  // A model's risk levels by name (the map's, else the names the run gave)
  const mapLevels = $derived(info?.categories?.every((c) => c.value >= 0) ? info.categories.map((c) => c.name) : null)
  const levels = $derived(series?.labels ? (mapLevels ?? levelNames(series)) : null)
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

{#snippet intro()}
  <div class="flex items-start justify-between gap-3">
    <div>
      <h1 class="text-xl font-semibold">Weather and pest maps</h1>
      <p class="text-sm text-ink-muted">Choose a map, a day and a place. Click the map for a cell's recent days.</p>
    </div>
    {#if wide.current}
      <div class="flex shrink-0 gap-2">
        <SaveImageButton save={saveImage} sites={sites.length} disabled={!info} />
        <ShareButton url={shareUrl} />
      </div>
    {/if}
  </div>
  {#if $view.group}
    <p class="flex flex-wrap items-center gap-x-3 text-sm" data-testid="map-group">
      <span>
        {`Showing the group ${$view.group.name}: ${$view.group.sites.length === 1 ? '1 site' : `${$view.group.sites.length} sites`}, named on the map.`}
      </span>
      <button type="button" class="text-ink-muted underline hover:text-ink" onclick={() => change({ group: null })}>
        Stop showing the group
      </button>
    </p>
  {/if}
{/snippet}

{#snippet failed()}
  {#if loadError}
    <div class="rounded-md border border-danger p-3 text-sm" role="alert">
      <p>{loadError}</p>
      <button type="button" class="mt-2 underline" onclick={load}>Try again</button>
    </div>
  {/if}
{/snippet}

{#snippet cell()}
  {#if $view.at}
    <CellPanel
      lat={$view.at.lat}
      lng={$view.at.lng}
      value={picked?.text ?? null}
      {title}
      when={subtitle || when}
      {place}
      {placeError}
      searched={searchedName}
      model={mapModel}
      group={$view.group?.name ?? null}
      onclear={() => change({ at: null })}
    />
  {/if}
{/snippet}

{#snippet settings()}
  {#if layers.length}
    <LayerPicker view={$view} {layers} {models} {crops} {presets} onchange={change} />
    {#if layer?.group === 'model'}
      <LayerSettings view={$view} {layer} {options} onchange={change} />
    {/if}
    {#if layer}
      <TimeControls view={$view} {layer} {today} onchange={change} />
      <MapOptions view={$view} {layer} {info} {palettes} onchange={change} />
    {/if}
  {:else if !loadError}
    <p class="text-sm text-ink-muted">Loading the maps…</p>
  {/if}
{/snippet}

<div class="lg:grid lg:h-[calc(100dvh-var(--chrome-h))] lg:grid-cols-2">
  <div class="relative h-[calc(100svh-var(--chrome-h)-6.5rem)] min-h-80 p-2 lg:h-full lg:min-h-0 lg:pr-1">
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
        label="Map of {title}, {subtitle || when}"
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
          <TitleChip {title} {subtitle} forecast={shownForecast} notes={info?.warnings.length ?? 0} />
        {/snippet}
        {#snippet controls()}
          <PlaceSearch {map} onplace={(p) => chooseSearched(p.label, p.center[1], p.center[0])} />
        {/snippet}
      </DataMap>
    {:else}
      <div
        class="flex h-full items-center justify-center rounded-lg border border-line bg-surface text-sm text-ink-muted"
      >
        {loadError ?? 'Loading the map…'}
      </div>
    {/if}
    {#if !wide.current && $view.at}
      <!-- On phones the cell's answer slides up over the map's foot (the legend), at most 60% of its height -->
      <div
        class="absolute inset-x-3 bottom-3 z-10 max-h-[60%] overflow-y-auto rounded-md shadow-xl"
        transition:fly={{ y: 160, duration: motion(200) }}
      >
        {@render cell()}
      </div>
    {/if}
  </div>

  {#if wide.current}
    <div class="space-y-5 p-4 lg:min-h-0 lg:overflow-y-auto">
      {@render intro()}
      {@render failed()}
      {@render cell()}
      {@render settings()}
    </div>
  {:else}
    <!-- Phones: the map's controls in a sheet, and the day's stepper under the map -->
    <div class="space-y-2 border-b border-line px-2 pb-2" data-testid="phone-bar">
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center justify-between gap-2 rounded-md border border-line bg-surface-raised px-3 py-1.5 text-left
            hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          aria-haspopup="dialog"
          aria-expanded={sheetOpen}
          onclick={() => (sheetOpen = true)}
        >
          <span class="min-w-0">
            <span class="block text-sm font-semibold">Layer and date</span>
            <span class="block truncate text-xs text-ink-muted">{layer ? shortTitle(layer) : 'Loading…'}</span>
          </span>
          <span aria-hidden="true" class="text-ink-muted">▴</span>
        </button>
        <SaveImageButton save={saveImage} sites={sites.length} disabled={!info} compact />
        <ShareButton url={shareUrl} />
      </div>
      {#if layer && stepWhen}
        <TimeStepper {layer} when={stepWhen} {today} onstep={(next) => change(stepTo($view, layer, next))} />
      {/if}
    </div>
    <div class="space-y-3 p-4">
      {@render intro()}
      {@render failed()}
    </div>

    <Dialog.Root bind:open={sheetOpen}>
      <Dialog.Portal>
        <Dialog.Overlay class="fixed inset-0 z-40 bg-black/20" />
        <Dialog.Content
          preventScroll={false}
          class="fixed inset-x-0 bottom-0 z-50 flex max-h-[80dvh] flex-col rounded-t-xl border-t border-line bg-surface-raised shadow-2xl"
          data-testid="controls-sheet"
        >
          <div class="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
            <div class="min-w-0">
              <Dialog.Title class="text-base font-semibold">Layer and date</Dialog.Title>
              <Dialog.Description class="truncate text-xs text-ink-muted">
                {subtitle ? `${title}, ${subtitle}` : title}
              </Dialog.Description>
            </div>
            <Dialog.Close
              class="rounded-md bg-brand-600 px-3 py-1 text-sm font-semibold text-surface hover:bg-brand-700
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
            >
              Show the map
            </Dialog.Close>
          </div>
          <div class="space-y-5 overflow-y-auto overscroll-contain p-4">
            {@render settings()}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  {/if}
</div>

<div class="mx-auto w-full max-w-6xl space-y-8 px-4 py-8">
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
    <section id="map-notes" class="space-y-2" aria-labelledby="about-heading">
      <h2 id="about-heading" class="text-lg font-semibold">About this map</h2>
      {#each info?.warnings ?? [] as warning (warning)}
        <p class="max-w-prose rounded-md border border-line bg-surface-raised p-2 text-sm" role="note">{warning}</p>
      {/each}
      <p class="max-w-prose text-sm">{layer.group === 'degree_days' ? DEGREE_DAYS_ABOUT : layer.description}</p>
      {#each info?.caption ?? [] as line (line)}<p class="max-w-prose text-sm text-ink-muted">{line}</p>{/each}
      {#if through}<p class="text-sm text-ink-muted">{through}.</p>{/if}
      <p class="max-w-prose text-sm text-ink-muted">
        Each cell of the map is 2.5 km (1.5 miles) across. Days run midnight to midnight Central Standard Time.
      </p>
    </section>
  {/if}

  {#if shown}
    <CountyTable
      tiles={shown}
      {info}
      {title}
      region={countyState}
      onregion={(code) => {
        countyStateChosen = true
        countyState = code
      }}
    />
  {/if}
</div>
