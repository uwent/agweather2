<script lang="ts" module>
  /** What a data map's legend shows, in the reader's units */
  export type DataLegendSpec = {
    title: string
    /** The unit's label (°F, in, °F·d), or '' */
    unit: string
    /** A continuous palette over low..high, or a swatch per level */
    colors: string[]
    categorical: boolean
    low: number
    high: number
    /** The levels' names, for a categorical map */
    levels?: string[]
    /** Values are dates (days since 1970-01-01) */
    dates: boolean
    /** Whether the map can show "none" (a first or last day not found) */
    none: boolean
  }
</script>

<script lang="ts">
  import { formatNumber } from '@/lib/units'

  import { cssGradient, fittedTicks, formatDays, NONE_COLOR } from './dataTiles'

  // A data map's legend, placed by DataMap at its lower left with the scale bar above it: the layer's title, then a
  // color bar with round ticks in the reader's units, or a swatch per level
  let { legend }: { legend: DataLegendSpec } = $props()

  const ticks = $derived(
    legend.categorical
      ? []
      : fittedTicks(legend.low, legend.high, legend.dates ? (v) => formatDays(v, false) : formatNumber),
  )
</script>

<div
  class="w-full rounded-md bg-surface-raised/90 px-2.5 py-1.5 text-xs text-ink shadow-md ring-1 ring-line"
  data-testid="data-legend"
>
  <p class="font-medium">
    {legend.title}{legend.unit && !legend.categorical ? ` (${legend.unit})` : ''}
  </p>
  {#if legend.categorical}
    <ul class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
      {#each legend.colors as color, level (level)}
        <li class="inline-flex items-center gap-1">
          <span class="size-3 shrink-0 rounded-xs ring-1 ring-black/20" style:background-color={color}></span>
          {legend.levels?.[level] ?? `Level ${level}`}
        </li>
      {/each}
    </ul>
  {:else}
    <div class="mt-1 h-3 rounded-xs ring-1 ring-black/20" style:background-image={cssGradient(legend.colors)}></div>
    <div class="relative mt-0.5 h-4">
      {#each ticks as tick (tick.value)}
        <span
          class="absolute top-0 whitespace-nowrap tabular-nums {tick.at < 0.05
            ? ''
            : tick.at > 0.95
              ? '-translate-x-full'
              : '-translate-x-1/2'}"
          style:left="{tick.at * 100}%"
        >
          {tick.label}
        </span>
      {/each}
    </div>
  {/if}
  {#if legend.none}
    <p class="mt-1 inline-flex items-center gap-1">
      <span class="size-3 shrink-0 rounded-xs ring-1 ring-black/20" style:background-color={NONE_COLOR}></span>None
    </p>
  {/if}
</div>
