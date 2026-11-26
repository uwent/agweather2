<!-- WISP 3: app/frontend/lib/charts/Chart.svelte (copied) -->
<script lang="ts">
  import { onMount } from 'svelte'

  import type { ECharts } from 'echarts/core'

  import type { ChartView, EChartsCoreOption } from './echarts'
  import { onThemeChange } from '../theme'
  import { join, resetGroup, share, type LinkedChart } from './link'
  import { readPalette, type Palette } from './palette'

  // build turns the current palette into the chart's option; it's rebuilt when the data it reads
  // changes or the theme switches. It also gets the days in view once the user zooms, for values
  // that depend on them (running totals). modified is true once the user zooms or toggles a series;
  // reset() puts the chart back as it opened.
  // group: charts that zoom together (lib/charts/link.ts). In one, zooming doesn't count as
  // modified (every chart in it would offer a reset); zoomed says whether the group is zoomed, and
  // reset() puts the whole group back. inView: the days in view once zoomed (indexes into the x
  // axis), undefined while it shows the days it opened on.
  let {
    build,
    height = '18rem',
    label,
    modified = $bindable(false),
    zoomed = $bindable(false),
    inView = $bindable(),
    group,
  }: {
    build: (palette: Palette, view?: ChartView) => EChartsCoreOption
    height?: string
    label: string
    modified?: boolean
    zoomed?: boolean
    inView?: ChartView
    group?: string
  } = $props()

  let element: HTMLDivElement
  let chart: ECharts | undefined = $state()
  let palette: Palette | undefined = $state()
  // The user's zoom (percent of the x range) and legend choices, kept when the data reloads after an edit
  let zoom: { start: number; end: number } | undefined
  let view: ChartView | undefined
  let legend: Record<string, boolean> | undefined

  function withState(option: EChartsCoreOption): EChartsCoreOption {
    let result = option
    if (zoom && Array.isArray(option.dataZoom)) {
      const { start, end } = zoom
      result = {
        ...result,
        dataZoom: option.dataZoom.map((dz: object) => ({
          ...dz,
          start,
          end,
          startValue: undefined,
          endValue: undefined,
        })),
      }
    }
    if (legend && option.legend) result = { ...result, legend: { ...(option.legend as object), selected: legend } }
    return result
  }

  export function reset() {
    legend = undefined
    modified = false
    // In a group, the zoom is the group's: resetZoom() puts it back
    if (!group) {
      zoom = view = inView = undefined
      zoomed = false
    }
    if (chart && palette) chart.setOption(withState(build(palette, view)), { notMerge: true })
  }

  /** Every chart in the group back to the days it opened on */
  export function resetZoom() {
    if (group) resetGroup(group)
    else reset()
  }

  // In a group: the range another chart passed on, and a rebuild for it once the dragging pauses
  // (a rebuild per chart per frame would make ten charts stutter)
  let following = false
  let rebuildTimer: ReturnType<typeof setTimeout> | undefined
  const linked: LinkedChart = {
    zoom: ({ start, end }) => {
      following = true
      try {
        chart?.dispatchAction({ type: 'dataZoom', start, end })
      } finally {
        following = false
      }
    },
    reset: () => {
      clearTimeout(rebuildTimer)
      zoom = view = inView = undefined
      zoomed = false
      if (chart && palette) chart.setOption(withState(build(palette)), { notMerge: true })
    },
  }

  // ECharts is the largest chunk on the pages with charts, so it loads after the page renders
  // (the chart's box keeps its height meanwhile)
  onMount(() => {
    let destroyed = false
    let cleanup: (() => void) | undefined
    import('./echarts').then(({ echarts }) => {
      if (destroyed) return
      cleanup = start(echarts.init(element, null, { renderer: 'canvas' }))
    })
    return () => {
      destroyed = true
      cleanup?.()
    }
  })

  function start(instance: ECharts) {
    chart = instance
    palette = readPalette()
    chart.on('datazoom', () => {
      const option = chart?.getOption()
      const [dz] = (option?.dataZoom as { start: number; end: number }[] | undefined) ?? []
      if (!dz || !palette) return
      zoom = { start: dz.start, end: dz.end }
      const count = ((option?.xAxis as { data?: unknown[] }[] | undefined)?.[0]?.data?.length ?? 1) - 1
      view = { start: Math.round((dz.start / 100) * count), end: Math.round((dz.end / 100) * count) }
      inView = view
      zoomed = true
      const rebuild = () => palette && chart?.setOption(withState(build(palette, view)), { lazyUpdate: true })
      if (!group) {
        modified = true
        return rebuild()
      }
      if (!following) share(group, linked, zoom)
      clearTimeout(rebuildTimer)
      rebuildTimer = setTimeout(rebuild, 150)
    })
    chart.on('legendselectchanged', (event) => {
      legend = (event as { selected: Record<string, boolean> }).selected
      modified = true
    })
    const offTheme = onThemeChange(() => (palette = readPalette()))
    // Canvas text uses whatever font is loaded when it's drawn; redraw once the web fonts are in
    document.fonts?.ready.then(() => chart && (palette = readPalette()))
    const observer = new ResizeObserver(() => chart?.resize())
    observer.observe(element)
    const leave = group ? join(group, linked) : undefined
    return () => {
      leave?.()
      clearTimeout(rebuildTimer)
      offTheme()
      observer.disconnect()
      chart?.dispose()
    }
  }

  $effect(() => {
    if (chart && palette) chart.setOption(withState(build(palette, view)), { notMerge: true, lazyUpdate: true })
  })
</script>

<div bind:this={element} style:height role="img" aria-label={label} class="w-full" data-chart></div>
