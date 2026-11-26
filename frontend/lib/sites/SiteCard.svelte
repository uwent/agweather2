<!-- A saved site's card on /sites: its name (a link to the site page), today's and tomorrow's weather, and its top
     three risks today in words and color. It loads when it scrolls into view, through the page's request queue. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { ApiError, isAbort } from '@/lib/api'
  import { formatHour } from '@/lib/charts/kinds'
  import { formatDate } from '@/lib/dates'
  import { riskColor } from '@/lib/riskLevels'
  import { siteLabel, type Group, type Site } from '@/lib/sites.svelte'
  import RiskStrip from '@/lib/components/RiskStrip.svelte'
  import { trendWords } from '@/lib/riskSpan'
  import { formatCoords, siteModelUrl, siteUrl } from '@/lib/siteKey'
  import { currentUnits } from '@/lib/units'

  import { WEATHER_UNITS, type DayWeather, type RiskSummary, type SiteWeather } from './cardData'
  import { missingWords, NOT_LIVE, rainSoFarShort } from './rainSoFar'
  import SiteGroups from './SiteGroups.svelte'

  let {
    site,
    index,
    count,
    groups = [],
    today,
    loadRisk,
    loadWeather,
    onmove,
    onremove,
    readOnly = false,
    prefsKey = '',
  }: {
    site: Site
    index: number
    count: number
    groups?: Group[]
    today: string
    loadRisk: (site: Site) => Promise<RiskSummary>
    loadWeather: (site: Site) => Promise<SiteWeather | undefined>
    onmove: (site: Site, to: number) => void
    onremove: (site: Site) => void
    readOnly?: boolean
    /** The site's preferences as text: when they change (a crop chosen, a model hidden), its risks load again */
    prefsKey?: string
  } = $props()

  let choosingGroups = $state(false)

  const units = $derived(currentUnits())
  const label = $derived(siteLabel(site))

  type Loading<T> = { state: 'idle' | 'loading' } | { state: 'done'; value: T } | { state: 'failed'; error: ApiError }
  let risk = $state<Loading<RiskSummary>>({ state: 'idle' })
  let weather = $state<Loading<SiteWeather | undefined>>({ state: 'idle' })
  let wait = $state(0) // seconds until "Try again" (a 429 or 503's Retry-After)
  let timer: ReturnType<typeof setInterval> | undefined

  function failure(error: unknown): ApiError {
    return error instanceof ApiError
      ? error
      : new ApiError({ status: 0, errors: [{ code: 'error', param: null, message: String(error) }] })
  }

  async function load() {
    risk = { state: 'loading' }
    weather = { state: 'loading' }
    const failed = (error: unknown, set: (value: { state: 'failed'; error: ApiError }) => void) => {
      if (isAbort(error)) return
      const found = failure(error)
      set({ state: 'failed', error: found })
      if (found.retryAfter && found.retryAfter > wait) countdown(found.retryAfter)
    }
    await Promise.all([
      loadRisk(site).then(
        (value) => (risk = { state: 'done', value }),
        (error) => failed(error, (v) => (risk = v)),
      ),
      loadWeather(site).then(
        (value) => (weather = { state: 'done', value }),
        (error) => failed(error, (v) => (weather = v)),
      ),
    ])
  }

  function countdown(seconds: number) {
    clearInterval(timer)
    wait = seconds
    timer = setInterval(() => {
      wait = Math.max(0, wait - 1)
      if (wait === 0) clearInterval(timer)
    }, 1000)
  }
  onDestroy(() => clearInterval(timer))

  // Load once the card is (nearly) in view; without IntersectionObserver (tests, old browsers) at once
  let card = $state<HTMLElement>()
  let seen = $state(false)
  $effect(() => {
    if (!card || seen) return
    if (typeof IntersectionObserver === 'undefined') {
      seen = true
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          seen = true
          observer.disconnect()
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(card)
    return () => observer.disconnect()
  })
  // Once: load() writes the state this would otherwise track
  $effect(() => {
    if (seen) untrack(() => risk.state === 'idle' && load())
  })

  // The risks again when the site's preferences change, once they've loaded
  let loadedFor: string | null = null
  $effect(() => {
    const key = prefsKey
    if (!seen) return
    untrack(() => {
      if (loadedFor !== null && key !== loadedFor) reloadRisk()
      if (seen) loadedFor = key
    })
  })

  async function reloadRisk() {
    risk = { state: 'loading' }
    try {
      risk = { state: 'done', value: await loadRisk(site) }
    } catch (error) {
      if (!isAbort(error)) risk = { state: 'failed', error: failure(error) }
    }
  }

  const failedError = $derived(risk.state === 'failed' ? risk.error : weather.state === 'failed' ? weather.error : null)

  let confirming = $state(false)

  const temp = (value: number | null) => units.format(WEATHER_UNITS.air_temperature_max, value)
  const precip = (day: DayWeather) => units.format(WEATHER_UNITS.precipitation_sum, day.precipitation)
</script>

<li
  bind:this={card}
  class="flex min-w-0 flex-col gap-3 rounded-lg border border-line bg-surface-raised p-4 shadow-sm"
  aria-labelledby="site-{site.key}"
>
  <div class="flex items-start justify-between gap-2">
    <div class="min-w-0">
      <h2 id="site-{site.key}" class="truncate text-lg font-semibold">
        <a href={siteUrl(site.key)} class="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">
          {label}
        </a>
      </h2>
      <p class="text-xs text-ink-muted">
        {site.name ? formatCoords(site.lat, site.lng) : ''}{site.name && groups.length ? ' · ' : ''}{groups
          .map((g) => g.name)
          .join(', ')}
      </p>
    </div>
    {#if !readOnly}
      <div class="flex shrink-0 gap-1">
        <button
          type="button"
          class="inline-flex size-8 items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink disabled:opacity-40"
          aria-label="Move {label} up"
          title="Move up"
          disabled={index === 0}
          onclick={() => onmove(site, index - 1)}
        >
          <span aria-hidden="true">↑</span>
        </button>
        <button
          type="button"
          class="inline-flex size-8 items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink disabled:opacity-40"
          aria-label="Move {label} down"
          title="Move down"
          disabled={index === count - 1}
          onclick={() => onmove(site, index + 1)}
        >
          <span aria-hidden="true">↓</span>
        </button>
      </div>
    {/if}
  </div>

  <!-- Today and tomorrow -->
  {#if weather.state === 'done' && weather.value}
    <dl class="grid grid-cols-2 gap-2 text-sm">
      {#each [{ title: 'Today', day: weather.value.today }, { title: 'Tomorrow', day: weather.value.tomorrow }] as item (item.title)}
        <div class="rounded-md bg-surface px-3 py-2">
          <dt class="text-xs text-ink-muted">
            {item.title}{item.day?.kind === 'forecast' ? ' (forecast)' : ''}
          </dt>
          <dd>
            {#if item.day}
              <span class="sr-only">High and low:</span>
              <span class="font-medium">{temp(item.day.high)} / {temp(item.day.low)}</span>
              {#if item.title === 'Today' && item.day.precipitation === null && weather.value.rainToday}
                {@const rain = weather.value.rainToday}
                <span class="block text-xs text-ink-muted" title={NOT_LIVE}>
                  {`Precipitation ${rainSoFarShort(rain, units)}, through ${formatHour(rain.through, rain.timeZone)}${missingWords(rain)}`}<span
                    class="sr-only"
                  >
                    {`. ${NOT_LIVE}`}
                  </span>
                </span>
              {:else}
                <span class="block text-xs text-ink-muted">Precipitation {precip(item.day)}</span>
              {/if}
            {:else}
              <span class="text-ink-muted">No data</span>
            {/if}
          </dd>
        </div>
      {/each}
    </dl>
  {:else if weather.state !== 'failed'}
    <div class="grid h-15 grid-cols-2 gap-2" aria-hidden="true">
      <div class="animate-pulse rounded-md bg-surface"></div>
      <div class="animate-pulse rounded-md bg-surface"></div>
    </div>
  {/if}

  <!-- Risk today -->
  <div class="min-h-20 text-sm">
    <h3 class="mb-1 text-xs font-medium text-ink-muted">Risk today, {formatDate(today)}</h3>
    {#if risk.state === 'done'}
      {#if risk.value.top.length}
        <ul class="space-y-1">
          {#each risk.value.top as row (row.model)}
            <li>
              <div class="flex items-center gap-2">
                <span
                  class="size-3 shrink-0 rounded-full border border-line"
                  style:background-color={riskColor(row.level, row.levels)}
                  aria-hidden="true"
                ></span>
                <a href={siteModelUrl(site.key, row.model)} class="min-w-0 truncate text-ink hover:underline">
                  {row.name}
                </a>
                <span class="ml-auto shrink-0 font-medium">{row.label}</span>
              </div>
              {#if row.days && row.days.length > 1}
                <RiskStrip
                  class="mt-0.5 w-full pl-5"
                  days={row.days}
                  levels={row.levels}
                  {today}
                  label={`${row.name}: ${trendWords({ model: row.model, name: row.name, days: row.days }, today)}.`}
                />
              {/if}
            </li>
          {/each}
        </ul>
        {#if risk.value.more}
          <p class="mt-1 text-xs text-ink-muted">
            {risk.value.more === 1 ? '1 more model' : `${risk.value.more} more models`} at the same or lower risk.
          </p>
        {/if}
      {:else}
        <p class="text-ink-muted">No models are in season here today.</p>
      {/if}
      {#if risk.value.top.some((row) => row.days && row.days.length > 1)}
        <p class="mt-1 text-xs text-ink-muted">Each strip runs from two weeks ago through the forecast (shaded).</p>
      {/if}
    {:else if risk.state !== 'failed'}
      <div class="space-y-1" aria-hidden="true">
        {#each [0, 1, 2] as k (k)}
          <div class="h-4 animate-pulse rounded-sm bg-surface"></div>
        {/each}
      </div>
    {/if}
  </div>

  {#if failedError}
    <div class="space-y-2 rounded-md border border-line bg-surface p-3 text-sm" role="alert">
      <p>{failedError.message}</p>
      {#if failedError.retryable}
        <button
          type="button"
          class="rounded-md border border-line bg-surface-raised px-3 py-1 font-medium hover:bg-brand-50 disabled:opacity-60"
          disabled={wait > 0}
          onclick={load}
        >
          {wait > 0 ? `Try again in ${wait} s` : 'Try again'}
        </button>
      {/if}
    </div>
  {/if}

  <div class="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line pt-2 text-sm">
    <a
      href={siteUrl(site.key)}
      class="font-medium text-brand-600 underline hover:text-brand-700"
      aria-label="Weather and models for {label}"
    >
      Weather and models
    </a>
    {#if !readOnly}
      <button
        type="button"
        class="text-ink-muted underline hover:text-ink"
        aria-label="Groups for {label}"
        aria-expanded={choosingGroups}
        onclick={() => (choosingGroups = !choosingGroups)}
      >
        Groups
      </button>
    {/if}
    <a
      href="{siteUrl(site.key)}#preferences"
      class="text-ink-muted underline hover:text-ink"
      aria-label="Preferences for {label}"
    >
      Preferences
    </a>
    {#if !readOnly}
      {#if confirming}
        <span class="ml-auto flex items-center gap-2">
          <span>Remove this site?</span>
          <button
            type="button"
            class="font-medium text-danger-ink underline"
            aria-label="Remove {label}"
            onclick={() => onremove(site)}
          >
            Remove
          </button>
          <button type="button" class="underline" onclick={() => (confirming = false)}>Keep</button>
        </span>
      {:else}
        <button
          type="button"
          class="ml-auto text-ink-muted underline hover:text-ink"
          aria-label="Remove {label}"
          onclick={() => (confirming = true)}
        >
          Remove
        </button>
      {/if}
    {/if}
  </div>
  {#if choosingGroups}
    <SiteGroups siteKey={site.key} {label} />
  {/if}
</li>
