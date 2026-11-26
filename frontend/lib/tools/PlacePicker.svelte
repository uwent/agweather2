<!-- The place a tool answers for (track 5; reused by the climate pages): the place now with where it is
     (/locate's county and state, and whether we cover it), Save this site and a link to its site page; your saved
     sites as buttons; and a search by name or coordinates (FindPlace). The page keeps the place in its view
     (./place.ts) and passes /locate's answer as `location` when it loads it anyway; without `location`, the picker
     asks /locate itself. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { LocateResponse, LocateData } from '@/types/api'

  import { get } from '../api'
  import { type PickedPlace } from '../siteKey'
  import { addSite, siteAt, siteLabel, sites } from '../sites.svelte'
  import FindPlace from '../sites/FindPlace.svelte'
  import { request } from '../sites/request.svelte'
  import { placeLine, placeSitePath, placeTitle, type Place } from './place'

  let {
    place,
    onpick,
    location = undefined,
    id = 'place',
    label = 'Choose a place',
  }: {
    place: Place | null
    onpick: (place: Place) => void
    /** /locate's answer for the place (null while it loads or if it failed); left out, the picker asks for it */
    location?: LocateData | null
    /** Prefix for the picker's element ids, where a page has two */
    id?: string
    /** The search's label */
    label?: string
  } = $props()

  // /locate, when the page doesn't pass it
  const own = request<LocateResponse>()
  const pointKey = $derived(place ? `${place.lat},${place.lng}` : '')
  $effect(() => {
    if (location !== undefined || !pointKey) return
    const point = untrack(() => ({ lat: place!.lat, lng: place!.lng }))
    untrack(() => own.load((signal) => get<LocateResponse>('/locate', point, { signal })))
  })
  onDestroy(() => own.cancel())
  const where = $derived(location !== undefined ? location : pointKey ? (own.value.data?.data ?? null) : null)

  const saved = $derived(place ? siteAt(place.lat, place.lng) : undefined)
  const title = $derived(place ? placeTitle(place, saved, where) : '')
  let searching = $state(false)
  let status = $state('')

  function pick(found: PickedPlace | Place) {
    searching = false
    status = ''
    onpick({ lat: found.lat, lng: found.lng, name: found.name || null })
  }

  function save() {
    if (!place) return
    const result = addSite({ lat: place.lat, lng: place.lng, name: title })
    status = result.ok ? `Saved as ${result.value.name}.` : result.message
  }

  const chip =
    'cursor-pointer rounded-full border px-3 py-0.5 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600'
</script>

<section class="space-y-3 rounded-lg border border-line bg-surface-raised p-4" aria-labelledby="{id}-heading">
  <h2 id="{id}-heading" class="sr-only">Place</h2>
  {#if place}
    <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div class="min-w-0">
        <p class="text-lg font-semibold wrap-break-word">{title}</p>
        <p class="text-sm text-ink-muted">{placeLine(place, where)}</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        {#if !saved}
          <button
            type="button"
            class="rounded-md bg-brand-600 px-3 py-1 text-sm font-semibold text-surface hover:bg-brand-700
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
            onclick={save}
          >
            Save this site
          </button>
        {/if}
        <a
          href={placeSitePath({ ...place, name: saved ? null : place.name })}
          class="text-sm text-brand-600 underline hover:text-brand-700"
        >
          Open the site page
        </a>
        <button
          type="button"
          class="rounded-md border border-line px-3 py-1 text-sm font-medium hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          aria-expanded={searching}
          aria-controls="{id}-search"
          onclick={() => (searching = !searching)}
        >
          Change place
        </button>
      </div>
    </div>
    <p class="text-sm" role="status">
      {#if status}{status}{' '}<a href="/sites" class="text-brand-600 underline hover:text-brand-700">
          Your sites
        </a>{/if}
    </p>
  {:else}
    <p class="text-sm text-ink-muted">
      Search for a town or address, enter coordinates, or choose one of your saved sites.
    </p>
  {/if}

  {#if !place || searching}
    <div id="{id}-search">
      <FindPlace id="{id}-find" {label} onpick={pick} />
    </div>
  {/if}
  {#if sites.length}
    <div class="space-y-1">
      <p id="{id}-saved" class="text-sm font-medium">Your sites</p>
      <ul class="flex flex-wrap gap-2" aria-labelledby="{id}-saved">
        {#each sites as site (site.key)}
          {@const current = saved?.key === site.key}
          <li>
            <button
              type="button"
              class="{chip} {current ? 'border-brand-600 bg-brand-50 font-medium' : 'border-line bg-surface'}"
              aria-pressed={current}
              onclick={() => pick({ lat: site.lat, lng: site.lng, name: null })}
            >
              {siteLabel(site)}
            </button>
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</section>
