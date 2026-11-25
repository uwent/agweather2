<!-- Development only (/dev/map): DataMap on the API's tiles (D119) with a small form, and WISP 3's chart core on fake data, for review. -->
<script lang="ts">
  import type { Map as MapLibreMap } from 'maplibre-gl'

  import { get } from '@/lib/api'
  import ChartCard, { type ChartTable } from '@/lib/charts/ChartCard.svelte'
  import type { EChartsCoreOption } from '@/lib/charts/echarts'
  import { baseOption, type Palette } from '@/lib/charts/palette'
  import { forecastShading } from '@/lib/charts/shading'
  import PlaceSearch from '@/lib/components/PlaceSearch.svelte'
  import { downloadCsv, frontmatter, toCsv } from '@/lib/csv'
  import { addDays, formatDate } from '@/lib/dates'
  import DataMap, { type DataInfo, type DataPick, type DataScale } from '@/lib/map/DataMap.svelte'
  import { currentUnits, parseNumber } from '@/lib/units'
  import type { LayerInfo, LayersResponse, PaletteInfo } from '@/types/api'

  const units = $derived(currentUnits())

  // --- The data map: a layer, a day, a palette and a scale

  // A choice is a layer and its settings; its value is the layer id, or the id and a suffix for a variant
  const LAYERS: { key: string; id: string; params: Record<string, string>; name?: string }[] = [
    { key: 'air_temperature_max', id: 'air_temperature_max', params: {} },
    { key: 'air_temperature_min', id: 'air_temperature_min', params: {} },
    {
      key: 'first-frost',
      id: 'air_temperature_min',
      params: { first: 'frost' },
      name: 'First frost (32 °F) since July 1',
    },
    { key: 'dd_modified_50_86', id: 'dd_modified_50_86', params: {} },
    { key: 'precipitation_sum', id: 'precipitation_sum', params: {} },
    { key: 'precipitation_total', id: 'precipitation_total', params: {} },
    { key: 'tar-spot', id: 'tar-spot', params: {} },
  ]

  let layerId = $state('air_temperature_max')
  let date = $state('')
  let paletteId = $state('')
  let scaleMode = $state<'auto' | 'default'>('auto')
  let lowText = $state('')
  let highText = $state('')
  let info = $state<DataInfo | null>(null)
  let picked = $state<DataPick | null>(null)
  let map: MapLibreMap | undefined = $state()

  let layers = $state<LayerInfo[]>([])
  let palettes = $state<PaletteInfo[]>([])
  get<LayersResponse>('/layers').then((body) => {
    layers = body.data
    date ||= body.data.find((l) => l.id === layerId)?.range.last ?? ''
  })
  get<PaletteInfo[]>('/palettes').then((body) => (palettes = body))

  const choice = $derived(LAYERS.find((l) => l.key === layerId) ?? LAYERS[0])
  const params = $derived(choice.params)
  const layerName = (l: (typeof LAYERS)[number]) => l.name ?? layers.find((info) => info.id === l.id)?.title ?? l.id
  // A categorical map takes only a categorical palette with as many levels; a continuous one no categorical one
  const choices = $derived(
    palettes
      .filter((p) =>
        info?.kind === 'categorical'
          ? p.kind === 'categorical' &&
            p.colors.length === palettes.find((d) => d.id === info?.defaultPalette)?.colors.length
          : p.kind !== 'categorical',
      )
      .map((p) => p.id),
  )
  const scale = $derived.by((): DataScale => {
    const low = parseNumber(lowText)
    const high = parseNumber(highText)
    const lowValue = low.ok ? low.value : null
    const highValue = high.ok ? high.value : null
    if (lowValue === null && highValue === null) return scaleMode
    return { low: lowValue, high: highValue }
  })

  // For measuring from Playwright (development only)
  $effect(() => {
    ;(window as unknown as { agwDataMap?: MapLibreMap }).agwDataMap = map
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
  <title>Data map and chart demo</title>
</svelte:head>

<section class="space-y-4">
  <h1 class="text-2xl font-semibold">Data map and chart demo</h1>
  <p class="max-w-prose text-sm text-ink-muted">
    A development page for reviewing the data map and the chart parts ported from WISP 3. The map draws the API's data
    tiles beneath the basemap's borders and place names, colored in the browser.
  </p>

  <form class="flex flex-wrap items-end gap-3 text-sm" onsubmit={(event) => event.preventDefault()}>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">Layer</span>
      <select class="max-w-full rounded-md border border-line bg-surface px-2 py-1" bind:value={layerId} name="layer">
        {#each LAYERS as l (l.key)}<option value={l.key}>{layerName(l)}</option>{/each}
      </select>
    </label>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">Date</span>
      <input type="date" class="rounded-md border border-line bg-surface px-2 py-1" bind:value={date} name="date" />
    </label>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">Palette</span>
      <select class="rounded-md border border-line bg-surface px-2 py-1" bind:value={paletteId} name="palette">
        <option value="">The layer's ({info?.defaultPalette ?? '…'})</option>
        {#each choices as id (id)}<option value={id}>{id}</option>{/each}
        {#each choices as id (`${id}_r`)}<option value="{id}_r">{id} reversed</option>{/each}
      </select>
    </label>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">Scale</span>
      <select class="rounded-md border border-line bg-surface px-2 py-1" bind:value={scaleMode} name="scale">
        <option value="auto">This map's range</option>
        <option value="default">The layer's fixed range</option>
      </select>
    </label>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">Low{info ? ` (${units.label(info.unit)})` : ''}</span>
      <input
        class="w-20 rounded-md border border-line bg-surface px-2 py-1"
        bind:value={lowText}
        name="low"
        inputmode="decimal"
      />
    </label>
    <label class="flex flex-col gap-1">
      <span class="text-ink-muted">High{info ? ` (${units.label(info.unit)})` : ''}</span>
      <input
        class="w-20 rounded-md border border-line bg-surface px-2 py-1"
        bind:value={highText}
        name="high"
        inputmode="decimal"
      />
    </label>
  </form>

  {#if date}
    <DataMap
      layer={choice.id}
      time={date}
      {params}
      palette={paletteId || null}
      {scale}
      label="Map of {info?.title ?? 'the data'}"
      prefsKey="dev-map"
      bind:map
      oninfo={(next) => (info = next)}
      onpick={(next) => (picked = next)}
    >
      {#snippet controls()}<PlaceSearch {map} />{/snippet}
    </DataMap>
  {/if}
  <p class="text-sm" data-testid="picked">
    {#if picked}
      {picked.lat.toFixed(4)}, {picked.lng.toFixed(4)}: {picked.text}
      <span class="text-ink-muted">(stored: {picked.value} {picked.unit})</span>
    {:else}
      <span class="text-ink-muted">Click the map for the value of a cell.</span>
    {/if}
  </p>

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
