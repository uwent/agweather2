<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { TableResponse } from '@/types/api'

  import { get } from '../api'
  import ChartCard from '../charts/ChartCard.svelte'
  import {
    normalSpans,
    recentNormal,
    recentNormalOption,
    recentNormalRows,
    recentNormalSummary,
  } from '../charts/climateNormals'
  import { addDays } from '../dates'
  import Failed from '../sites/Failed.svelte'
  import { request } from '../sites/request.svelte'
  import { currentUnits } from '../units'
  import { DEFAULT_PERIOD, type Period } from './periods'
  import { climateSlots, type Slots } from './slots'

  // "Temperature against normal" (track 6.2): the last 60 days' highs and lows and the forecast's, each over its
  // normal and usual range (the 10th to 90th percentiles of the period's years). `/weather/daily` and
  // `/climate/normals` for the same days (two normals requests when the span crosses January 1), in °F
  // (`units=us`), converted at display.
  let {
    lat,
    lng,
    today,
    period = DEFAULT_PERIOD,
    days = 60,
    queue = climateSlots,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    period?: Period
    /** How many days back from today */
    days?: number
    queue?: Slots
  } = $props()

  const VARS = ['air_temperature_max', 'air_temperature_min']
  // The forecast reaches about 16 days ahead: normals for every day it could hold
  const AHEAD = 16
  const units = $derived(currentUnits())

  type Answers = { weather: TableResponse; normals: TableResponse[] }
  const answer = request<Answers>()
  const query = $derived({ lat, lng, period, start: addDays(today, -days), end: addDays(today, AHEAD) })
  const key = $derived(JSON.stringify(query))

  function load() {
    const { lat, lng, period, start, end } = untrack(() => query)
    answer.load(async (signal) => {
      const ask = (path: string, params: object) =>
        queue.run(signal, () => get<TableResponse>(path, params, { signal }))
      const [weather, ...normals] = await Promise.all([
        ask('/weather/daily', { lat, lng, start, vars: VARS, units: 'us' }),
        ...normalSpans(start, end).map((span) =>
          ask('/climate/normals', { lat, lng, period, vars: VARS, percentiles: [10, 90], units: 'us', ...span }),
        ),
      ])
      return { weather, normals }
    })
  }
  $effect(() => {
    void key
    untrack(load)
  })
  onDestroy(() => answer.cancel())

  const recent = $derived(answer.value.data ? recentNormal(answer.value.data.weather, answer.value.data.normals) : null)
  const summary = $derived(recent ? recentNormalSummary({ recent, units }) : '')
</script>

<div class="space-y-3">
  {#if answer.value.status === 'failed'}
    <Failed {...answer.value} retry={load} />
  {/if}
  {#if recent}
    {#if recent.warnings.length}
      <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on the temperature data">
        {#each recent.warnings as warning (warning)}<li>{warning}</li>{/each}
      </ul>
    {/if}
    <p class="max-w-prose text-sm">{summary}</p>
    <div aria-busy={answer.value.status === 'loading'}>
      <ChartCard
        title="Highs and lows against normal"
        info="The solid lines are each day’s high and low, observed and then forecast (shaded). The dashed lines are the normal high and low for the date, each over its usual range: the band between the 10th and 90th percentiles of the period’s years, which holds 8 years in 10."
        height="20rem"
        build={(palette) => recentNormalOption({ recent, units, palette, today })}
        {summary}
        table={() => recentNormalRows(recent, units)}
      />
    </div>
  {:else if answer.value.status === 'loading'}
    <div class="h-96 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</div>
