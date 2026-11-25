<!-- WISP 3: app/frontend/lib/map/PlaceSearch.svelte (adapted: the danger token for its error) -->
<script lang="ts">
  import type { Map as MapLibreMap } from 'maplibre-gl'

  import { searchPlaces, type Place } from '@/lib/geocode'

  // Find a place ("Hancock WI") and move the map there. Searches only when submitted (Nominatim's
  // usage policy), preferring places in the current view.
  let { map, maxZoom = 13 }: { map: MapLibreMap | undefined; maxZoom?: number } = $props()

  let query = $state('')
  let searching = $state(false)
  let places = $state<Place[] | null>(null)
  let searchError = $state<string | null>(null)

  async function search() {
    if (!query.trim() || searching) return
    searching = true
    searchError = null
    places = null
    try {
      const view = map?.getBounds()
      const found = await searchPlaces(
        query.trim(),
        view && [view.getWest(), view.getSouth(), view.getEast(), view.getNorth()],
      )
      if (found.length === 0) searchError = 'No places found. Try adding the state, such as Hancock, WI.'
      else if (found.length === 1) goTo(found[0])
      else places = found
    } catch {
      searchError = "Place search isn't responding right now. Please try again in a moment."
    } finally {
      searching = false
    }
  }

  function goTo(place: Place) {
    places = null
    const [west, south, east, north] = place.bounds
    map?.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 40, maxZoom },
    )
  }

  /** Closes the list of places (a click elsewhere on the map) */
  export function close() {
    places = null
  }

  // The search box can sit inside a page's form: Enter searches instead of submitting it
  function onKey(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault()
      search()
    } else if (event.key === 'Escape') {
      places = null
    }
  }
</script>

<div>
  {#if places}
    <ul
      class="border-line bg-surface-raised mb-1 overflow-hidden rounded-md border text-sm shadow-lg"
      aria-label="Places found"
    >
      {#each places as place (place.label)}
        <li>
          <button type="button" class="hover:bg-brand-50 block w-full px-3 py-2 text-left" onclick={() => goTo(place)}>
            {place.label}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
  {#if searchError}
    <p class="bg-surface-raised text-danger mb-1 rounded-md px-3 py-1.5 text-xs shadow-sm">
      {searchError}
    </p>
  {/if}
  <!-- 90% opaque: the most see-through that keeps the placeholder and "Go" at 4.5:1 over any imagery -->
  <div class="border-line bg-surface-raised/90 flex overflow-hidden rounded-md border shadow-sm backdrop-blur-sm">
    <input
      type="search"
      bind:value={query}
      onkeydown={onKey}
      placeholder="Find a place, e.g. Hancock WI"
      aria-label="Find a place on the map"
      class="min-w-0 flex-1 border-0 bg-transparent px-3 py-1.5 text-sm focus:ring-0"
    />
    <button
      type="button"
      class="text-ink hover:bg-brand-50 px-3 text-sm font-medium disabled:opacity-60"
      onclick={search}
      disabled={searching}
    >
      {searching ? '…' : 'Go'}
    </button>
  </div>
</div>
