<!-- The degree-day calculator (track 5 T1 b): the site page's Degree days tab for any place picked here, with an end
     date and a link to the same total on the map. Its view (the place, the settings, the start, the season, the end,
     the projection) uses the tab's names, so a Share link opens the same answer. A saved site's planting date and
     biofix are counted from and kept as on its site page. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { today as gridToday } from '@/lib/dates'
  import { routes } from '@/lib/routes'
  import DegreeDaysTab, { type DegreeDaysView } from '@/lib/sites/DegreeDaysTab.svelte'
  import { request } from '@/lib/sites/request.svelte'
  import { effectivePrefs, setPrefs, siteAt } from '@/lib/sites.svelte'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeView } from '@/lib/tools/place'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { LocateResponse } from '@/types/api'

  const today = $derived(gridToday())

  const view = viewState({
    ...PLACE_FIELDS,
    dd: field(codecs.string, ''),
    from: field(codecs.oneOf(['jan1', 'planting', 'biofix'] as const), 'jan1'),
    since: field(codecs.date, null),
    season: field(codecs.integer({ min: 2000, max: 2100 }), null),
    projection: field(codecs.boolean, false),
    end: field(codecs.date, null),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))

  // Where the place is, for the picker and for a crop's typical planting date there
  const locate = request<LocateResponse>()
  const pointKey = $derived(place ? `${place.lat},${place.lng}` : '')
  $effect(() => {
    if (!pointKey) return
    const point = untrack(() => ({ lat: place!.lat, lng: place!.lng }))
    untrack(() => locate.load((signal) => get<LocateResponse>('/locate', point, { signal })))
  })
  onDestroy(() => locate.cancel())
  const location = $derived(pointKey ? (locate.value.data?.data ?? null) : null)

  const saved = $derived(place ? siteAt(place.lat, place.lng) : undefined)
  const savedPlanting = $derived(saved ? (effectivePrefs(saved.key).planting ?? null) : null)
  const savedBiofix = $derived(saved ? (effectivePrefs(saved.key).biofix ?? null) : null)
  function saveSince(from: 'planting' | 'biofix', date: string | null) {
    if (saved) setPrefs({ kind: 'site', key: saved.key }, from === 'planting' ? { planting: date } : { biofix: date })
  }

  // The link keeps a saved site's name, so whoever opens it sees what you called it
  function shareUrl() {
    const url = new URL(view.shareUrl())
    if (saved?.name) url.searchParams.set('name', saved.name)
    return url.toString()
  }

  const ddView = $derived<DegreeDaysView>({
    dd: $view.dd,
    from: $view.from,
    since: $view.since,
    year: $view.season,
    projection: $view.projection,
    end: $view.end,
  })
  function change(changes: Partial<DegreeDaysView>) {
    const { year, ...rest } = changes
    view.patch({ ...rest, ...('year' in changes ? { season: year } : {}) })
  }
</script>

<svelte:head>
  <title>Degree-day calculator · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
    <div class="space-y-2">
      <h1 class="text-2xl font-semibold sm:text-3xl">Degree-day calculator</h1>
      <p class="max-w-prose">
        How many growing degree days has a crop or an insect had this season? Choose a place, then a crop’s or an
        insect’s usual setting or your own, and when to count from. Totals run through the forecast, or through a date
        you choose.
      </p>
      <p class="text-sm">
        <a href={routes.topic({ topic_id: 'degree-days' })} class="text-brand-600 underline hover:text-brand-700">
          About degree days and how we calculate them
        </a>
      </p>
    </div>
    {#if place}<ShareButton url={shareUrl} />{/if}
  </div>

  <PlacePicker {place} {location} onpick={(picked) => view.patch(placeView(picked))} />

  {#if place}
    <DegreeDaysTab
      lat={place.lat}
      lng={place.lng}
      {today}
      {location}
      planting={savedPlanting}
      biofix={savedBiofix}
      onsave={saved ? saveSince : undefined}
      view={ddView}
      onchange={change}
      calculator
    />
  {/if}
</div>
