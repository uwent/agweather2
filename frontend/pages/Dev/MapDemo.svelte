<!-- Development only (/dev/map, wave 1): WISP 3's map and chart cores on fake data, for review. Wave 2 deletes or replaces it. -->
<script lang="ts">
  import { onDestroy, onMount, untrack } from 'svelte'
  import type { Map as MapLibreMap } from 'maplibre-gl'
  import 'maplibre-gl/dist/maplibre-gl.css'

  import ChartCard, { type ChartTable } from '@/lib/charts/ChartCard.svelte'
  import type { EChartsCoreOption } from '@/lib/charts/echarts'
  import { baseOption, type Palette } from '@/lib/charts/palette'
  import { forecastShading } from '@/lib/charts/shading'
  import PlaceSearch from '@/lib/components/PlaceSearch.svelte'
  import { downloadCsv, frontmatter, toCsv } from '@/lib/csv'
  import { addDays, formatDate } from '@/lib/dates'
  import { BasemapSwitch, beneathLabels } from '@/lib/map/basemaps'
  import BasemapToggle from '@/lib/map/BasemapToggle.svelte'
  import { createMap } from '@/lib/map/createMap'
  import { COVERAGE_BOUNDS } from '@/lib/map/coverage'
  import HoverLabel from '@/lib/map/HoverLabel.svelte'
  import { MapHover } from '@/lib/map/hover.svelte'
  import MapLayersButton from '@/lib/map/MapLayersButton.svelte'
  import { MapOverlays } from '@/lib/map/mapOverlays.svelte'
  import OverlayLayers from '@/lib/map/OverlayLayers.svelte'
  import type { OverlayId } from '@/lib/map/overlays'
  import OverlayTooltip from '@/lib/map/OverlayTooltip.svelte'
  import { loadPrefs, savePrefs } from '@/lib/map/prefs'
  import { followRoads } from '@/lib/map/roads.svelte'
  import { units as unitsFor } from '@/lib/units'

  const units = unitsFor('imperial')

  // --- The map: basemap, overlays, place search, and a stand-in data layer beneath the labels (D119)

  let prefs = $state(loadPrefs('dev-map'))
  $effect(() => savePrefs('dev-map', $state.snapshot(prefs)))

  let container: HTMLDivElement
  let wrapper: HTMLDivElement | undefined = $state()
  let map: MapLibreMap | undefined = $state()
  let mapWidth = $state(0)
  let placeSearch = $state<PlaceSearch>()

  const DATA = 'demo-data'
  const isOwn = (source: string) => source === DATA || source.startsWith('overlay-')

  const overlays = new MapOverlays({ droughtArea: () => COVERAGE_BOUNDS })
  $effect(() => {
    const shown = (prefs.overlay ? [prefs.overlay] : []) as OverlayId[]
    const opacity = { ...prefs.opacity }
    untrack(() => overlays.sync(shown, opacity))
  })
  onDestroy(() => overlays.destroy())

  followRoads(() => map)

  const hover = new MapHover(
    (m, point) => {
      const { lng, lat } = m.unproject(point)
      return [`${lat.toFixed(3)}°N, ${Math.abs(lng).toFixed(3)}°W`]
    },
    () => wrapper,
  )

  const basemapSwitch = new BasemapSwitch(
    untrack(() => prefs.basemap),
    { map: () => map, isOwn, show: (to) => (prefs.basemap = to) },
  )

  // A box over southern Wisconsin, standing in for the data tiles wave 2 adds
  function addData(m: MapLibreMap) {
    if (m.getSource(DATA)) return
    m.addSource(DATA, {
      type: 'geojson',
      data: {
        type: 'Polygon',
        coordinates: [
          [
            [-91.5, 42.5],
            [-87.5, 42.5],
            [-87.5, 44.5],
            [-91.5, 44.5],
            [-91.5, 42.5],
          ],
        ],
      },
    })
    m.addLayer(
      { id: DATA, type: 'fill', source: DATA, paint: { 'fill-color': '#f46d43', 'fill-opacity': 0.55 } },
      beneathLabels(m),
    )
  }

  onMount(() => {
    const cleanups: (() => void)[] = []
    const remove = createMap(
      container,
      prefs.basemap,
      (m, maplibre) => {
        map = m
        m.addControl(new maplibre.ScaleControl({ unit: 'imperial' }), 'bottom-left')
        m.on('load', () => {
          addData(m)
          overlays.attach(m)
        })
        m.on('click', () => placeSearch?.close())
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

  // --- The chart: two panels sharing a time axis, a forecast, an estimated day and a missing one

  const START = '2026-07-01'
  const DAYS = 21
  const FORECAST_FROM = 14
  const ESTIMATED = 5
  const MISSING = 9
  const dates = Array.from({ length: DAYS }, (_, i) => addDays(START, i))
  const high = dates.map((_, i) => (i === MISSING ? null : Math.round(82 + 7 * Math.sin(i / 3))))
  const low = dates.map((_, i) => (i === MISSING ? null : Math.round(61 + 5 * Math.sin(i / 3 + 1))))
  const rain = dates.map((_, i) =>
    i === MISSING ? null : [3, 4, 11, 12, 16, 19].includes(i) ? (i % 5) * 0.21 + 0.05 : 0,
  )

  function build(palette: Palette): EChartsCoreOption {
    const base = baseOption(palette)
    const labels = dates.map((date) => formatDate(date))
    const shading = forecastShading({ dates: labels, from: FORECAST_FROM, grids: 2, axisOffset: 2, palette })
    const zoomAxes = [0, 1, ...shading.xAxisIndexes]
    const point = (value: number | null, i: number) =>
      i === ESTIMATED ? { value, symbol: 'emptyCircle', symbolSize: 7 } : value
    const temperature = (name: string, data: (number | null)[], color: string) => ({
      name,
      type: 'line',
      data: data.map(point),
      color,
      xAxisIndex: 0,
      yAxisIndex: 0,
      symbol: 'none',
      lineStyle: { width: 2 },
      z: 3,
    })
    return {
      animation: base.animation,
      textStyle: base.textStyle,
      tooltip: base.tooltip,
      legend: { data: ['High', 'Low', 'Precipitation'], top: 0, textStyle: { color: palette.ink } },
      grid: [
        { top: 44, height: '36%', left: 44, right: 12 },
        { top: '64%', bottom: 44, left: 44, right: 12 },
      ],
      xAxis: [
        { type: 'category', data: labels, gridIndex: 0, axisLabel: { show: false }, axisLine: base.axisLine },
        { type: 'category', data: labels, gridIndex: 1, axisLabel: base.axisLabel, axisLine: base.axisLine },
        ...shading.xAxis,
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, name: '°F', scale: true, axisLabel: base.axisLabel, splitLine: base.splitLine },
        { type: 'value', gridIndex: 1, name: 'in', axisLabel: base.axisLabel, splitLine: base.splitLine },
        ...shading.yAxis,
      ],
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      dataZoom: [
        { type: 'inside', xAxisIndex: zoomAxes },
        { type: 'slider', xAxisIndex: zoomAxes, height: 14, bottom: 6, textStyle: { color: palette.inkMuted } },
      ],
      series: [
        ...shading.series,
        {
          ...temperature('High', high, palette.temperature.max),
          symbol: 'circle',
          showSymbol: false,
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: palette.inkMuted, type: 'dashed' },
            label: { formatter: 'Today', position: 'insideEndTop', color: palette.inkMuted },
            data: [{ xAxis: FORECAST_FROM - 1 }],
          },
          markArea: {
            silent: true,
            itemStyle: { color: 'transparent' },
            label: { position: 'insideTop', color: palette.inkMuted, fontSize: 11 },
            data: [[{ name: 'Forecast', xAxis: FORECAST_FROM }, { xAxis: DAYS - 1 }]],
          },
        },
        temperature('Low', low, palette.temperature.min),
        {
          name: 'Precipitation',
          type: 'bar',
          data: rain,
          color: palette.precipitation,
          xAxisIndex: 1,
          yAxisIndex: 1,
          z: 3,
        },
      ],
    }
  }

  const summary = `High temperatures run from ${Math.min(...high.filter((v) => v !== null))} to ${Math.max(...high.filter((v) => v !== null))} °F over these 3 weeks, the last 7 days a forecast. July 6 is estimated and July 10 is missing.`

  const table = (): ChartTable => ({
    columns: ['High (°F)', 'Low (°F)', 'Precipitation (in)'],
    rows: dates
      .map((date, i) => ({
        date,
        forecast: i >= FORECAST_FROM,
        values: [high[i], low[i], rain[i]].map((v, j) => (v === null ? null : j === 2 ? v.toFixed(2) : String(v))),
      }))
      .reverse(),
  })

  function download() {
    const rows = [
      ...frontmatter('AgWeather demo data', { Note: 'Fake values for review' }),
      ['Date', 'Forecast', 'High (°F)', 'Low (°F)', 'Precipitation (in)'],
      ...dates.map((date, i) => [date, i >= FORECAST_FROM ? 'yes' : 'no', high[i], low[i], rain[i]]),
    ]
    downloadCsv('agweather-demo.csv', toCsv(rows))
  }
</script>

<svelte:head>
  <title>Map and chart demo</title>
</svelte:head>

<section class="space-y-4">
  <h1 class="text-2xl font-semibold">Map and chart demo</h1>
  <p class="text-ink-muted max-w-prose text-sm">
    A development page for reviewing the map and chart parts ported from WISP 3. The orange box stands in for a data
    layer: the basemap's borders and place names should draw above it.
  </p>

  <div
    bind:this={wrapper}
    bind:clientWidth={mapWidth}
    class="border-line bg-surface relative h-[28rem] w-full overflow-hidden rounded-lg border sm:h-[32rem]"
  >
    <div bind:this={container} class="size-full" role="application" aria-label="Demo map of the coverage"></div>
    <div class="pointer-events-none absolute top-2 left-2 flex w-[calc(100%-4rem)] flex-col gap-2">
      <div class="flex flex-wrap items-start gap-2 *:pointer-events-auto">
        <BasemapToggle value={prefs.basemap} onchange={(to) => basemapSwitch.change(to)} />
        <MapLayersButton id="demo-map-layers" basemap={prefs.basemap} count={prefs.overlay ? 1 : 0}>
          <OverlayLayers bind:prefs {overlays} {units} />
        </MapLayersButton>
      </div>
      <div class="pointer-events-auto w-full max-w-68">
        <PlaceSearch bind:this={placeSearch} {map} />
      </div>
    </div>
    <HoverLabel label={hover.label} />
    {#if overlays.probe}
      <OverlayTooltip probe={overlays.probe} {units} width={mapWidth} />
    {/if}
    {#if overlays.notice}
      <div
        class="border-line bg-surface-raised absolute right-2 bottom-8 left-2 flex items-start gap-2 rounded-md border p-2 text-sm shadow-lg sm:left-auto sm:max-w-sm"
        role="status"
      >
        <p class="flex-1">{overlays.notice}</p>
        <button
          type="button"
          class="text-ink-muted hover:text-ink"
          aria-label="Dismiss"
          onclick={() => overlays.dismiss()}>✕</button
        >
      </div>
    {/if}
  </div>

  <div class="max-w-3xl">
    <ChartCard
      title="Temperature and precipitation"
      info="Daily high and low temperature and precipitation. The shaded days are a forecast; a hollow point is an estimated day, and a gap is a missing one."
      {build}
      height="20rem"
      {summary}
      {table}
      {download}
    />
  </div>
</section>
