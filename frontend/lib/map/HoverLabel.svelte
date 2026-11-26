<!-- WISP 3: app/frontend/lib/map/HoverLabel.svelte (copied) -->
<script lang="ts">
  import { type HoverLabelState, labelAnchor } from './hover.svelte'

  // A map's hover label, placed in the map's box (the pointer is measured from it): a setup map's
  // (MapHover.label) or the Map tab's. Pointer users only: the pages name everything for keyboards
  // and screen readers.
  let { label }: { label: HoverLabelState | null } = $props()

  // Just below the anchor: its ring is drawn 1px outside its box
  const anchor = $derived(label && labelAnchor(label.x, label.y, label.flip))
</script>

{#if label && anchor}
  <div
    class="pointer-events-none absolute z-10 w-max max-w-80 space-y-0.5 rounded-md bg-surface-raised px-2 py-1 text-xs
      text-ink shadow-md ring-1 ring-line {label.flip ? '-translate-x-full' : ''}"
    style:left="{anchor.x}px"
    style:top="{anchor.y + 2}px"
    aria-hidden="true"
  >
    {#each label.lines as line, index (index)}
      <p>{line}</p>
    {/each}
    {#if label.hint}<p class="text-ink-muted">{label.hint}</p>{/if}
  </div>
{/if}
