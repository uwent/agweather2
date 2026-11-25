<script lang="ts">
  import type { LocateData } from '@/types/api'

  import { formatHour } from '../charts/kinds'
  import ShareButton from '../components/ShareButton.svelte'
  import { addSite, siteAt } from '../sites.svelte'
  import { siteKey } from '../siteKey'
  import { coordinates, dayBasisWords, placeName, sourceWords } from './text'

  // The site page's header: the site's name (saved, else the shared link's, else "Unsaved location") with Save
  // this site, where it is (county and state, coordinates, the grid cell), whose days it uses, where its
  // weather comes from, how recent it is, and Share. location: /locate's answer, null while it loads or if it
  // failed. latest: the newest observed hour (UTC), from the page's latest-hour request.
  let {
    lat,
    lng,
    name,
    location,
    latest,
    shareUrl,
  }: {
    lat: number
    lng: number
    name: string | null
    location: LocateData | null
    latest: string | null
    shareUrl: () => string
  } = $props()

  const key = $derived(siteKey(lat, lng))
  const saved = $derived(siteAt(key))
  const title = $derived(saved?.name ?? name ?? 'Unsaved location')
  const place = $derived(placeName(location))
  let status = $state('')

  function save() {
    const result = addSite({ lat, lng, name: name ?? place ?? coordinates(lat, lng) })
    status = result.ok ? `Saved as ${result.site.name}.` : result.error
  }
</script>

<header class="space-y-2">
  <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
    <div class="min-w-0">
      <h1 class="text-2xl font-semibold wrap-break-word sm:text-3xl">{title}</h1>
      <p class="text-sm text-ink-muted">
        {place ? `${place} · ` : ''}{coordinates(lat, lng)}
      </p>
    </div>
    <div class="flex shrink-0 items-center gap-2">
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
      <ShareButton url={shareUrl} />
    </div>
  </div>
  <p class="text-sm" role="status">
    {#if status}{status}{' '}<a href="/sites" class="text-brand-600 underline hover:text-brand-700">Your sites</a>{/if}
  </p>
  <ul class="space-y-0.5 text-sm text-ink-muted">
    {#if location?.cell}
      <li>
        {`Weather for the 2.5 km grid cell centered at ${coordinates(location.cell.lat, location.cell.lng)}.`}
      </li>
    {/if}
    <li>{dayBasisWords(location)}</li>
    {#if location}<li>{sourceWords(location)}</li>{/if}
    {#if latest}
      <li>{`Observed through ${formatHour(latest, location?.timezone ?? undefined)}; forecast after that.`}</li>
    {/if}
  </ul>
</header>
