<script lang="ts" module>
  /** What `/locate` says of a clicked point (the fields the panel reads) */
  export type CellPlace = {
    county: string | null
    state: string | null
    in_box: boolean
    cell: { lat: number; lng: number } | null
    corners: [number, number][] | null
  }
</script>

<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import { routes } from '@/lib/routes'
  import { addSite, groups, setInGroup, siteAt } from '@/lib/sites.svelte'
  import SiteGroups from '@/lib/sites/SiteGroups.svelte'
  import { coordinates, placeName } from '@/lib/sites/text'

  import { modelPath, sitePath, siteModelPath } from './links'

  // The clicked cell in words (Phase 7 track 2 step 6): its value first, then where it is ("Dane County, WI ·
  // 43.07° N, 89.40° W"), and links on: the cell's chart below, the site's page, saving it as a site, and for a
  // model's map the model's page and the model at this site.
  let {
    lat,
    lng,
    value,
    title,
    when,
    place,
    placeError,
    searched = null,
    model = null,
    group = null,
    outsideTraining = false,
    onclear,
  }: {
    /** The point chosen (a click, or a place found by search) */
    lat: number
    lng: number
    /** The value as the reader sees it ("38 °F", "High"), or null while it loads */
    value: string | null
    title: string
    when: string
    place: CellPlace | null
    placeError: string | null
    /** The name of the place found by search, where the point came from one */
    searched?: string | null
    /** The map's model, for the links to its page and to it at this site */
    model?: { id: string; name: string } | null
    /** The name of the group of sites the map shows; a site saved here goes into it when it's one of yours */
    group?: string | null
    /** Whether the cell is outside the area the map's model was fitted to (D101) */
    outsideTraining?: boolean
    onclear: () => void
  } = $props()

  const where = $derived.by(() => {
    const county = placeName(place)
    const at = place?.cell
      ? `${Math.abs(place.cell.lat).toFixed(2)}° ${place.cell.lat >= 0 ? 'N' : 'S'}, ${Math.abs(place.cell.lng).toFixed(2)}° ${place.cell.lng < 0 ? 'W' : 'E'}`
      : ''
    return [county, at].filter(Boolean).join(' · ')
  })

  // The site's name: the place searched for, else its county
  const name = $derived(searched || placeName(place))
  const saved = $derived(siteAt(lat, lng))
  let status = $state('')
  $effect(() => {
    // A new point starts without the last one's message
    void [lat, lng]
    status = ''
  })

  // The map's group, when it's one of the reader's own (a shared link's group may not be)
  const ownGroup = $derived(group ? groups.find((g) => g.name.toLowerCase() === group.toLowerCase()) : undefined)
  let choosingGroups = $state(false)

  function save() {
    const result = addSite({ lat, lng, name: name ?? coordinates(lat, lng) })
    if (result.ok && ownGroup) setInGroup(ownGroup.id, result.value.key, true)
    status = result.ok ? `Saved as ${result.value.name}.` : result.message
  }

  const linkClass = 'text-brand-600 underline hover:text-brand-700'
</script>

<section
  class="rounded-md border border-line bg-surface p-3"
  aria-labelledby="cell-heading"
  data-testid="cell-panel"
  tabindex="-1"
>
  <div class="flex items-start justify-between gap-2">
    <h2 id="cell-heading" class="text-base font-semibold">The cell you chose</h2>
    <button
      type="button"
      class="rounded-md px-1.5 text-sm text-ink-muted hover:bg-brand-50 hover:text-ink"
      aria-label="Clear the cell you chose"
      onclick={onclear}
    >
      ✕
    </button>
  </div>
  <p class="mt-1 text-lg font-semibold">{value ?? 'Loading…'}</p>
  <p class="text-sm">{when ? `${title}, ${when}` : title}</p>
  {#if searched}<p class="text-sm">{searched}</p>{/if}
  {#if where}<p class="text-sm text-ink-muted">{where}</p>{/if}
  {#if placeError}<p class="text-sm text-danger-ink">{placeError}</p>{/if}
  {#if place && !place.in_box}
    <p class="mt-1 text-sm text-ink-muted">
      This place is outside the area AgWeather maps, so the map has no value here. Its site page has its weather from
      Open-Meteo.
    </p>
  {:else if outsideTraining && model}
    <p class="mt-1 text-sm" data-testid="outside-training">
      {`This place is outside the area ${model.name}'s data came from (the dashed line on the map), so its timing here is less certain.`}
    </p>
  {/if}
  <ul class="mt-2 space-y-1 text-sm">
    <li><a href="#cell-chart" class={linkClass}>See this cell's recent days and forecast</a></li>
    <li><Link href={sitePath(lat, lng, saved ? null : name)} class={linkClass}>Open this site</Link></li>
    {#if model}
      <li>
        <Link href={siteModelPath(lat, lng, model.id, saved ? null : name)} class={linkClass}>
          {model.name} at this site
        </Link>
      </li>
      <li><Link href={modelPath(model.id)} class={linkClass}>About this model</Link></li>
    {/if}
  </ul>
  <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
    {#if saved}
      <p>
        {`Saved as ${saved.name || coordinates(saved.lat, saved.lng)}. `}<Link href={routes.sites()} class={linkClass}>
          Your sites
        </Link>
      </p>
    {:else}
      <button
        type="button"
        class="rounded-md border border-line px-2.5 py-1 font-medium hover:bg-brand-50
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
        onclick={save}
      >
        {ownGroup ? `Save this site in ${ownGroup.name}` : 'Save this site'}
      </button>
    {/if}
  </div>
  {#if saved}
    <div class="mt-1 text-sm">
      <button
        type="button"
        class={linkClass}
        aria-expanded={choosingGroups}
        onclick={() => (choosingGroups = !choosingGroups)}
      >
        {`Groups${groups.some((g) => g.siteKeys.includes(saved.key)) ? ` (${groups.filter((g) => g.siteKeys.includes(saved.key)).length})` : ''}`}
      </button>
      {#if choosingGroups}
        <div class="mt-1">
          <SiteGroups siteKey={saved.key} label={saved.name || coordinates(saved.lat, saved.lng)} />
        </div>
      {/if}
    </div>
  {/if}
  <p class="text-sm" role="status">{saved ? '' : status}</p>
</section>
