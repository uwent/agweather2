<script lang="ts" module>
  import type { TileCategory } from './dataTiles'

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
    /** Levels' names by value (a risk map's), or a crop's stages with their codes (a stage map's color bar is
     * labelled with the codes) */
    categories?: TileCategory[]
    /** Values are dates (days since 1970-01-01) */
    dates: boolean
    /** Whether the map can show "none" (a first or last day not found) */
    none: boolean
  }
</script>

<script lang="ts">
  import { formatNumber } from '@/lib/units'

  import { categoryCode, cssGradient, fittedTicks, formatDays, NONE_COLOR } from './dataTiles'

  // A data map's legend, placed by DataMap at its lower left with the scale bar above it: the layer's title, then a
  // color bar with round ticks in the reader's units (a stage map's labelled with the stages' codes), or a swatch
  // per level named in words; and a hatched swatch for "No data", where the map is left clear
  let { legend }: { legend: DataLegendSpec } = $props()

  const stages = $derived(legend.categories?.some((c) => c.value < 0) ? legend.categories : undefined)
  const ticks = $derived.by(() => {
    if (legend.categorical) return []
    if (stages) return fittedTicks(legend.low, legend.high, (v) => (Number.isInteger(v) ? categoryCode(stages, v) : ''))
    return fittedTicks(legend.low, legend.high, legend.dates ? (v) => formatDays(v, false) : formatNumber)
  })
  const levelName = (level: number) => legend.categories?.find((c) => c.value === level)?.name ?? `Level ${level}`
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
          {levelName(level)}
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
  <p class="mt-1 flex flex-wrap gap-x-3">
    {#if legend.none}
      <span class="inline-flex items-center gap-1">
        <span class="size-3 shrink-0 rounded-xs ring-1 ring-black/20" style:background-color={NONE_COLOR}></span>None
      </span>
    {/if}
    <span class="inline-flex items-center gap-1" data-testid="legend-no-data">
      <span class="no-data-swatch size-3 shrink-0 rounded-xs ring-1 ring-ink-muted/60" aria-hidden="true"></span>No data
    </span>
  </p>
</div>

<style>
  /* Missing cells are drawn clear, so the basemap shows through: the swatch says so with hatching over nothing */
  .no-data-swatch {
    background-image: repeating-linear-gradient(135deg, var(--color-ink-muted) 0 1px, transparent 1px 3px);
  }
</style>
