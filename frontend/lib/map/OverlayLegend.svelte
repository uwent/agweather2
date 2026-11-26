<!-- WISP 3: app/frontend/lib/map/OverlayLegend.svelte (adapted: our units module, rain depths stored in inches) -->
<script lang="ts">
  import type { Units } from '@/lib/units'

  import type { Legend } from './overlays'

  let { legend, units }: { legend: Legend; units: Units } = $props()
</script>

<div class="space-y-1.5">
  {#if legend.kind === 'ramp'}
    <div>
      <div class="h-2.5 rounded-sm" style:background="linear-gradient(to right, {legend.colors.join(', ')})"></div>
      <div class="mt-0.5 flex justify-between text-xs text-ink-muted">
        <span>{legend.start}</span><span>{legend.end}</span>
      </div>
    </div>
  {:else if legend.kind === 'depths'}
    <div>
      <ul class="grid grid-cols-5 gap-1 text-xs">
        {#each legend.items as item (item.inches)}
          <li class="flex flex-col items-center">
            <span class="h-2.5 w-full rounded-sm" style:background={item.color}></span>
            <span class="text-ink-muted tabular-nums">{units.format('in', item.inches, { unit: false })}</span>
          </li>
        {/each}
      </ul>
      <p class="text-xs text-ink-muted">Each color starts at the amount shown, in {units.label('in')}</p>
    </div>
  {:else}
    <ul class="space-y-0.5 text-xs">
      {#each legend.items as item (item.label)}
        <li class="flex items-center gap-1.5">
          <span class="size-3 rounded-sm border border-line" style:background={item.color}></span>{item.label}
        </li>
      {/each}
    </ul>
  {/if}
</div>
