<!-- WISP 3: app/frontend/lib/map/BasemapToggle.svelte (copied) -->
<script lang="ts">
  import { BASEMAPS, type Basemap } from './basemaps'

  // Satellite / Map, for the system picker and the map page
  let { value, onchange }: { value: Basemap; onchange: (basemap: Basemap) => void } = $props()
</script>

<div
  class="border-line bg-surface-raised flex overflow-hidden rounded-md border text-xs shadow-sm"
  role="group"
  aria-label="Basemap"
>
  {#each BASEMAPS as { key, name } (key)}
    <button
      type="button"
      class="px-2.5 py-1.5 {value === key ? 'bg-brand-600 dark:text-surface text-white' : 'hover:bg-surface'}"
      aria-pressed={value === key}
      onclick={() => value !== key && onchange(key)}
    >
      {name}
    </button>
  {/each}
</div>
