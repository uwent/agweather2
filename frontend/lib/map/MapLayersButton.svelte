<!-- WISP 3: app/frontend/lib/map/MapLayersButton.svelte (copied) -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  import type { Basemap } from './basemaps'
  import { roads, setRoads } from './roads.svelte'

  // Every map's Layers button and panel, beside the Satellite | Map pill: what the map adds
  // (children: the soil types, the Map tab's data overlays and shapes), then under Basemap the roads
  // and place names over the satellite imagery (while it's shown). Nothing to show (the street map,
  // no layers of its own): no button.
  // A panel that follows its button in the tab order; Escape or × closes it and goes back there.
  let {
    id,
    basemap,
    count = 0,
    children,
  }: {
    /** Unique on the page */
    id: string
    basemap: Basemap
    /** The layers switched on, counted on the button */
    count?: number
    children?: Snippet
  } = $props()

  let open = $state(false)
  let button: HTMLButtonElement | undefined = $state()

  function close() {
    open = false
    button?.focus()
  }
</script>

{#if basemap === 'imagery' || children}
  <div class="relative">
    <button
      type="button"
      class="border-line bg-surface-raised hover:bg-surface flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs
      shadow-sm {open ? 'ring-brand-500 ring-2' : ''}"
      bind:this={button}
      aria-expanded={open}
      aria-controls={id}
      onclick={() => (open = !open)}
    >
      <svg
        viewBox="0 0 24 24"
        class="size-4"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" />
      </svg>
      Layers{#if count}<span class="bg-brand-600 dark:text-surface rounded-full px-1.5 text-white">{count}</span>{/if}
    </button>
    {#if open}
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions (Escape from any control inside) -->
      <div
        {id}
        class="border-line bg-surface-raised absolute top-full left-0 z-20 mt-1 max-h-[min(70vh,32rem)] w-72 space-y-4 overflow-y-auto
        rounded-md border p-3 text-sm shadow-lg"
        role="group"
        aria-label="Map layers"
        onkeydown={(event) => {
          if (event.key !== 'Escape') return
          event.stopPropagation()
          close()
        }}
      >
        <div class="flex items-center justify-between">
          <h2 class="font-medium">Map layers</h2>
          <button
            type="button"
            class="text-ink-muted hover:text-ink rounded-sm px-1.5 text-lg leading-none"
            aria-label="Close map layers"
            onclick={close}
          >
            ×
          </button>
        </div>
        {@render children?.()}
        {#if basemap === 'imagery'}
          <fieldset>
            <legend class="text-ink-muted mb-1 text-xs font-medium tracking-wide uppercase">Basemap</legend>
            <label class="flex items-start gap-2">
              <input
                type="checkbox"
                class="mt-1"
                checked={roads.on}
                onchange={(event) => setRoads(event.currentTarget.checked)}
              />
              <span>
                Roads and place names
                <span class="text-ink-muted block text-xs">Over the satellite imagery, from OpenStreetMap</span>
              </span>
            </label>
          </fieldset>
        {/if}
      </div>
    {/if}
  </div>
{/if}
