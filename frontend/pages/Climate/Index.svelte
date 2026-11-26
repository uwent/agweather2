<!-- The climate explorer, /climate (Phase 7 track 6 step 6.4, as Ben changed it on 2026-11-26): a climate map
     chosen from a short list (lib/climate/maps.ts, each a view of the map explorer, so its tiles come from the
     explorer's tileRequest), and a location's climate: click the map, search, or choose a saved site, and the site
     page's Climate tab (lib/sites/ClimateTab.svelte, its sections from lib/climate/) follows below. On wide screens
     the map on the left and the controls on the right, as on /map; on phones the map first. -->
<script lang="ts">
  import type { Map as MapLibreMap, Marker } from 'maplibre-gl'
  import { onDestroy, onMount, untrack } from 'svelte'

  import { ApiError, get } from '@/lib/api'
  import { DEFAULT_NORMAL_VARIABLE, NORMAL_VARIABLE_IDS } from '@/lib/climate/Normals.svelte'
  import {
    CLIMATE_MAPS,
    type ClimateMap,
    climateMapText,
    explorerUrl,
    explorerView,
    MAP_LAYERS,
    mapShown,
    mapsFor,
  } from '@/lib/climate/maps'
  import PeriodChoice from '@/lib/climate/PeriodChoice.svelte'
  import { DEFAULT_PERIOD, NORMAL_PERIODS } from '@/lib/climate/periods'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { today as gridToday } from '@/lib/dates'
  import { climateValueWords, storedDd } from '@/lib/explorer/climate'
  import { siteClimatePath } from '@/lib/explorer/links'
  import TitleChip from '@/lib/explorer/TitleChip.svelte'
  import { tileRequest } from '@/lib/explorer/view'
  import DataMap, { type DataInfo, type DataPick } from '@/lib/map/DataMap.svelte'
  import { loadMapLibre } from '@/lib/map/maplibre'
  import { routes } from '@/lib/routes'
  import { siteAt } from '@/lib/sites.svelte'
  import ClimateTab, { type ClimateView } from '@/lib/sites/ClimateTab.svelte'
  import { request } from '@/lib/request.svelte'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeTitle, placeView, type Place } from '@/lib/tools/place'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { LayerInfo, LayersResponse, LocateResponse } from '@/types/api'

  const today = gridToday()
  const units = $derived(currentUnits())

  // --- The view (D118): the map, the place, and the Climate tab's settings under its names

  const view = viewState({
    layer: field(codecs.oneOf(CLIMATE_MAPS), null),
    ...PLACE_FIELDS,
    cperiod: field(codecs.oneOf(NORMAL_PERIODS), DEFAULT_PERIOD),
    cdd: field(codecs.string, ''),
    cstart: field(codecs.date, null),
    cyear: field(codecs.integer({ min: 2000, max: 2100 }), null),
    cmonth: field(codecs.integer({ min: 1, max: 12 }), null),
    cvar: field(codecs.oneOf(NORMAL_VARIABLE_IDS), DEFAULT_NORMAL_VARIABLE),
  })
  onDestroy(() => view.destroy())

  const maps = mapsFor(today)
  const mapId = $derived(mapShown($view.layer, today))
  const text = $derived(climateMapText(mapId, units))
  const place = $derived(placeOf($view))

  // --- The layers (`/layers`, once a visit): the map's latest day, and the degree-day settings with normals

  let layers = $state<LayerInfo[]>([])
  let loadError = $state<string | null>(null)
  async function load() {
    loadError = null
    try {
      layers = (await get<LayersResponse>('/layers')).data
    } catch (error) {
      loadError = error instanceof ApiError ? error.message : String(error)
    }
  }
  onMount(load)

  const layer = $derived(layers.find((l) => l.id === MAP_LAYERS[mapId]))
  const explorer = $derived(
    layer ? explorerView({ map: mapId, layer, today, period: $view.cperiod, at: $view.at }) : null,
  )
  const tiles = $derived(explorer && layer ? tileRequest(explorer, layer, { today, stored: storedDd(layers) }) : null)
  const explorerLink = $derived(explorer ? explorerUrl(explorer) : routes.map())

  // --- The place: /locate's answer (whether we cover it, its open water), for the picker and the Climate tab

  const locate = request<LocateResponse>()
  const pointKey = $derived(place ? `${place.lat},${place.lng}` : '')
  $effect(() => {
    if (!pointKey) return
    const point = untrack(() => ({ lat: place!.lat, lng: place!.lng }))
    untrack(() => locate.load((signal) => get<LocateResponse>('/locate', point, { signal })))
  })
  onDestroy(() => locate.cancel())
  const location = $derived(pointKey ? (locate.value.data?.data ?? null) : null)
  const title = $derived(place ? placeTitle(place, siteAt(place.lat, place.lng), location) : '')

  function pick(next: Place) {
    view.patch(placeView(next))
  }

  // --- The map's value at the place: from a click, or read from the tiles when the place or the map changes

  let dataMap: ReturnType<typeof DataMap> | undefined = $state()
  let map = $state<MapLibreMap>()
  let info = $state<DataInfo | null>(null)
  let picked = $state<DataPick | null>(null)

  async function readValue() {
    const p = place
    if (!p || !dataMap) {
      picked = null
      return
    }
    const found = await dataMap.valueAt(p.lat, p.lng)
    if (place && place.lat === p.lat && place.lng === p.lng) picked = found
  }
  $effect(() => {
    void pointKey
    void dataMap
    untrack(readValue)
  })

  const words = $derived.by(() => {
    if (!tiles || !layer || !picked || picked.value === null || picked.value === 'none') return null
    const years = typeof info?.request?.years === 'string' ? info.request.years : null
    return climateValueWords({
      layer,
      time: typeof info?.request?.date === 'string' && tiles.time === 'latest' ? info.request.date : tiles.time,
      params: tiles.params,
      value: picked.value,
      unit: picked.unit,
      units,
      years,
    })
  })

  // A marker at the place
  let marker: Marker | undefined
  $effect(() => {
    const [m, p] = [map, place]
    untrack(() => {
      if (!m || !p) {
        marker?.remove()
        marker = undefined
        return
      }
      loadMapLibre().then((maplibre) => {
        marker ??= new maplibre.Marker({ color: '#1f2937' })
        marker.setLngLat([p.lng, p.lat]).addTo(m)
      })
    })
  })
  onDestroy(() => marker?.remove())

  // --- The Climate tab's settings, under the view's names

  const climateView = $derived<ClimateView>({
    period: $view.cperiod,
    dd: $view.cdd,
    start: $view.cstart,
    year: $view.cyear,
    month: $view.cmonth,
    variable: $view.cvar,
  })
  const NAMES = { period: 'cperiod', dd: 'cdd', start: 'cstart', year: 'cyear', month: 'cmonth', variable: 'cvar' }
  function patchClimate(changes: Partial<ClimateView>) {
    view.patch(
      Object.fromEntries(Object.entries(changes).map(([key, value]) => [NAMES[key as keyof ClimateView], value])),
    )
  }

  const siteHref = $derived(
    place
      ? siteClimatePath(place.lat, place.lng, siteAt(place.lat, place.lng) ? null : place.name, $view.cperiod)
      : undefined,
  )
</script>

<svelte:head>
  <title>Climate · AgWeather</title>
</svelte:head>

<div class="lg:grid lg:h-[calc(100dvh-var(--chrome-h))] lg:grid-cols-2">
  <div class="h-[60svh] min-h-80 p-2 lg:h-full lg:min-h-0 lg:pr-1">
    {#if tiles}
      <DataMap
        bind:this={dataMap}
        bind:map
        layer={tiles.layer}
        time={tiles.time}
        stat={tiles.stat}
        params={tiles.params}
        label="Map of {text.title}{info?.subtitle ? `, ${info.subtitle}` : ''}"
        prefsKey="climate-map"
        class="h-full"
        oninfo={(next) => (info = next)}
        onupdate={readValue}
        onpick={(p) => {
          picked = p
          pick({ lat: p.lat, lng: p.lng, name: null })
        }}
      >
        {#snippet header()}
          <TitleChip title={text.title} subtitle={info?.subtitle ?? ''} notes={info?.warnings.length ?? 0} />
        {/snippet}
      </DataMap>
    {:else}
      <div
        class="flex h-full items-center justify-center rounded-lg border border-line bg-surface text-sm text-ink-muted"
      >
        {loadError ?? (layers.length ? 'This map has no data yet.' : 'Loading the map…')}
      </div>
    {/if}
  </div>

  <div class="space-y-5 p-4 lg:min-h-0 lg:overflow-y-auto">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold">Climate</h1>
        <p class="text-sm text-ink-muted">
          See how this season compares with normal across the region. Click the map, or choose a place, for that
          location’s climate.
        </p>
      </div>
      <ShareButton url={() => view.shareUrl()} />
    </div>

    {#if loadError}
      <div class="rounded-md border border-danger p-3 text-sm" role="alert">
        <p>{loadError}</p>
        <button type="button" class="mt-2 underline" onclick={load}>Try again</button>
      </div>
    {/if}

    <fieldset class="space-y-1">
      <legend class="mb-1 text-sm font-semibold">Map</legend>
      {#each maps as id (id)}
        <label class="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="radio"
            name="climate-map"
            value={id}
            checked={mapId === id}
            class="accent-brand-600"
            onchange={() => view.patch({ layer: id as ClimateMap })}
          />
          {climateMapText(id, units).label}
        </label>
      {/each}
    </fieldset>
    <p class="max-w-prose text-sm text-ink-muted">{text.about}</p>

    <PeriodChoice
      value={$view.cperiod}
      {today}
      name="climate-map-period"
      onchange={(period) => view.patch({ cperiod: period })}
    />

    <p class="text-sm">
      <a href={explorerLink} class="text-brand-600 underline hover:text-brand-700">Open in the map explorer</a>
      <span class="text-ink-muted">{' for other days, settings and downloads.'}</span>
    </p>

    <PlacePicker {place} onpick={pick} {location} id="climate-place" label="Find a place" {siteHref} />

    {#if place}
      <div class="space-y-1 text-sm" data-testid="climate-value">
        {#if picked && picked.value !== null}
          <p>
            <span class="text-ink-muted">{'On this map: '}</span><span class="font-semibold">{picked.text}</span>
          </p>
          {#if words}<p>{words}</p>{/if}
        {:else if picked}
          <p class="text-ink-muted">This map has no value at this location.</p>
        {/if}
        <p>
          <a href="#location-climate" class="text-brand-600 underline hover:text-brand-700">
            See this location’s climate below
          </a>
        </p>
      </div>
    {/if}
  </div>
</div>

<div class="mx-auto w-full max-w-6xl space-y-8 px-4 py-8">
  {#if place}
    <section id="location-climate" class="scroll-mt-4 space-y-4" aria-labelledby="location-climate-heading">
      <h2 id="location-climate-heading" class="text-xl font-semibold">Climate at {title}</h2>
      <ClimateTab lat={place.lat} lng={place.lng} {today} {location} view={climateView} onchange={patchClimate} />
    </section>
  {/if}

  <section id="map-notes" class="space-y-2" aria-labelledby="about-heading">
    <h2 id="about-heading" class="text-lg font-semibold">About these maps</h2>
    {#each info?.warnings ?? [] as warning (warning)}
      <p class="max-w-prose rounded-md border border-line bg-surface-raised p-2 text-sm" role="note">{warning}</p>
    {/each}
    <p class="max-w-prose text-sm">
      A normal is what’s typical for a date: each year’s value averaged over a period of past years, 30 by default. We
      build normals from our own archive of hourly weather since 2016 and, for earlier years, from the gridMET daily
      dataset adjusted to match it.{' '}<a
        href={`${routes.methods()}#normals`}
        class="text-brand-600 underline hover:text-brand-700"
      >
        How normals are made
      </a>.
    </p>
    {#each info?.caption ?? [] as line (line)}<p class="max-w-prose text-sm text-ink-muted">{line}</p>{/each}
    <p class="max-w-prose text-sm text-ink-muted">
      Each cell of the map is 2.5 km (1.5 miles) across. Days run midnight to midnight Central Standard Time.
    </p>
  </section>
</div>
