<!-- Find a place by name or coordinates, for the home page and adding a site. Typed coordinates ("43.07, -89.40")
     are taken as they are; a name is searched with Nominatim only when submitted (its usage policy forbids
     search-as-you-type), as WISP 3's PlaceSearch does on its map. -->
<script lang="ts">
  import { searchPlaces, type Place } from '@/lib/geocode'
  import { parseSiteKey, type PickedPlace } from '@/lib/siteKey'

  let {
    onpick,
    label = 'Find a place',
    placeholder = 'A town, address or coordinates',
    id = 'find-place',
    button = 'Go',
  }: {
    onpick: (place: PickedPlace) => void
    label?: string
    placeholder?: string
    id?: string
    button?: string
  } = $props()

  let query = $state('')
  let searching = $state(false)
  let places = $state<Place[] | null>(null)
  let message = $state<string | null>(null)

  /** "Hancock, Waushara County, Wisconsin" → "Hancock" for a site's name */
  const shortName = (label: string) => label.split(',')[0].trim()

  async function search() {
    const text = query.trim()
    if (!text || searching) return
    message = null
    places = null
    const coords = parseSiteKey(text)
    if (coords) {
      onpick({ ...coords, name: '' })
      return
    }
    if (/^-?\d/.test(text)) {
      message =
        'Enter coordinates as latitude and longitude in decimal degrees, such as 43.07, -89.40 (west longitudes are negative).'
      return
    }
    searching = true
    try {
      const found = await searchPlaces(text)
      if (found.length === 0) message = "No places found. Try adding the state, such as 'Hancock, WI'."
      else if (found.length === 1) pick(found[0])
      else places = found
    } catch {
      message = 'Place search isn’t responding right now. Please try again in a moment, or enter coordinates.'
    } finally {
      searching = false
    }
  }

  function pick(place: Place) {
    places = null
    const [lng, lat] = place.center
    onpick({ lat, lng, name: shortName(place.label) })
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault()
      search()
    } else if (event.key === 'Escape') {
      places = null
    }
  }
</script>

<div class="space-y-2">
  <label for={id} class="block text-sm font-medium">{label}</label>
  <div class="flex max-w-xl overflow-hidden rounded-md border border-line bg-surface-raised shadow-sm">
    <input
      {id}
      type="search"
      bind:value={query}
      onkeydown={onKey}
      {placeholder}
      aria-describedby={message ? `${id}-message` : undefined}
      class="min-w-0 flex-1 border-0 bg-transparent px-3 py-2 text-sm focus:ring-0 focus-visible:outline-2
        focus-visible:-outline-offset-2 focus-visible:outline-brand-600"
    />
    <button
      type="button"
      class="px-4 text-sm font-medium text-ink hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2
        focus-visible:outline-brand-600 disabled:opacity-60"
      onclick={search}
      disabled={searching}
    >
      {searching ? 'Searching…' : button}
    </button>
  </div>
  {#if message}
    <p id="{id}-message" class="text-sm text-danger-ink" role="alert">{message}</p>
  {/if}
  {#if places}
    <ul
      class="max-w-xl overflow-hidden rounded-md border border-line bg-surface-raised text-sm"
      aria-label="Places found"
    >
      {#each places as place (place.label)}
        <li>
          <button
            type="button"
            class="block w-full px-3 py-2 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2
              focus-visible:outline-brand-600"
            onclick={() => pick(place)}
          >
            {place.label}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
