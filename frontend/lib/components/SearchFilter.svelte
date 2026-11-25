<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/SearchFilter.svelte -->
<script lang="ts">
  import { searchHighlight } from '@/lib/searchHighlight'

  // A search box over a list (sites, models), marking what it matched on the page
  // (lib/searchHighlight.ts). As tall as the selects beside it; compact in a sidebar.
  let {
    value = $bindable(''),
    placeholder = 'Search',
    label = 'Search',
    compact = false,
    class: className = '',
  }: { value?: string; placeholder?: string; label?: string; compact?: boolean; class?: string } = $props()
</script>

<input
  type="search"
  bind:value
  {placeholder}
  aria-label={label}
  {@attach searchHighlight(() => value)}
  class="block rounded-md text-sm {compact ? 'py-1' : ''} {className}"
/>
