<!-- Your sites (/sites, track 3 step 4): a card per saved site in your order, each loading its weather and risk as it
     scrolls into view, at most 3 requests at once (lib/siteQueue). The sites live in this browser (D120). -->
<script lang="ts">
  import { onDestroy, tick } from 'svelte'

  import { get } from '@/lib/api'
  import Button from '@/lib/components/Button.svelte'
  import CollapsibleSection from '@/lib/components/CollapsibleSection.svelte'
  import { downloadCsv } from '@/lib/csv'
  import { today as gridToday } from '@/lib/dates'
  import { riskSpanQuery } from '@/lib/riskSpan'
  import { createBatcher, createSiteQueue } from '@/lib/siteQueue'
  import {
    effectivePrefs,
    exportSitesCsv,
    groups,
    MAX_SITES,
    moveSite,
    removeSite,
    siteLabel,
    sites,
    sitesSnapshot,
    sitesState,
    type Site,
  } from '@/lib/sites.svelte'
  import AddSiteDialog from '@/lib/sites/AddSiteDialog.svelte'
  import { rainQuery, riskModels, topRisks, weatherByPoint, weatherQuery, type SiteWeather } from '@/lib/sites/cardData'
  import FeedPicker from '@/lib/sites/FeedPicker.svelte'
  import GroupsPanel from '@/lib/sites/GroupsPanel.svelte'
  import { groupMapUrl } from '@/lib/sites/groupMap'
  import ImportDialog from '@/lib/sites/ImportDialog.svelte'
  import { explainPrefs } from '@/lib/sites/prefs'
  import PrefsPanel from '@/lib/sites/PrefsPanel.svelte'
  import { NOT_LIVE, rainSoFarByPoint } from '@/lib/sites/rainSoFar'
  import { routes } from '@/lib/routes'
  import SiteCard from '@/lib/sites/SiteCard.svelte'
  import StorageNotice from '@/lib/sites/StorageNotice.svelte'
  import type { SitesIndexProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  let { models, crops, settings }: SitesIndexProps = $props()

  const today = $derived(gridToday())

  const queue = createSiteQueue({ limit: 3 })
  onDestroy(() => queue.cancel())

  const weather = createBatcher<SiteWeather>({
    queue,
    max: 10,
    name: 'weather',
    async fetch(keys, signal) {
      const points = keys.map((key) => sites.find((s) => s.key === key)).filter((s): s is Site => !!s)
      // Today's hours for its precipitation so far alongside; without them a card shows today's total as missing
      const [body, hours] = await Promise.all([
        get<TableResponse>('/weather/daily', weatherQuery(points, today), { signal }),
        get<TableResponse>('/weather/hourly', rainQuery(points, today), { signal }).catch(() => null),
      ])
      const found = weatherByPoint(body, points.length, today)
      const rain = hours ? rainSoFarByPoint(hours, points.length, today) : []
      return new Map(points.map((site, k) => [site.key, { ...found[k], rainToday: rain[k] ?? null }]))
    },
  })

  async function loadRisk(site: Site) {
    const prefs = effectivePrefs(site.key)
    const chosen = riskModels(prefs, models)
    if (chosen && chosen.length === 0) return { top: [], more: 0, none: 0 }
    const body = await queue.run(`risk:${site.key}`, (signal) =>
      get<TableResponse>(
        '/risk',
        { lat: site.lat, lng: site.lng, ...riskSpanQuery(today), models: chosen },
        { signal },
      ),
    )
    return topRisks(body, models, prefs.hiddenModels, 3, today)
  }

  // The group shown ('' for all); reordering works within what's shown, on the whole list's order
  let groupId = $state('')
  // A group deleted while it's shown: all sites again
  const chosenGroup = $derived(groups.find((g) => g.id === groupId))
  const shown = $derived(chosenGroup ? sites.filter((s) => chosenGroup.siteKeys.includes(s.key)) : [...sites])
  const groupsOfSite = (key: string) => groups.filter((g) => g.siteKeys.includes(key))

  let announcement = $state('')

  async function move(site: Site, to: number) {
    const neighbour = shown[to]
    if (!neighbour) return
    const up = to < shown.indexOf(site)
    moveSite(site.key, sites.indexOf(neighbour))
    announcement = `${siteLabel(site)} moved to position ${to + 1} of ${shown.length}.`
    await tick()
    // Keep the keyboard on the button just used, or the other one at the list's end
    const label = siteLabel(site)
    const buttons = [`Move ${label} ${up ? 'up' : 'down'}`, `Move ${label} ${up ? 'down' : 'up'}`]
    for (const name of buttons) {
      const button = document.querySelector<HTMLButtonElement>(`button[aria-label="${CSS.escape(name)}"]`)
      if (button && !button.disabled) {
        button.focus()
        break
      }
    }
  }

  function remove(site: Site) {
    const result = removeSite(site.key)
    if (result.ok) announcement = `${siteLabel(site)} removed.`
  }

  function exportCsv() {
    downloadCsv('agweather-sites.csv', exportSitesCsv())
  }

  let adding = $state(false)
  let importing = $state(false)
  const full = $derived(sites.length >= MAX_SITES)
</script>

<svelte:head>
  <title>Your sites · AgWeather</title>
</svelte:head>

<section class="space-y-6">
  <header class="space-y-2">
    <h1 class="text-3xl font-semibold">Your sites</h1>
    <p class="max-w-prose text-ink-muted">
      Today’s weather and crop risk at the places you follow. Your sites are saved in this browser, so they stay here
      until you remove them; export them to keep a copy or move them to another device.
    </p>
    {#if sites.length}
      <p class="max-w-prose text-sm text-ink-muted">
        {`Today’s precipitation is the total so far, through the hour shown. ${NOT_LIVE} For rain falling now, see the `}<a
          href={`${routes.map()}?overlay=radar`}
          class="underline hover:text-ink"
        >
          radar on the map
        </a>.
      </p>
    {/if}
  </header>

  <StorageNotice />

  <div class="flex flex-wrap items-center gap-3">
    {#if !sitesState.readOnly}
      <Button onclick={() => (adding = true)} disabled={full}>Add a site</Button>
      <Button variant="secondary" onclick={() => (importing = true)} disabled={full}>Import</Button>
    {/if}
    <Button variant="secondary" onclick={exportCsv} disabled={sites.length === 0}>Export CSV</Button>
    {#if groups.length}
      <div class="flex items-center gap-2 sm:ml-auto">
        <label for="group-filter" class="text-sm font-medium">Show</label>
        <select id="group-filter" class="rounded-md text-sm" bind:value={groupId}>
          <option value="">All sites ({sites.length})</option>
          {#each groups as group (group.id)}
            <option value={group.id}>{group.name} ({group.siteKeys.length})</option>
          {/each}
        </select>
        {#if chosenGroup?.siteKeys.length}
          <a
            href={groupMapUrl(
              chosenGroup,
              sites,
              explainPrefs(sitesSnapshot(), { kind: 'group', id: chosenGroup.id }).layer.value,
            )}
            class="text-sm text-brand-600 underline hover:text-brand-700"
            aria-label="Show {chosenGroup.name} on the map"
          >
            Show on the map
          </a>
        {/if}
      </div>
    {/if}
  </div>
  {#if full}
    <p class="text-sm text-ink-muted">
      You’ve saved {MAX_SITES} sites, the most AgWeather keeps. Remove one to add another.
    </p>
  {/if}

  {#if sites.length === 0}
    <div class="max-w-prose space-y-3 rounded-lg border border-dashed border-line p-6">
      <h2 class="text-lg font-semibold">No sites yet</h2>
      <p>
        A site is a place you want to follow, such as a field or a farm. Add one by searching for a town or address, or
        by entering its latitude and longitude. You can also import a list from a CSV file, such as one exported from
        the Crop Risk Tool.
      </p>
      <p>
        Each site’s card shows today’s and tomorrow’s weather and the crop disease and insect risks that are highest.
      </p>
    </div>
  {:else}
    <ul class="grid gap-4 md:grid-cols-2 lg:grid-cols-3" aria-label="Saved sites">
      {#each shown as site, index (site.key)}
        <SiteCard
          {site}
          {index}
          count={shown.length}
          groups={groupsOfSite(site.key)}
          {today}
          {loadRisk}
          loadWeather={(s) => weather.load(s.key)}
          onmove={move}
          onremove={remove}
          readOnly={sitesState.readOnly}
          prefsKey={JSON.stringify(effectivePrefs(site.key))}
        />
      {/each}
    </ul>
  {/if}

  {#if sites.length}<FeedPicker {models} />{/if}

  <CollapsibleSection title="Groups" id="groups" open={false} storageKey="sites-groups">
    <GroupsPanel {models} {crops} {settings} />
  </CollapsibleSection>

  <CollapsibleSection title="Preferences for all sites" id="preferences" open={false} storageKey="sites-prefs">
    <PrefsPanel level={{ kind: 'all' }} {models} {crops} {settings} />
  </CollapsibleSection>

  <p class="sr-only" role="status" aria-live="polite">{announcement}</p>
</section>

<AddSiteDialog bind:open={adding} />
<ImportDialog bind:open={importing} />
