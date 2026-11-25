<script lang="ts">
  import { Tabs } from 'bits-ui'
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import { addDays, today as gridToday } from '@/lib/dates'
  import { request } from '@/lib/sites/request.svelte'
  import Overview from '@/lib/sites/Overview.svelte'
  import SiteHeader from '@/lib/sites/SiteHeader.svelte'
  import WeatherTab, { type WeatherView } from '@/lib/sites/WeatherTab.svelte'
  import { siteAt } from '@/lib/sites.svelte'
  import { tableRows } from '@/lib/tableRows'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { SiteProps } from '@/types'
  import type { LocateResponse, TableResponse } from '@/types/api'

  // A site's page (F1): any point by its coordinates, saved or not. The header says where it is and whose days
  // it uses; the tabs show today and the forecast with the risk now (Overview) and the weather as charts
  // (Weather). Its content (the point, a shared link's name, the models' catalog) comes as props; its numbers
  // from the API (D117). The tab and the Weather tab's settings are the page's view, kept per browser tab and
  // given in full by Share (D118).
  let { lat, lng, name, models }: SiteProps = $props()

  const today = $derived(gridToday())

  const view = viewState({
    tab: field(codecs.oneOf(['overview', 'weather'] as const), 'overview'),
    step: field(codecs.oneOf(['daily', 'hourly'] as const), 'daily'),
    range: field(codecs.oneOf(['week', 'month', 'season', 'custom'] as const), 'month'),
    dates: field(codecs.dateRange, null),
    roll: field(codecs.integer({ min: 2, max: 365 }), null),
    forecast: field(codecs.boolean, true),
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
  const latestHours = request<TableResponse>()
  // Inertia hands the page its props again after it mounts: the point as text, so equal props don't refetch
  const pointKey = $derived(`${lat},${lng}`)
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
  onDestroy(() => [locate, latestHours].forEach((r) => r.cancel()))

  const location = $derived(locate.value.data?.data ?? null)
  // The newest observed hour with a temperature
  const latest = $derived.by(() => {
    const body = latestHours.value.data
    if (!body) return null
    const table = tableRows(body)
    const day = table.days.findLast((row) => row.kind === 'observed' && row.values.air_temperature !== null)
    return day ? { table, day } : null
  })

  const title = $derived(saved?.name ?? name ?? 'Unsaved location')
  const weatherView = $derived<WeatherView>({
    step: $view.step,
    range: $view.range,
    dates: $view.dates,
    roll: $view.roll,
    forecast: $view.forecast,
  })

  const tabs = [
    { value: 'overview', label: 'Overview' },
    { value: 'weather', label: 'Weather' },
  ] as const
</script>

<svelte:head>
  <title>{title} · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <SiteHeader {lat} {lng} name={name ?? null} {location} latest={latest?.day.date ?? null} {shareUrl} />
  {#if locate.value.status === 'failed'}
    <p class="text-sm text-ink-muted" role="status">{locate.value.message}</p>
  {/if}

  <Tabs.Root value={$view.tab} onValueChange={(tab) => view.patch({ tab: tab as 'overview' | 'weather' })}>
    <Tabs.List class="flex gap-1 border-b border-line" aria-label="Site sections">
      {#each tabs as tab (tab.value)}
        <Tabs.Trigger
          value={tab.value}
          class="-mb-px cursor-pointer border-b-2 border-transparent px-3 py-2 text-sm font-medium text-ink-muted
            hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600
            data-[state=active]:border-brand-600 data-[state=active]:text-ink"
        >
          {tab.label}
        </Tabs.Trigger>
      {/each}
    </Tabs.List>
    <Tabs.Content value="overview" class="pt-6">
      <!-- Only the tab shown makes its requests -->
      {#if $view.tab === 'overview'}<Overview {lat} {lng} {today} {latest} {models} />{/if}
    </Tabs.Content>
    <Tabs.Content value="weather" class="pt-6">
      {#if $view.tab === 'weather'}
        <WeatherTab {lat} {lng} {today} view={weatherView} onchange={(changes) => view.patch(changes)} />
      {/if}
    </Tabs.Content>
  </Tabs.Root>
  {#if locate.value.data?.meta.attribution}
    <p class="text-xs text-ink-muted">{locate.value.data.meta.attribution}</p>
  {/if}
</div>
