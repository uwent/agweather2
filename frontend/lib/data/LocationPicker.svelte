<!-- /data's locations (track 7 step 7.1): the reader's saved sites to tick, and any place found by name or
     coordinates (FindPlace), in one list of up to 50 (./locations.ts). -->
<script lang="ts">
  import { formatCoords } from '../siteKey'
  import { siteLabel, sites } from '../sites.svelte'
  import FindPlace from '../sites/FindPlace.svelte'
  import { MAX_POINTS } from '../sites/dataRequest'
  import { plural } from '../words'
  import { addLocation, addLocations, type Chosen } from './locations'
  import { routes } from '@/lib/routes'

  let { chosen = $bindable() }: { chosen: Chosen[] } = $props()

  const id = $props.id()
  let message = $state<string | null>(null)
  const keys = $derived(new Set(chosen.map((c) => c.key)))
  const savedKeys = $derived(new Set(sites.map((s) => s.key)))
  const found = $derived(chosen.filter((c) => !savedKeys.has(c.key)))

  function toggleSite(site: (typeof sites)[number], on: boolean) {
    if (on) {
      const added = addLocation(chosen, site)
      chosen = added.list
      message = added.message
    } else {
      chosen = chosen.filter((c) => c.key !== site.key)
      message = null
    }
  }

  function chooseAll() {
    const added = addLocations(chosen, sites)
    chosen = added.list
    message = added.message
  }

  function remove(key: string) {
    chosen = chosen.filter((c) => c.key !== key)
    message = null
  }

  const label = (c: Chosen) => c.name || formatCoords(c.lat, c.lng)
</script>

<div class="space-y-4">
  {#if sites.length}
    <fieldset class="space-y-2">
      <legend class="text-sm font-medium">Your saved sites</legend>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="cursor-pointer rounded-md border border-line bg-surface px-3 py-1 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
          onclick={chooseAll}
        >
          Choose all
        </button>
        <button
          type="button"
          class="cursor-pointer rounded-md border border-line bg-surface px-3 py-1 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
          onclick={() => {
            chosen = chosen.filter((c) => !savedKeys.has(c.key))
            message = null
          }}
        >
          Clear
        </button>
      </div>
      <div class="grid max-h-64 gap-x-4 gap-y-1 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
        {#each sites as site (site.key)}
          <label class="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              class="mt-0.5 size-4 shrink-0 accent-brand-600"
              checked={keys.has(site.key)}
              onchange={(event) => toggleSite(site, event.currentTarget.checked)}
            />
            <span>
              {siteLabel(site)}
              {#if site.name}<span class="block text-xs text-ink-muted">{formatCoords(site.lat, site.lng)}</span>{/if}
            </span>
          </label>
        {/each}
      </div>
    </fieldset>
  {:else}
    <p class="text-sm text-ink-muted">
      {'You have no saved sites in this browser. Find places below, or '}
      <a href={routes.sites()} class="underline hover:text-ink">save your sites</a>
      {' to choose them here.'}
    </p>
  {/if}

  <div class="max-w-xl">
    <FindPlace
      id="{id}-find"
      label="Add a place"
      button="Add"
      onpick={(place) => {
        const added = addLocation(chosen, place)
        chosen = added.list
        message = added.message
      }}
    />
  </div>

  {#if found.length}
    <div class="space-y-1">
      <p class="text-sm font-medium">Places you added</p>
      <ul class="flex flex-wrap gap-2">
        {#each found as place (place.key)}
          <li class="flex items-center gap-1 rounded-full border border-line bg-surface-raised py-0.5 pr-1 pl-3 text-sm">
            {label(place)}
            <button
              type="button"
              class="cursor-pointer rounded-full px-1.5 text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600"
              aria-label={`Remove ${label(place)}`}
              onclick={() => remove(place.key)}
            >
              ×
            </button>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <p class="text-sm" role="status">
    {chosen.length === 0
      ? 'No locations chosen yet.'
      : `${plural(chosen.length, 'location')} chosen, of up to ${MAX_POINTS}.`}
    {#if message}<span class="text-danger-ink">{` ${message}`}</span>{/if}
  </p>
</div>
