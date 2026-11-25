<!-- WISP 3: app/frontend/lib/map/OverlayTooltip.svelte (adapted: our units module, rain depths stored in inches) -->
<script lang="ts">
  import type { Units } from '@/lib/units'

  import { flipsAt, labelAnchor } from './hover.svelte'
  import type { Probe, ProbeValue } from './mapOverlays.svelte'

  // What the shown layers have under the pointer or a tap (MapOverlays.probe), kept inside the map:
  // just above where the hover label hangs (labelAnchor), flipped to the pointer's left with it, so
  // the two don't cover each other. Without room above (near the map's top), it goes below, on the
  // pointer's other side from the hover label where there's room.
  let { probe, units, width }: { probe: Probe; units: Units; width: number } = $props()

  let tooltipHeight = $state(0)
  const above = $derived(labelAnchor(probe.x, probe.y, false).y - 1 - tooltipHeight >= 0)
  // The hover label's side, or below it the other side where there's room (it's at most 16rem wide)
  const labelFlipped = $derived(flipsAt(probe.x, width))
  const flip = $derived(above || (!labelFlipped && probe.x < 280) ? labelFlipped : !labelFlipped)
  const anchor = $derived(labelAnchor(probe.x, probe.y, flip))
  const left = $derived(anchor.x)
  const top = $derived(above ? anchor.y - 1 : anchor.y + 1)
  const shift = $derived(`${flip ? '-100%' : '0'} ${above ? '-100%' : '0'}`)

  const depth = (inches: number) => units.format('in', inches)
  function describe(value: ProbeValue, none: string): { text: string; color?: string; muted?: boolean } {
    if (value === 'loading') return { text: '…', muted: true }
    if (value === 'unavailable') return { text: 'Unavailable', muted: true }
    if (value === 'outside') return { text: 'No data outside the US', muted: true }
    if (value.kind === 'none') return { text: none }
    if (value.kind === 'text') return { text: value.text, color: value.color }
    if (value.upTo === undefined) return { text: `About ${depth(value.inches)}` }
    if (value.upTo === null) return { text: `${depth(value.inches)} or more` }
    return { text: `${units.format('in', value.inches, { unit: false })}–${depth(value.upTo)}` }
  }
</script>

<div
  class="border-line bg-surface-raised pointer-events-none absolute z-30 max-w-64 rounded-md border px-2.5 py-1.5 text-xs
    shadow-lg"
  style:left="{left}px"
  style:top="{top}px"
  style:translate={shift}
  bind:offsetHeight={tooltipHeight}
  role="status"
  aria-live="polite"
>
  <dl class="space-y-0.5">
    {#each probe.items as item (item.id)}
      {@const shown = describe(item.value, item.none)}
      <div>
        <dt class="text-ink-muted">{item.name}</dt>
        <dd class="flex items-center gap-1.5 font-medium {shown.muted ? 'text-ink-muted font-normal' : ''}">
          {#if shown.color}<span class="border-line size-2.5 shrink-0 rounded-sm border" style:background={shown.color}
            ></span>{/if}{shown.text}
        </dd>
      </div>
    {/each}
  </dl>
</div>
