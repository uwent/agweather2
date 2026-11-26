<script lang="ts">
  import type { LocateData } from '@/types/api'

  import { formatHour } from '../charts/kinds'
  import ShareButton from '../components/ShareButton.svelte'
  import type { ModelSettings } from '@/types'

  import { addSite, groups, siteAt } from '../sites.svelte'
  import PrefsPanel from './PrefsPanel.svelte'
  import SiteGroups from './SiteGroups.svelte'
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
    models = [],
    crops = [],
    settings = [],
  }: {
    lat: number
    lng: number
    name: string | null
    location: LocateData | null
    latest: string | null
    shareUrl: () => string
    /** For the preferences panel (a saved site's): the models and crops it can show, and the models' settings */
    models?: readonly { id: string; name: string; crops: string[] }[]
    crops?: readonly { id: string; name: string }[]
    settings?: readonly ModelSettings[]
  } = $props()

  const saved = $derived(siteAt(lat, lng))
  const title = $derived(saved?.name ?? name ?? 'Unsaved location')
  const place = $derived(placeName(location))
  let status = $state('')

  // A saved site's groups and preferences, under the header; `#preferences` (a card's link) opens the preferences
  let panel = $state<'groups' | 'prefs' | null>(
    typeof window !== 'undefined' && window.location.hash === '#preferences' ? 'prefs' : null,
  )
  const siteGroups = $derived(saved ? groups.filter((g) => g.siteKeys.includes(saved.key)) : [])
  const toggle = (which: 'groups' | 'prefs') => (panel = panel === which ? null : which)
  const tool =
    'rounded-md border border-line px-3 py-1 text-sm font-medium hover:bg-brand-50 aria-expanded:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600'

  function save() {
    const result = addSite({ lat, lng, name: name ?? place ?? coordinates(lat, lng) })
    status = result.ok ? `Saved as ${result.value.name}.` : result.message
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
      {:else}
        <button
          type="button"
          class={tool}
          aria-expanded={panel === 'groups'}
          aria-controls="site-groups"
          onclick={() => toggle('groups')}
        >
          {`Groups${siteGroups.length ? ` (${siteGroups.length})` : ''}`}
        </button>
        <button
          type="button"
          class={tool}
          aria-expanded={panel === 'prefs'}
          aria-controls="preferences"
          onclick={() => toggle('prefs')}
        >
          Preferences
        </button>
      {/if}
      <ShareButton url={shareUrl} />
    </div>
  </div>
  <p class="text-sm" role="status">
    {#if status}{status}{' '}<a href="/sites" class="text-brand-600 underline hover:text-brand-700">Your sites</a>{/if}
  </p>
  <ul class="space-y-0.5 text-sm text-ink-muted">
    {#if location?.in_box && location.cell}
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
  {#if saved && panel === 'groups'}
    <section
      id="site-groups"
      class="rounded-md border border-line bg-surface-raised p-3"
      aria-labelledby="site-groups-h"
    >
      <h2 id="site-groups-h" class="mb-2 text-base font-semibold">Groups</h2>
      <SiteGroups siteKey={saved.key} label={saved.name || coordinates(lat, lng)} />
      <p class="mt-2 text-sm">
        <a href="/sites#groups" class="text-brand-600 underline hover:text-brand-700">Manage your groups</a>
      </p>
    </section>
  {/if}
  {#if saved && panel === 'prefs'}
    <section id="preferences" class="rounded-md border border-line bg-surface-raised p-3" aria-labelledby="prefs-h">
      <h2 id="prefs-h" class="mb-2 text-base font-semibold">Preferences for this site</h2>
      <PrefsPanel level={{ kind: 'site', key: saved.key }} {models} {crops} {settings} />
    </section>
  {/if}
</header>
