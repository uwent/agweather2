<script lang="ts">
  import { Tabs } from 'bits-ui'
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import { addDays, today as gridToday } from '@/lib/dates'
  import { riskSpanQuery } from '@/lib/riskSpan'
  import { DEFAULT_NORMAL_VARIABLE, NORMAL_VARIABLE_IDS } from '@/lib/climate/Normals.svelte'
  import { DEFAULT_PERIOD, NORMAL_PERIODS } from '@/lib/climate/periods'
  import { request } from '@/lib/request.svelte'
  import ClimateTab, { type ClimateView } from '@/lib/sites/ClimateTab.svelte'
  import DataTab, { type DataView } from '@/lib/sites/DataTab.svelte'
  import DegreeDaysTab, { type DegreeDaysView } from '@/lib/sites/DegreeDaysTab.svelte'
  import ModelsTab from '@/lib/sites/ModelsTab.svelte'
  import Overview from '@/lib/sites/Overview.svelte'
  import { rainSoFarByPoint } from '@/lib/sites/rainSoFar'
  import SiteHeader from '@/lib/sites/SiteHeader.svelte'
  import WeatherTab, { type WeatherView } from '@/lib/sites/WeatherTab.svelte'
  import { effectivePrefs, setPrefs, siteAt } from '@/lib/sites.svelte'
  import { tableRows } from '@/lib/tableRows'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { SiteProps } from '@/types'
  import type { LocateResponse, TableResponse } from '@/types/api'

  // A site's page (F1): any point by its coordinates, saved or not. The header says where it is and whose days
  // it uses; the tabs show today and the forecast with the risk now (Overview) and the weather as charts
  // (Weather). Its content (the point, a shared link's name, the models' catalog) comes as props; its numbers
  // from the API (D117). The tab and the Weather tab's settings are the page's view, kept per browser tab and
  // given in full by Share (D118).
  let { lat, lng, name, models, crops, settings }: SiteProps = $props()

  const today = $derived(gridToday())

  const TAB_IDS = ['overview', 'weather', 'models', 'degree-days', 'climate', 'data'] as const
  type Tab = (typeof TAB_IDS)[number]

  const view = viewState({
    tab: field(codecs.oneOf(TAB_IDS), 'overview'),
    step: field(codecs.oneOf(['daily', 'hourly'] as const), 'daily'),
    range: field(codecs.oneOf(['week', 'month', 'season', 'custom'] as const), 'month'),
    dates: field(codecs.dateRange, null),
    roll: field(codecs.integer({ min: 2, max: 365 }), null),
    forecast: field(codecs.boolean, true),
    // The Degree days tab
    dd: field(codecs.string, ''),
    from: field(codecs.oneOf(['jan1', 'planting', 'biofix'] as const), 'jan1'),
    since: field(codecs.date, null),
    season: field(codecs.integer({ min: 2000, max: 2100 }), null),
    projection: field(codecs.boolean, false),
    // The Climate tab
    cperiod: field(codecs.oneOf(NORMAL_PERIODS), DEFAULT_PERIOD),
    cdd: field(codecs.string, ''),
    cstart: field(codecs.date, null),
    cyear: field(codecs.integer({ min: 2000, max: 2100 }), null),
    cmonth: field(codecs.integer({ min: 1, max: 12 }), null),
    cvar: field(codecs.oneOf(NORMAL_VARIABLE_IDS), DEFAULT_NORMAL_VARIABLE),
    // The Data tab
    get: field(codecs.oneOf(['daily', 'hourly', 'totals', 'degree-days', 'model'] as const), 'daily'),
  })
  onDestroy(() => view.destroy())

  // The link keeps the site's name, so whoever opens it sees what you called it
  const saved = $derived(siteAt(lat, lng))
  function shareUrl() {
    const url = new URL(view.shareUrl())
    const label = saved?.name ?? name
    if (label) url.searchParams.set('name', label)
    return url.toString()
  }

  const locate = request<LocateResponse>()
  // Every model's risk from two weeks back through the forecast: Overview's "Risk now" and the Models tab
  const risk = request<TableResponse>()
  const loadRisk = () =>
    untrack(() => risk.load((signal) => get<TableResponse>('/risk', { lat, lng, ...riskSpanQuery(today) }, { signal })))
  const latestHours = request<TableResponse>()
  // Inertia hands the page its props again after it mounts: the point as text, so equal props don't refetch
  const pointKey = $derived(`${lat},${lng},${today}`)
  $effect(() => {
    void pointKey
    const point = untrack(() => ({ lat, lng }))
    untrack(() => {
      locate.load((signal) => get<LocateResponse>('/locate', point, { signal }))
      latestHours.load((signal) =>
        get<TableResponse>(
          '/weather/hourly',
          {
            ...point,
            start: addDays(today, -1),
            forecast: false,
            vars: ['air_temperature', 'dew_point', 'relative_humidity', 'wind_speed', 'precipitation'],
            units: 'metric',
          },
          { signal },
        ),
      )
    })
  })
  onDestroy(() => [locate, latestHours, risk].forEach((r) => r.cancel()))
  // The risk once a tab that shows it opens (not for the Weather tab alone), again when the point or day changes
  let riskFor = ''
  $effect(() => {
    if (!['overview', 'models'].includes($view.tab) || riskFor === pointKey) return
    riskFor = pointKey
    loadRisk()
  })

  const location = $derived(locate.value.data?.data ?? null)
  // The newest observed hour with a temperature
  const latest = $derived.by(() => {
    const body = latestHours.value.data
    if (!body) return null
    const table = tableRows(body)
    const day = table.days.findLast((row) => row.kind === 'observed' && row.values.air_temperature !== null)
    return day ? { table, day } : null
  })
  // Today's precipitation so far, from the same hours (the day in progress has no daily total)
  const rainToday = $derived(latestHours.value.data ? rainSoFarByPoint(latestHours.value.data, 1, today)[0] : null)

  const title = $derived(saved?.name ?? name ?? 'Unsaved location')
  const weatherView = $derived<WeatherView>({
    step: $view.step,
    range: $view.range,
    dates: $view.dates,
    roll: $view.roll,
    forecast: $view.forecast,
  })

  const ddView = $derived<DegreeDaysView>({
    dd: $view.dd,
    from: $view.from,
    since: $view.since,
    year: $view.season,
    projection: $view.projection,
  })
  const dataView = $derived<DataView>({ get: $view.get })
  const climateView = $derived<ClimateView>({
    period: $view.cperiod,
    dd: $view.cdd,
    start: $view.cstart,
    year: $view.cyear,
    month: $view.cmonth,
    variable: $view.cvar,
  })
  function patchClimate(changes: Partial<ClimateView>) {
    const names = { period: 'cperiod', dd: 'cdd', start: 'cstart', year: 'cyear', month: 'cmonth', variable: 'cvar' }
    view.patch(
      Object.fromEntries(
        Object.entries(changes).map(([key, value]) => [names[key as keyof ClimateView], value]),
      ) as Partial<typeof $view>,
    )
  }
  // A saved site's planting date (its preferences), for the Degree days tab's count from planting
  const savedPlanting = $derived(saved ? (effectivePrefs(saved.key).planting ?? null) : null)
  const savedBiofix = $derived(saved ? (effectivePrefs(saved.key).biofix ?? null) : null)
  // A date chosen to count from is kept with a saved site (D120), as a model at a site keeps its settings
  function saveSince(from: 'planting' | 'biofix', date: string | null) {
    if (saved) setPrefs({ kind: 'site', key: saved.key }, from === 'planting' ? { planting: date } : { biofix: date })
  }

  const tabs = [
    { value: 'overview', label: 'Overview' },
    { value: 'weather', label: 'Weather' },
    { value: 'models', label: 'Models' },
    { value: 'degree-days', label: 'Degree days' },
    { value: 'climate', label: 'Climate' },
    { value: 'data', label: 'Data' },
  ] as const
</script>

<svelte:head>
  <title>{title} · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <SiteHeader
    {lat}
    {lng}
    name={name ?? null}
    {location}
    latest={latest?.day.date ?? null}
    {shareUrl}
    {models}
    {crops}
    {settings}
  />
  {#if locate.value.status === 'failed'}
    <p class="text-sm text-ink-muted" role="status">{locate.value.message}</p>
  {/if}

  <Tabs.Root value={$view.tab} onValueChange={(tab) => view.patch({ tab: tab as Tab })}>
    <!-- The tabs wrap rather than scroll: on a phone a sideways-scrolling row hid the Data tab past the screen's edge,
         with nothing to say it was there -->
    <Tabs.List class="flex flex-wrap gap-x-1 border-b border-line" aria-label="Site sections">
      {#each tabs as tab (tab.value)}
        <Tabs.Trigger
          value={tab.value}
          class="-mb-px cursor-pointer border-b-2 border-transparent px-3 py-2 text-sm font-medium whitespace-nowrap text-ink-muted
            hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600
            data-[state=active]:border-brand-600 data-[state=active]:text-ink"
        >
          {tab.label}
        </Tabs.Trigger>
      {/each}
    </Tabs.List>
    <Tabs.Content value="overview" class="pt-6">
      <!-- Only the tab shown makes its requests -->
      {#if $view.tab === 'overview'}<Overview
          {lat}
          {lng}
          {today}
          {latest}
          {rainToday}
          {models}
          {risk}
          {loadRisk}
        />{/if}
    </Tabs.Content>
    <Tabs.Content value="weather" class="pt-6">
      {#if $view.tab === 'weather'}
        <WeatherTab {lat} {lng} {today} view={weatherView} onchange={(changes) => view.patch(changes)} />
      {/if}
    </Tabs.Content>
    <Tabs.Content value="models" class="pt-6">
      {#if $view.tab === 'models'}<ModelsTab {lat} {lng} {today} {models} {crops} {risk} {loadRisk} />{/if}
    </Tabs.Content>
    <Tabs.Content value="degree-days" class="pt-6">
      {#if $view.tab === 'degree-days'}
        <DegreeDaysTab
          {lat}
          {lng}
          {today}
          {location}
          planting={savedPlanting}
          biofix={savedBiofix}
          onsave={saved ? saveSince : undefined}
          view={ddView}
          onchange={(changes) =>
            view.patch({
              ...('dd' in changes ? { dd: changes.dd } : {}),
              ...('from' in changes ? { from: changes.from } : {}),
              ...('since' in changes ? { since: changes.since } : {}),
              ...('year' in changes ? { season: changes.year } : {}),
              ...('projection' in changes ? { projection: changes.projection } : {}),
            })}
        />
      {/if}
    </Tabs.Content>
    <Tabs.Content value="climate" class="pt-6">
      {#if $view.tab === 'climate'}
        <ClimateTab {lat} {lng} {today} {location} view={climateView} onchange={patchClimate} />
      {/if}
    </Tabs.Content>
    <Tabs.Content value="data" class="pt-6">
      {#if $view.tab === 'data'}
        <DataTab {lat} {lng} {today} {models} view={dataView} onchange={(changes) => view.patch(changes)} />
      {/if}
    </Tabs.Content>
  </Tabs.Root>
  {#if locate.value.data?.meta.attribution}
    <p class="text-xs text-ink-muted">{locate.value.data.meta.attribution}</p>
  {/if}
</div>
