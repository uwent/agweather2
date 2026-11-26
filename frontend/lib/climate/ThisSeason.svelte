<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { PresetsResponse, TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import { compareTable } from '../charts/climateCharts'
  import { formatDate } from '../dates'
  import Failed from '../components/Failed.svelte'
  import { parseSetting, resolveSeries, seriesName, settingWords } from '../sites/degreeDays'
  import { request } from '../request.svelte'
  import { currentUnits } from '../units'
  import CompareChart from './CompareChart.svelte'
  import { DEFAULT_PERIOD, type Period } from './periods'
  import { climateSlots, type Slots } from './slots'

  export type ThisSeasonSettings = {
    /** A degree-day preset's id or a setting (`sine_41_86`); empty for modified 50/86 °F */
    dd: string
    /** The day the totals start, in `year`; null for January 1 */
    start: string | null
    /** The season, a year; null for this one */
    year: number | null
  }

  // "This season so far" (track 6.2): degree days and precipitation from a start date, this year (observed, then
  // the forecast) against last year and the normal with its usual range, and how many days ahead or behind normal
  // the degree days run. One `/climate/compare` request for both, in °F and inches (`units=us`), converted at
  // display. Takes only a location and its settings, so `/climate` shows it as the site page does.
  let {
    lat,
    lng,
    today,
    period = DEFAULT_PERIOD,
    dd = '',
    start = null,
    year = null,
    onchange,
    queue = climateSlots,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    period?: Period
    onchange?: (changes: Partial<ThisSeasonSettings>) => void
    queue?: Slots
  } & Partial<ThisSeasonSettings> = $props()

  const DEFAULT_DD = 'modified_50_86'
  const units = $derived(currentUnits())
  const current = $derived(Number(today.slice(0, 4)))
  // The archive's years (the last 11), as the Degree days tab offers
  const years = $derived(Array.from({ length: 11 }, (_, k) => current - k))
  const season = $derived(year && years.includes(year) ? year : current)
  const from = $derived(start && start.startsWith(`${season}-`) ? start : `${season}-01-01`)

  const presets = request<PresetsResponse>()
  presets.load((signal) => get<PresetsResponse>('/degree-days/presets', undefined, { signal }))
  const presetList = $derived(presets.value.data?.data ?? [])
  const token = $derived(dd || DEFAULT_DD)
  const isPreset = $derived(/^[a-z]+(-[a-z]+)*$/.test(token))
  const series = $derived(resolveSeries([token], presetList)[0] ?? resolveSeries([DEFAULT_DD], [])[0])
  // A preset's setting is known once the presets come
  const ready = $derived(!isPreset || presets.value.status !== 'loading')

  const answer = request<TableResponse>()
  const query = $derived({
    lat,
    lng,
    period,
    units: 'us',
    vars: ['precipitation_sum'],
    dd: [series.dd],
    start: from,
    end: season < current ? `${season}-12-31` : undefined,
  })
  const key = $derived(ready ? JSON.stringify(query) : '')
  function load() {
    const params = untrack(() => query)
    answer.load((signal) => queue.run(signal, () => get<TableResponse>('/climate/compare', params, { signal })))
  }
  $effect(() => {
    if (key) untrack(load)
  })
  onDestroy(() => [presets, answer].forEach((r) => r.cancel()))

  const table = $derived(answer.value.data ? compareTable(answer.value.data) : null)
  const ddColumn = $derived(`dd_${series.dd}`)
  const ddName = $derived(series.preset ? series.preset.label : seriesName(series, units))
  // Last year's line only for this season: a past season's "last year" would be the period's last year
  const lastYear = $derived(season === current)
  const crops = $derived(presetList.filter((p) => p.group === 'crop'))
  const insects = $derived(presetList.filter((p) => p.group === 'insect'))
  const control = 'rounded-md border border-line bg-surface px-2 py-1 text-xs'
</script>

<div class="space-y-4">
  <p class="max-w-prose text-sm text-ink-muted">
    {`Degree days and precipitation from ${formatDate(from)}${season < current ? ` to the end of ${season}` : ''}, against the normal for the same dates.`}
  </p>
  {#if onchange}
    <div class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-md border border-line bg-surface-raised p-3">
      <label class="flex max-w-full min-w-0 items-center gap-2 text-xs">
        <span class="text-ink-muted">Degree days</span>
        <select
          class="{control} max-w-full min-w-0"
          value={token}
          onchange={(event) =>
            onchange({ dd: event.currentTarget.value === DEFAULT_DD ? '' : event.currentTarget.value })}
        >
          <option value={DEFAULT_DD}>{`${settingWords(parseSetting(DEFAULT_DD)!, units)} (most crops)`}</option>
          {#if !isPreset && token !== DEFAULT_DD}<option value={token}>{seriesName(series, units)}</option>{/if}
          {#if isPreset && !presetList.some((p) => p.id === token)}<option value={token}>Loading…</option>{/if}
          {#if crops.length}
            <optgroup label="Crops">
              {#each crops as preset (preset.id)}<option value={preset.id}>{preset.label}</option>{/each}
            </optgroup>
          {/if}
          {#if insects.length}
            <optgroup label="Insects">
              {#each insects as preset (preset.id)}<option value={preset.id}>{preset.label}</option>{/each}
            </optgroup>
          {/if}
        </select>
      </label>
      <label class="flex items-center gap-2 text-xs">
        <span class="text-ink-muted">Season</span>
        <select
          class={control}
          value={String(season)}
          onchange={(event) => {
            const next = Number(event.currentTarget.value)
            onchange({ year: next === current ? null : next, start: null })
          }}
        >
          {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
        </select>
      </label>
      <label class="flex items-center gap-2 text-xs">
        <span class="text-ink-muted">From</span>
        <input
          type="date"
          class={control}
          min="{season}-01-01"
          max="{season}-12-31"
          value={from}
          onchange={(event) => {
            const value = event.currentTarget.value
            if (value) onchange({ start: value === `${season}-01-01` ? null : value })
          }}
        />
      </label>
    </div>
  {/if}
  {#if presets.value.status === 'failed' && isPreset}
    <Failed
      {...presets.value}
      retry={() => presets.load((signal) => get('/degree-days/presets', undefined, { signal }))}
    />
  {/if}
  {#if answer.value.status === 'failed'}
    <Failed {...answer.value} retry={load} />
  {/if}
  {#if answer.value.data && warningsOf(answer.value.data).length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on this season’s data">
      {#each warningsOf(answer.value.data) as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if table}
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2" aria-busy={answer.value.status === 'loading'}>
      <CompareChart
        {table}
        column={ddColumn}
        label="Degree days"
        {today}
        title={`Degree days: ${ddName}`}
        {lastYear}
        filename={`agweather-degree-days-normal-${lat},${lng}`}
      />
      <CompareChart
        {table}
        column="precipitation_sum"
        label="Precipitation"
        {today}
        title="Precipitation"
        {lastYear}
        filename={`agweather-precipitation-normal-${lat},${lng}`}
      />
    </div>
  {:else if answer.value.status === 'loading'}
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2" aria-hidden="true">
      <div class="h-96 animate-pulse rounded-lg bg-surface-raised"></div>
      <div class="h-96 animate-pulse rounded-lg bg-surface-raised"></div>
    </div>
  {/if}
</div>
