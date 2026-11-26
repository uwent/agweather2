<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/SectionHeading.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  import InfoTip from '@/lib/components/InfoTip.svelte'
  import { fieldInfo, type FieldInfoKey } from '@/lib/fieldInfo'
  import { currentUnits } from '@/lib/units'

  // A section's heading inside a long form, ruled off from what's above it as the
  // planting form's Season and Size are: an info tip, or `children` (a button), at the far end.
  let {
    label,
    id,
    level = 'h3',
    info,
    children,
  }: {
    label: string
    /** For the section's aria-labelledby */
    id: string
    /** To fit the page's outline */
    level?: 'h2' | 'h3'
    info?: FieldInfoKey
    children?: Snippet
  } = $props()

  const tip = $derived(info ? fieldInfo(info, currentUnits()) : null)
</script>

<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-line pt-4">
  <svelte:element this={level} {id} class="font-display text-sm font-semibold">{label}</svelte:element>
  {#if tip}<InfoTip text={tip.text} term={tip.term} label="About {label}" />{/if}
  {@render children?.()}
</div>
