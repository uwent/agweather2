<!-- STAND-IN, TO BE REPLACED (w7-oakwilt, 2026-11-26): w7-tools is building the shared `lib/tools/PlacePicker.svelte`
     (FindPlace, saved sites as chips, the /locate line, Save this site, open the site page). This is the least of it,
     with the same props, so the oak wilt page codes against that interface; when PlacePicker merges, import it in
     pages/Tools/OakWilt.svelte in place of this file and delete this one. -->
<script lang="ts">
  import { routes } from '@/lib/routes'
  import FindPlace from '@/lib/sites/FindPlace.svelte'
  import { coordinates } from '@/lib/sites/text'

  import type { Place } from './placeStandIn'

  let {
    place,
    onpick,
  }: {
    place: Place | null
    onpick: (place: Place) => void
    /** The place's `/locate` answer, when the page has it (unused here) */
    location?: unknown
  } = $props()

  const siteHref = $derived.by(() => {
    if (!place) return null
    const url = routes.site({ lat: String(place.lat), lng: String(place.lng) })
    return place.name ? `${url}?name=${encodeURIComponent(place.name)}` : url
  })
</script>

<div class="space-y-2">
  <FindPlace
    onpick={(p) => onpick({ ...p, name: p.name || null })}
    id="tool-place"
    label="Choose a location"
    button="Go"
  />
  {#if place}
    <p class="text-sm">
      <span class="font-medium">{place.name || coordinates(place.lat, place.lng)}</span>
      {#if place.name}<span class="text-ink-muted">{` · ${coordinates(place.lat, place.lng)}`}</span>{/if}
      {#if siteHref}
        <span class="text-ink-muted">{' · '}</span>
        <a href={siteHref} class="text-brand-600 underline hover:text-brand-700">Open the site page</a>
      {/if}
    </p>
  {/if}
</div>
