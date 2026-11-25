<script lang="ts" module>
  import { get, type QueryScalar } from '@/lib/api'
  import type { LayerInfo, LayersResponse, PaletteInfo } from '@/types/api'

  // What every data map shares, fetched once a visit: the palettes, and the layers' fixed ranges
  let palettesLoading: Promise<PaletteInfo[]> | undefined
  let layersLoading: Promise<LayerInfo[]> | undefined
  const shared = () => {
    palettesLoading ??= get<PaletteInfo[]>('/palettes').catch((error) => {
      palettesLoading = undefined
      throw error
    })
    layersLoading ??= get<LayersResponse>('/layers').then(
      (body) => body.data,
      (error) => {
        layersLoading = undefined
        throw error
      },
    )
    return Promise.all([palettesLoading, layersLoading])
  }

  /** What the colors span: the map's own range (`auto`, the API's 2nd to 98th percentile), the layer's fixed range
   * (`default`, for comparing days color for color), or low and high in the reader's units (an end left null takes
   * the map's own) */
  export type DataScale = 'auto' | 'default' | { low: number | null; high: number | null }

  /** A layer's settings beyond its time: `dd`, `output`, `planting`, a model's options */
  export type DataParams = Record<string, QueryScalar | null | undefined>

  /** What a click on the map picked: the point, and the value of the cell under it (stored units) */
  export type DataPick = {
    lat: number
    lng: number
    /** The value in `unit`; null where missing, 'none' where a first or last day wasn't found */
    value: number | 'none' | null
    unit: string
    /** The value as the reader sees it ("72 °F", "High", "No data") */
    text: string
  }

  /** What the map shows, once its tiles are described: for the page's title and controls */
  export type DataInfo = {
    title: string
    /** The stored unit */
    unit: string
    step: number
    /** The palette the layer takes by default, and its kind */
    defaultPalette: string
    kind: 'sequential' | 'diverging' | 'categorical' | 'cyclic'
    /** The colors' ends in the reader's units, as drawn */
    low: number
    high: number
    /** What the map shows beyond its name (the date or range, the settings), when the API gives it */
    subtitle?: string
    /** A longer note under the map (how it was made), when the API gives it */
    caption?: string
    /** The API's warnings about this map, in its words */
    warnings: string[]
    /** The request as the API read it (the TileJSON's `request`) */
    request: TileJson['request']
  }
</script>

<script lang="ts">
  import { onDestroy, onMount, type Snippet, untrack } from 'svelte'
  import type { Map as MapLibreMap, MapMouseEvent, RasterDEMSourceSpecification } from 'maplibre-gl'
  import 'maplibre-gl/dist/maplibre-gl.css'

  import { API_BASE, ApiError, isAbort, latestRequests, queryString } from '@/lib/api'
  import { BasemapSwitch, beneathLabels } from '@/lib/map/basemaps'
  import { COVERAGE_BOUNDS } from '@/lib/map/coverage'
  import { createMap } from '@/lib/map/createMap'
  import { currentUnits, units as unitsOf } from '@/lib/units'

  import BasemapToggle from './BasemapToggle.svelte'
  import DataLegend, { type DataLegendSpec } from './DataLegend.svelte'
  import {
    colorExpression,
    findPalette,
    formatDays,
    maplibreEncoding,
    MAX_ZOOM,
    MIN_ZOOM,
    type PixelValue,
    type TileJson,
    TileValues,
  } from './dataTiles'
  import HoverLabel from './HoverLabel.svelte'
  import { MapHover } from './hover.svelte'
  import MapLayersButton from './MapLayersButton.svelte'
  import { MapOverlays } from './mapOverlays.svelte'
  import OverlayLayers from './OverlayLayers.svelte'
  import type { OverlayId } from './overlays'
  import OverlayTooltip from './OverlayTooltip.svelte'
  import { loadPrefs, savePrefs } from './prefs'
  import { followRoads } from './roads.svelte'

  // A map of one layer of the API's data (D119): its tiles as a raster-dem source colored on the GPU by a
  // color-relief layer beneath the basemap's borders and labels, so a palette or scale change recolors without a
  // request; the value under the pointer read from the same tiles' pixels; a legend in the reader's units; the
  // basemap toggle and WISP 3's overlays. New tiles load only when the layer, time or settings change.
  let {
    layer,
    time,
    stat = null,
    params = {},
    palette = null,
    scale = 'auto',
    opacity = 1,
    label,
    prefsKey = 'data-map',
    map = $bindable(),
    onpick,
    oninfo,
    controls,
    header,
    class: className = 'h-112 sm:h-128',
  }: {
    /** A layer id from `/layers` */
    layer: string
    /** A day (2026-07-08), an hour (2026-07-08T15), a range of days with `stat` (2026-07-01..2026-07-07), a
     * season (2025-26) or `latest` */
    time: string
    stat?: string | null
    params?: DataParams
    /** A `/palettes` id (`_r` reversed); null: the layer's own */
    palette?: string | null
    scale?: DataScale
    opacity?: number
    /** The map's accessible name */
    label: string
    /** Where this page's map settings (view, basemap, overlay) are remembered */
    prefsKey?: string
    map?: MapLibreMap
    onpick?: (pick: DataPick) => void
    oninfo?: (info: DataInfo | null) => void
    /** The page's own controls, under the basemap toggle (a place search) */
    controls?: Snippet
    /** Above the basemap toggle at the top left (the map's title) */
    header?: Snippet
    class?: string
  } = $props()

  const units = $derived(currentUnits())

  let palettes = $state<PaletteInfo[]>([])
  let layers = $state<LayerInfo[]>([])

  // --- The tiles: described by the TileJSON for the layer, time and settings

  type Tiles = {
    key: string
    template: string
    tilejson: TileJson
    step: number
    unit: string
    /** The map's own range (the API's auto scale), in the stored unit */
    auto: [number, number]
    levels?: string[]
  }

  let tiles = $state<Tiles | null>(null)
  let loading = $state(false)
  let failure = $state<string | null>(null)
  const requests = latestRequests()

  const settings = $derived(queryString({ stat, ...params }))
  const key = $derived(`${layer}/${time}?${settings}`)

  $effect(() => {
    const [k, l, t, query] = [key, layer, time, settings]
    untrack(() => describe(k, l, t, query))
  })

  async function describe(k: string, l: string, t: string, query: string) {
    loading = true
    failure = null
    try {
      const params = Object.fromEntries(new URLSearchParams(query))
      // The auto range comes in the request's units and is kept in the stored unit, so a units switch needs nothing
      // (`units` among the settings, as for degree days written in °F, is the request's and so the domain's)
      const system = params.units ?? (units.system === 'metric' ? 'metric' : 'us')
      const shownIn = unitsOf(system === 'metric' ? 'metric' : 'imperial')
      const sharing = shared()
      const tilejson = await requests.run('tilejson', (signal) =>
        get<TileJson>(`/tiles/${l}.json`, { ...params, time: t, style: 'default', units: system }, { signal }),
      )
      const [[p, ls], levels] = await Promise.all([sharing, levelNames(tilejson)])
      if (k !== untrack(() => key)) return // a newer request has the map
      ;[palettes, layers] = [p, ls]
      const { step, unit } = tilejson.encoding
      const auto = (tilejson.domain ?? [0, 1]).map((v) => shownIn.toStored(unit, v)) as [number, number]
      const path = `${API_BASE}/tiles/${encodeURIComponent(l)}/${encodeURIComponent(t)}/{z}/{x}/{y}.png`
      const template = `${location.origin}${path}${query ? `?${query}` : ''}`
      tiles = { key: k, template, tilejson, step, unit, auto, levels }
    } catch (error) {
      if (isAbort(error) || k !== untrack(() => key)) return
      tiles = null
      failure = error instanceof ApiError ? error.message : String(error)
    } finally {
      if (k === untrack(() => key)) loading = false
    }
  }

  // A model's risk levels by name, for the legend and the hover label
  async function levelNames(tilejson: TileJson): Promise<string[] | undefined> {
    const model = tilejson.request.model
    const output = tilejson.request.output
    if (!model || (output !== 'risk_level' && output !== 'projected_risk_level')) return undefined
    try {
      const body = await get<{ data: { risk?: { levels: string[] } | null } }>(`/models/${model.id}`)
      return body.data.risk?.levels
    } catch {
      return undefined
    }
  }

  // --- The colors: the palette over the scale, in the stored unit (the tiles' values)

  const layerInfo = $derived(layers.find((l) => l.id === layer))
  const outputInfo = $derived.by(() => {
    const outputs = layerInfo?.outputs ?? []
    const name = tiles?.tilejson.request.output ?? params.output
    return outputs.find((o) => o.name === name) ?? outputs[0]
  })
  const defaultPalette = $derived(tiles?.tilejson.palette ?? outputInfo?.palette ?? layerInfo?.palette ?? 'viridis')
  const paletteShown = $derived.by(() => {
    const fallback = findPalette(defaultPalette, palettes)
    const asked = palette ? findPalette(palette, palettes) : undefined
    // A categorical map takes only a categorical palette with as many levels, and a continuous map no categorical one
    if (!asked || !fallback) return fallback
    if ((asked.kind === 'categorical') !== (fallback.kind === 'categorical')) return fallback
    if (asked.kind === 'categorical' && asked.colors.length !== fallback.colors.length) return fallback
    return asked
  })

  /** The colors' ends in the stored unit */
  const domain = $derived.by((): [number, number] | null => {
    if (!tiles) return null
    const fixed = outputInfo?.domain ?? (layerInfo?.outputs?.length ? null : layerInfo?.domain)
    if (paletteShown?.kind === 'categorical' || paletteShown?.kind === 'cyclic') return tiles.auto
    if (scale === 'auto') return tiles.auto
    if (scale === 'default') return fixed ? [fixed[0], fixed[1]] : tiles.auto
    const low = scale.low === null ? tiles.auto[0] : units.toStored(tiles.unit, scale.low)
    const high = scale.high === null ? tiles.auto[1] : units.toStored(tiles.unit, scale.high)
    return [low, high]
  })

  const colors = $derived(tiles && paletteShown && domain ? colorExpression(paletteShown, domain, tiles.step) : null)

  const legend = $derived.by((): DataLegendSpec | null => {
    if (!tiles || !paletteShown || !domain) return null
    const categorical = paletteShown.kind === 'categorical'
    return {
      title: tiles.tilejson.name,
      unit: categorical || tiles.unit === 'date' ? '' : units.label(tiles.unit),
      colors: paletteShown.colors,
      categorical,
      low: units.toDisplay(tiles.unit, domain[0]) ?? 0,
      high: units.toDisplay(tiles.unit, domain[1]) ?? 1,
      levels: tiles.levels,
      dates: tiles.unit === 'date',
      none: tiles.tilejson.encoding.none !== undefined,
    }
  })

  $effect(() => {
    if (!tiles || !paletteShown || !legend) return oninfo?.(null)
    const info: DataInfo = {
      title: tiles.tilejson.name,
      unit: tiles.unit,
      step: tiles.step,
      defaultPalette,
      kind: paletteShown.kind,
      low: legend.low,
      high: legend.high,
      subtitle: tiles.tilejson.subtitle ?? undefined,
      caption: tiles.tilejson.caption ?? undefined,
      warnings: tiles.tilejson.warnings ?? [],
      request: tiles.tilejson.request,
    }
    untrack(() => oninfo?.(info))
  })

  // --- The map

  let prefs = $state(untrack(() => loadPrefs(prefsKey)))
  $effect(() => savePrefs(prefsKey, $state.snapshot(prefs)))

  let container: HTMLDivElement
  let wrapper: HTMLDivElement | undefined = $state()
  let legendHeight = $state(0)

  // The scale bar (MapLibre's bottom-left controls) sits just above the legend, so they never overlap
  $effect(() => {
    const m = map
    const height = legend ? legendHeight : 0
    const corner = m?.getContainer().querySelector<HTMLElement>('.maplibregl-ctrl-bottom-left')
    if (corner) corner.style.bottom = height ? `${height + 8}px` : ''
  })
  let mapWidth = $state(0)
  let styleReady = $state(false)

  const SOURCE_PREFIX = 'data-'
  const isOwn = (source: string) => source.startsWith(SOURCE_PREFIX) || source.startsWith('overlay-')
  let shown: { id: string; key: string } | null = null
  let serial = 0

  const overlays = new MapOverlays({
    droughtArea: () => COVERAGE_BOUNDS,
    claimsClick: () => onpick !== undefined,
  })
  $effect(() => {
    const on = (prefs.overlay ? [prefs.overlay] : []) as OverlayId[]
    const overlayOpacity = { ...prefs.opacity }
    untrack(() => overlays.sync(on, overlayOpacity))
  })
  onDestroy(() => {
    overlays.destroy()
    requests.cancel()
  })

  followRoads(() => map)

  const basemapSwitch = new BasemapSwitch(
    untrack(() => prefs.basemap),
    { map: () => map, isOwn, show: (to) => (prefs.basemap = to) },
  )

  // The tiles' layer: added beneath the basemap's labels once the style is in, and replaced when the tiles change
  // (the new one beneath the old, which goes once the new one's tiles are in, so the map doesn't blank)
  $effect(() => {
    const m = map
    const t = tiles
    if (!m || !styleReady || !t) return
    untrack(() => install(m, t))
  })

  function install(m: MapLibreMap, t: Tiles) {
    if (shown?.key === t.key && m.getLayer(shown.id)) return
    const id = `${SOURCE_PREFIX}${++serial}`
    const source: RasterDEMSourceSpecification = {
      type: 'raster-dem',
      tiles: [t.template],
      tileSize: 256,
      minzoom: MIN_ZOOM,
      maxzoom: MAX_ZOOM,
      bounds: t.tilejson.bounds,
      attribution: t.tilejson.attribution,
      ...maplibreEncoding(t.step),
    }
    m.addSource(id, source)
    const previous = shown
    m.addLayer(
      {
        id,
        type: 'color-relief',
        source: id,
        paint: {
          // Nearest, never linear: blending neighbors' bytes would make values that aren't there
          resampling: 'nearest',
          'color-relief-opacity': opacity,
          ...(colors ? { 'color-relief-color': colors } : {}),
        },
      },
      previous && m.getLayer(previous.id) ? previous.id : beneathLabels(m),
    )
    shown = { id, key: t.key }
    values = new TileValues(t.template, t.step, () => hover.refresh())
    hover.refresh() // the label under a still pointer reads the new tiles
    if (previous) {
      const drop = () => {
        if (!m.getStyle()) return
        if (m.getLayer(previous.id)) m.removeLayer(previous.id)
        if (m.getSource(previous.id)) m.removeSource(previous.id)
      }
      const ready = () => {
        if (m.isSourceLoaded(id)) {
          m.off('sourcedata', ready)
          drop()
        }
      }
      m.on('sourcedata', ready)
      // Whatever happens to the new tiles, the old ones go within a few seconds
      setTimeout(() => {
        m.off('sourcedata', ready)
        drop()
      }, 4000)
    }
  }

  // Recoloring is a paint change: the tiles and their requests stay
  $effect(() => {
    const m = map
    const expression = colors
    if (!m || !styleReady || !expression || !shown) return
    if (m.getLayer(shown.id)) m.setPaintProperty(shown.id, 'color-relief-color', expression)
  })
  $effect(() => {
    const m = map
    const o = opacity
    if (!m || !styleReady || !shown) return
    if (m.getLayer(shown.id)) m.setPaintProperty(shown.id, 'color-relief-opacity', o)
  })

  // --- The value under the pointer, from the z8 tile's pixels

  let values: TileValues | null = null

  function describeValue(value: PixelValue | undefined): string {
    if (value === undefined) return 'Loading…'
    if (value === null) return 'No data'
    if (value === 'none') return 'None'
    if (!tiles) return ''
    if (paletteShown?.kind === 'categorical' && tiles.levels) return tiles.levels[value] ?? String(value)
    if (tiles.unit === 'index') return String(value)
    if (tiles.unit === 'date') return formatDays(value)
    return units.format(tiles.unit, value)
  }

  const hover = new MapHover(
    (m, point) => {
      if (!values || !tiles) return []
      const { lng, lat } = m.unproject(point)
      return [describeValue(values.at(lng, lat)), `${lat.toFixed(3)}°N, ${Math.abs(lng).toFixed(3)}°W`]
    },
    () => wrapper,
  )

  async function pick(event: MapMouseEvent) {
    if (!onpick || !values || !tiles) return
    const { lng, lat } = event.lngLat
    const unit = tiles.unit
    const value = await values.atLoaded(lng, lat)
    onpick({ lat, lng, value, unit, text: describeValue(value) })
  }

  onMount(() => {
    const cleanups: (() => void)[] = []
    const remove = createMap(
      container,
      prefs.basemap,
      (m, maplibre) => {
        map = m
        m.addControl(
          new maplibre.ScaleControl({ unit: units.system === 'metric' ? 'metric' : 'imperial' }),
          'bottom-left',
        )
        // The data goes on as soon as the style is in, not after the basemap's first tiles ('load')
        m.once('style.load', () => (styleReady = true))
        m.on('load', () => {
          overlays.attach(m)
          // MapLibre opens the compact credit at first; on a phone it would cover the legend until the map is moved
          if (m.getContainer().clientWidth < 640) {
            m.getContainer().querySelector('.maplibregl-compact-show')?.classList.remove('maplibregl-compact-show')
          }
        })
        m.on('click', (event) => pick(event))
        m.on('moveend', () => {
          const { lng, lat } = m.getCenter()
          prefs.view = { center: [lng, lat], zoom: Math.round(m.getZoom() * 100) / 100 }
        })
        cleanups.push(hover.attach(m))
      },
      prefs.view ?? {},
    )
    return () => {
      cleanups.forEach((cleanup) => cleanup())
      remove()
      map = undefined
    }
  })
</script>

<div
  bind:this={wrapper}
  bind:clientWidth={mapWidth}
  class="relative w-full overflow-hidden rounded-lg border border-line bg-surface {className}"
>
  <div bind:this={container} class="size-full" role="application" aria-label={label}></div>
  <div class="pointer-events-none absolute top-2 left-2 flex w-[calc(100%-4rem)] flex-col gap-2">
    {#if header}
      <div class="pointer-events-auto w-fit max-w-full">{@render header()}</div>
    {/if}
    <div class="flex flex-wrap items-start gap-2 *:pointer-events-auto">
      <BasemapToggle value={prefs.basemap} onchange={(to) => basemapSwitch.change(to)} />
      <MapLayersButton id="{prefsKey}-layers" basemap={prefs.basemap} count={prefs.overlay ? 1 : 0}>
        <OverlayLayers bind:prefs {overlays} {units} />
      </MapLayersButton>
    </div>
    {#if controls}
      <div class="pointer-events-auto w-full max-w-68">{@render controls()}</div>
    {/if}
  </div>
  {#if loading || failure}
    <p
      class="absolute top-12 left-1/2 -translate-x-1/2 rounded-md bg-surface-raised px-2 py-1 text-xs shadow-md ring-1 ring-line
        {failure ? 'text-danger' : 'text-ink-muted'}"
      role="status"
    >
      {failure ?? 'Loading the map…'}
    </p>
  {/if}
  {#if legend}
    <div
      class="pointer-events-none absolute bottom-2 left-2 w-60 max-w-[calc(100%-1rem)]"
      bind:clientHeight={legendHeight}
    >
      <DataLegend {legend} />
    </div>
  {/if}
  <HoverLabel label={hover.label} />
  {#if overlays.probe}
    <OverlayTooltip probe={overlays.probe} {units} width={mapWidth} />
  {/if}
  {#if overlays.notice}
    <div
      class="absolute inset-x-2 bottom-8 flex items-start gap-2 rounded-md border border-line bg-surface-raised p-2 text-sm shadow-lg sm:left-auto sm:max-w-sm"
      role="status"
    >
      <p class="flex-1">{overlays.notice}</p>
      <button
        type="button"
        class="text-ink-muted hover:text-ink"
        aria-label="Dismiss"
        onclick={() => overlays.dismiss()}
      >
        ✕
      </button>
    </div>
  {/if}
</div>
