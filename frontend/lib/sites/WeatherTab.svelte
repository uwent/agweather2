<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import ChartCard from '../charts/ChartCard.svelte'
  import { downloadCsv, toCsv } from '../csv'
  import {
    panelColumns,
    panelCsvRows,
    panelOption,
    panelSummary,
    panelTable,
    shownPanels,
    weatherPanels,
  } from '../charts/weatherCharts'
  import SegmentedChoice from '../components/SegmentedChoice.svelte'
  import { addDays } from '../dates'
  import { tableRows } from '../tableRows'
  import { currentUnits } from '../units'
  import Failed from './Failed.svelte'
  import { request } from './request.svelte'
  import { rangeDays, type Range } from './text'

  export type WeatherView = {
    step: 'daily' | 'hourly'
    range: Range
    dates: { start: string; end: string } | null
    roll: number | null
    forecast: boolean
  }

  // The Weather tab: a panel per measure (lib/charts/weatherCharts), stacked on one time axis and zooming
  // together, from /weather/daily or, over a week or less, /weather/hourly. The settings are the page's view
  // (in its Share link); values come in metric and convert at display, so a change of units needs no request.
  let {
    lat,
    lng,
    today,
    view,
    onchange,
  }: {
    lat: number
    lng: number
    today: string
    view: WeatherView
    onchange: (changes: Partial<WeatherView>) => void
  } = $props()

  const units = $derived(currentUnits())
  const hourly = $derived(view.step === 'hourly')
  const panels = $derived(weatherPanels({ hourly }))
  const answer = request<TableResponse>()
  const group = $props.id()

  // Custom dates as typed, applied with Show
  let customStart = $state(untrack(() => view.dates?.start ?? addDays(today, -30)))
  let customEnd = $state(untrack(() => view.dates?.end ?? today))
  let dateError = $state('')

  const days = $derived(rangeDays(view.range, today, view.dates))

  function load() {
    const { start, end } = days
    const params = {
      lat,
      lng,
      start,
      end,
      vars: panelColumns(panels),
      forecast: view.forecast,
      units: 'metric',
      ...(hourly ? {} : { roll: view.roll }),
    }
    return answer.load((signal) =>
      get<TableResponse>(hourly ? '/weather/hourly' : '/weather/daily', params, { signal }),
    )
  }

  // What the request depends on, as text, so an equal view (a new object with the same settings) doesn't refetch
  const requestKey = $derived(JSON.stringify([lat, lng, days, hourly, view.forecast, hourly ? null : view.roll]))
  $effect(() => {
    void requestKey
    untrack(load)
  })
  onDestroy(() => answer.cancel())

  const table = $derived(answer.value.data ? tableRows(answer.value.data) : null)
  const shown = $derived(table ? shownPanels(panels, table) : [])
  const roll = $derived(hourly ? null : view.roll)

  function applyDates(event: SubmitEvent) {
    event.preventDefault()
    if (!customStart || !customEnd) {
      dateError = 'Enter a start date and an end date.'
      return
    }
    if (customEnd < customStart) {
      dateError = 'The end date is before the start date. Choose an end date on or after the start date.'
      return
    }
    dateError = ''
    onchange({ range: 'custom', dates: { start: customStart, end: customEnd } })
  }

  const ranges = $derived([
    { value: 'week' as const, label: 'Past week' },
    { value: 'month' as const, label: '30 days', disabled: hourly },
    { value: 'season' as const, label: 'Season', disabled: hourly },
    { value: 'custom' as const, label: 'Custom', disabled: hourly },
  ])

  // Hours only over a week: switching to hourly from a longer range shows the past week
  function setStep(step: WeatherView['step']) {
    onchange(step === 'hourly' ? { step, range: 'week' } : { step })
  }

  function download(key: string) {
    const panel = shown.find((p) => p.key === key)
    if (!panel || !table) return
    downloadCsv(`agweather-${key}-${lat},${lng}.csv`, toCsv(panelCsvRows(panel, table, units)))
  }
</script>

<div class="space-y-4">
  <div class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-md border border-line bg-surface-raised p-3">
    <SegmentedChoice
      legend="Daily or hourly"
      name="weather-step"
      options={[
        { value: 'daily', label: 'Daily' },
        { value: 'hourly', label: 'Hourly' },
      ]}
      value={view.step}
      onchange={setStep}
    />
    <SegmentedChoice
      legend="Days shown"
      name="weather-range"
      options={ranges}
      value={view.range}
      onchange={(range) => onchange({ range })}
    />
    {#if !hourly}
      <label class="flex items-center gap-2 text-xs">
        <span class="text-ink-muted">Smoothing</span>
        <select
          class="rounded-md border border-line bg-surface px-2 py-1 text-xs"
          value={String(view.roll ?? '')}
          onchange={(event) => {
            const value = event.currentTarget.value
            onchange({ roll: value ? Number(value) : null })
          }}
        >
          <option value="">None</option>
          <option value="7">7-day</option>
          <option value="14">14-day</option>
          <option value="28">28-day</option>
        </select>
      </label>
    {/if}
    <label class="flex items-center gap-2 text-xs">
      <input
        type="checkbox"
        class="size-4 accent-brand-600"
        checked={view.forecast}
        onchange={(event) => onchange({ forecast: event.currentTarget.checked })}
      />
      Show the forecast
    </label>
  </div>

  {#if view.range === 'custom' && !hourly}
    <form class="flex flex-wrap items-end gap-3 text-sm" onsubmit={applyDates} novalidate>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">Start date</span>
        <input
          type="date"
          class="rounded-md border border-line bg-surface px-2 py-1"
          bind:value={customStart}
          aria-invalid={dateError ? 'true' : undefined}
        />
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">End date</span>
        <input
          type="date"
          class="rounded-md border border-line bg-surface px-2 py-1"
          bind:value={customEnd}
          aria-invalid={dateError ? 'true' : undefined}
        />
      </label>
      <button
        type="submit"
        class="rounded-md border border-line bg-surface-raised px-3 py-1 hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
      >
        Show
      </button>
      <p class="w-full text-sm text-danger-ink" role="alert">{dateError}</p>
    </form>
  {/if}

  {#if answer.value.status === 'failed'}
    <Failed {...answer.value} retry={load} />
  {/if}
  {#if answer.value.data && warningsOf(answer.value.data).length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on this data">
      {#each warningsOf(answer.value.data) as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if table}
    <div class="space-y-3" aria-busy={answer.value.status === 'loading'}>
      {#each shown as panel (panel.key)}
        <ChartCard
          title={panel.title}
          info={panel.info(units)}
          height={panel.totals || panel.below ? '18rem' : '14rem'}
          build={(palette, zoom) => panelOption(panel, table, { units, palette, today, roll, view: zoom })}
          summary={panelSummary(panel, table, units)}
          table={() => panelTable(panel, table, units, roll)}
          download={() => download(panel.key)}
          {group}
        />
      {:else}
        <p class="text-sm text-ink-muted">No weather for these days yet.</p>
      {/each}
    </div>
  {:else if answer.value.status === 'loading'}
    <div class="space-y-3" aria-hidden="true">
      {#each [0, 1, 2] as i (i)}<div class="h-56 animate-pulse rounded-lg bg-surface-raised"></div>{/each}
    </div>
  {/if}
</div>
