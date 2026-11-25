<!-- WISP 3: app/frontend/lib/map/MapLegend.svelte (adapted: its Swatch type from lib/outlines/layers.ts, which isn't taken, defined here) -->
<script lang="ts" module>
  /** A legend entry, drawn as the map draws it */
  export type Swatch = {
    label: string
    color: string
    width: number
    filled?: boolean
    dashed?: boolean
    /** A ring, on a dark casing */
    round?: boolean
  }
</script>

<script lang="ts">
  // A map's legend of shapes and lines, over its lower left corner (the attribution is at the right),
  // a line per row. Each swatch is drawn as the map draws it, on a dark tile like the imagery: an
  // outline's line (dashed as the map's dashes, at this size), a filled shape's tint, a ring on its casing.
  let { rows }: { rows: Swatch[][] } = $props()

  const shown = $derived(rows.filter((row) => row.length))
</script>

{#if shown.length}
  <div
    class="bg-surface-raised/90 text-ink ring-line pointer-events-none absolute bottom-2 left-2
      max-w-[calc(100%-4rem)] space-y-0.5 rounded-md px-2 py-1 text-xs shadow-md ring-1"
  >
    {#each shown as row, index (index)}
      <p class="flex flex-wrap gap-x-3">
        {#each row as swatch (swatch.label)}
          <span class="inline-flex items-center gap-1">
            <svg viewBox="0 0 22 16" class="h-4 w-5.5 shrink-0" aria-hidden="true">
              <rect width="22" height="16" rx="2" fill="#2f3a2c" />
              {#if swatch.round}
                <circle cx="11" cy="8" r="5" fill="none" stroke="#0c2d48" stroke-width={swatch.width + 1.5} />
                <circle
                  cx="11"
                  cy="8"
                  r="5"
                  fill={swatch.filled ? swatch.color : 'none'}
                  fill-opacity={swatch.filled ? 0.35 : undefined}
                  stroke={swatch.color}
                  stroke-width={swatch.width}
                />
              {:else}
                <rect
                  x="4"
                  y="3.5"
                  width="14"
                  height="9"
                  fill={swatch.filled ? swatch.color : 'none'}
                  fill-opacity={swatch.filled ? 0.35 : undefined}
                  stroke={swatch.color}
                  stroke-width={swatch.width * 0.75}
                  stroke-dasharray={swatch.dashed ? '3 2.5' : undefined}
                />
              {/if}
            </svg>{swatch.label}
          </span>
        {/each}
      </p>
    {/each}
  </div>
{/if}
