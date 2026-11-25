<!-- WISP 3: app/frontend/lib/charts/ChartCard.svelte (copied) -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  import InfoTip from '../components/InfoTip.svelte'
  import Chart from './Chart.svelte'
  import DataDialog from './DataDialog.svelte'
  import type { ChartView, EChartsCoreOption } from './echarts'
  import type { Palette } from './palette'

  export type ChartTable = {
    columns: string[]
    rows: { date: string; forecast: boolean; values: (string | null)[] }[]
  }

  // A chart in a card: its title, then (top right) a reset button once the chart has been zoomed
  // or had series toggled, and an (i) explaining what it shows. Below it, "Summary and data" opens a
  // dialog (Ben, 2026-11-17: the grid of cards stays even however many are open): the chart in words
  // (also its text alternative), its daily values as a table, and (given download) a button saving
  // them as CSV. controls: shown under the chart. The card fills its grid cell, the link at its foot.
  let {
    title,
    info,
    build,
    height = '12rem',
    summary,
    table,
    subtitle,
    controls,
    download,
    group,
  }: {
    title: string
    info: string
    build: (palette: Palette, view?: ChartView) => EChartsCoreOption
    height?: string
    summary: string
    table: () => ChartTable
    subtitle?: Snippet
    controls?: Snippet
    download?: () => void
    /** Charts that zoom together (Chart's group) */
    group?: string
  } = $props()

  let chart: Chart | undefined = $state()
  let modified = $state(false)
  let open = $state(false)
</script>

<div class="flex h-full flex-col rounded-lg border border-line bg-surface p-3">
  <div class="flex items-start justify-between gap-2">
    <h3 class="text-sm font-medium">{title} {@render subtitle?.()}</h3>
    <div class="-mt-1 -mr-1 flex shrink-0 items-center">
      {#if modified}
        <button
          type="button"
          class="inline-flex size-6 items-center justify-center rounded-full text-ink-muted hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600"
          aria-label="Reset {title} chart"
          title="Reset chart"
          onclick={() => chart?.reset()}
        >
          <svg
            viewBox="0 0 24 24"
            class="size-4"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
            <path d="M3 3v5h5" />
          </svg>
        </button>
      {/if}
      <InfoTip text={info} label="About the {title} chart" />
    </div>
  </div>
  <Chart bind:this={chart} bind:modified {height} label="{title}. {summary}" {build} {group} />
  {@render controls?.()}
  <button
    type="button"
    class="mt-auto self-end pt-1 text-xs text-brand-600 hover:underline"
    aria-haspopup="dialog"
    onclick={() => (open = true)}
  >
    Summary and data
  </button>
  <DataDialog
    bind:open
    title="{title}: summary and data"
    name="the {title} data"
    label={title}
    {summary}
    {table}
    {download}
  />
</div>
