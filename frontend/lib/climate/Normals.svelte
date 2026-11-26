<script lang="ts" module>
  import type { Palette } from '../charts/palette'

  /** The variables the normals show, in the table's order: each its name, color and whether a month's figure is a
   * total (else a mean) */
  export const NORMAL_VARIABLES = [
    { id: 'air_temperature_max', name: 'Average high', color: (p: Palette) => p.temperature.max, total: false },
    { id: 'air_temperature_min', name: 'Average low', color: (p: Palette) => p.temperature.min, total: false },
    { id: 'precipitation_sum', name: 'Precipitation', color: (p: Palette) => p.precipitation, total: true },
    { id: 'et0_sum', name: 'Reference ET', color: (p: Palette) => p.degreeDays, total: true },
    { id: 'shortwave_radiation_sum', name: 'Sunlight', color: (p: Palette) => p.et, total: true },
  ] as const

  export type NormalVariable = (typeof NORMAL_VARIABLES)[number]['id']
  export const NORMAL_VARIABLE_IDS = NORMAL_VARIABLES.map((v) => v.id) as NormalVariable[]
  export const DEFAULT_NORMAL_VARIABLE: NormalVariable = 'air_temperature_max'
</script>

<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import ChartCard from '../charts/ChartCard.svelte'
  import {
    monthlyNormals,
    normalYear,
    normalYearOption,
    normalYearRows,
    normalYearSummary,
    yearFromMonths,
  } from '../charts/climateNormals'
  import Failed from '../sites/Failed.svelte'
  import { request } from '../sites/request.svelte'
  import { currentUnits } from '../units'
  import { DEFAULT_PERIOD, periodWords, periodYears, type Period } from './periods'
  import { climateSlots, type Slots } from './slots'

  // "Normals" (track 6.2): a place's normals by month (average high and low, precipitation, reference ET and
  // sunlight, with the year's), and one variable through the year over its usual range, a total as its running
  // total from January 1. `/climate/normals` twice (by month, and the variable's days with `percentiles=10,90`),
  // in US units (`units=us`), converted at display.
  let {
    lat,
    lng,
    today,
    period = DEFAULT_PERIOD,
    variable = DEFAULT_NORMAL_VARIABLE,
    onchange,
    queue = climateSlots,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    period?: Period
    /** The variable drawn through the year */
    variable?: NormalVariable
    onchange?: (changes: { variable: NormalVariable }) => void
    queue?: Slots
  } = $props()

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const units = $derived(currentUnits())
  const chosen = $derived(NORMAL_VARIABLES.find((v) => v.id === variable) ?? NORMAL_VARIABLES[0])

  const months = request<TableResponse>()
  const daily = request<TableResponse>()
  const monthsQuery = $derived({ lat, lng, period, units: 'us', interval: 'month', vars: NORMAL_VARIABLE_IDS })
  const dailyQuery = $derived({ lat, lng, period, units: 'us', vars: [chosen.id], percentiles: [10, 90] })
  const monthsKey = $derived(JSON.stringify(monthsQuery))
  const dailyKey = $derived(JSON.stringify(dailyQuery))
  function loadMonths() {
    const params = untrack(() => monthsQuery)
    months.load((signal) => queue.run(signal, () => get<TableResponse>('/climate/normals', params, { signal })))
  }
  function loadDaily() {
    const params = untrack(() => dailyQuery)
    daily.load((signal) => queue.run(signal, () => get<TableResponse>('/climate/normals', params, { signal })))
  }
  $effect(() => {
    void monthsKey
    untrack(loadMonths)
  })
  $effect(() => {
    void dailyKey
    untrack(loadDaily)
  })
  onDestroy(() => [months, daily].forEach((r) => r.cancel()))

  const table = $derived(months.value.data ? monthlyNormals(months.value.data) : null)
  const normal = $derived(daily.value.data ? normalYear(daily.value.data, chosen.id) : null)
  const years = $derived(table?.years ?? normal?.years ?? periodYears(period, today))
  const label = $derived(normal?.cumulative ? `${chosen.name}, total from January 1` : chosen.name)
  const summary = $derived(normal ? normalYearSummary({ normal, units, today, label }) : '')
  const warnings = $derived([...new Set([...warningsOf(months.value.data), ...warningsOf(daily.value.data)])])

  function shown(id: string, value: number | null | undefined) {
    const unit = table?.units[id]
    return unit
      ? units.format(unit, value, { unit: false })
      : value === null || value === undefined
        ? '—'
        : String(value)
  }
  const unitOf = (id: string) => (table?.units[id] ? units.label(table.units[id]) : '')
  const thisMonth = $derived(Number(today.slice(5, 7)))
  const cell = 'py-1.5 pr-3 text-right tabular-nums'
  const head = 'py-1 pr-3 text-right font-medium'
  const sticky = 'sticky left-0 z-10 bg-surface'
</script>

<div class="space-y-4">
  {#each [months.value, daily.value] as value, k (k)}
    {#if value.status === 'failed'}
      <Failed {...value} retry={k ? loadDaily : loadMonths} />
    {/if}
  {/each}
  {#if warnings.length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on the normals">
      {#each warnings as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if table}
    <!-- Scrolls sideways on a phone, the first column kept in view; focusable so a keyboard can scroll it -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="overflow-x-auto focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Normals by month"
      tabindex="0"
      aria-busy={months.value.status === 'loading'}
    >
      <table class="w-full min-w-3xl text-sm">
        <caption class="mb-2 text-left text-sm text-ink-muted">
          {`Normals by month over ${periodWords(years)}: temperatures are the month’s average, the others its total.`}
        </caption>
        <thead>
          <tr class="border-b border-line text-left text-xs text-ink-muted">
            <th scope="col" class="{sticky} py-1 pr-3 font-medium">Normal</th>
            {#each MONTHS as name, k (name)}
              <th scope="col" class="{head} {k + 1 === thisMonth ? 'text-ink' : ''}">{name}</th>
            {/each}
            <th scope="col" class={head}>Year</th>
          </tr>
        </thead>
        <tbody>
          {#each NORMAL_VARIABLES as v (v.id)}
            {@const values = table.values[v.id] ?? []}
            <tr class="border-b border-line/60">
              <th scope="row" class="{sticky} py-1.5 pr-3 text-left font-normal whitespace-nowrap">
                {`${v.name} (${unitOf(v.id)})`}
              </th>
              {#each MONTHS as name, k (name)}
                <td class="{cell} {k + 1 === thisMonth ? 'font-medium' : ''}">{shown(v.id, values[k])}</td>
              {/each}
              <td class="{cell} font-medium">{shown(v.id, yearFromMonths(table.months, values, v.total))}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if months.value.status === 'loading'}
    <div class="h-48 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}

  {#if onchange}
    <label class="flex w-fit items-center gap-2 rounded-md border border-line bg-surface-raised p-3 text-xs">
      <span class="text-ink-muted">Through the year</span>
      <select
        class="rounded-md border border-line bg-surface px-2 py-1 text-xs"
        value={chosen.id}
        onchange={(event) => onchange({ variable: event.currentTarget.value as NormalVariable })}
      >
        {#each NORMAL_VARIABLES as v (v.id)}<option value={v.id}>{v.name}</option>{/each}
      </select>
    </label>
  {/if}
  {#if normal}
    <div aria-busy={daily.value.status === 'loading'}>
      <ChartCard
        title={normal.cumulative
          ? `${chosen.name}: normal total through the year`
          : `${chosen.name}: normal through the year`}
        info={normal.cumulative
          ? 'The line is the normal running total from January 1: each year’s own total to the date, averaged over the period. The band is its usual range, between the 10th and 90th percentiles of those years, which holds 8 years in 10.'
          : 'The line is the normal for each date: the period’s years averaged over the 15 days around it. The band is its usual range, between the 10th and 90th percentiles, which holds 8 years in 10.'}
        height="18rem"
        build={(palette) =>
          normalYearOption({ normal, units, palette, today, label: chosen.name, color: chosen.color(palette) })}
        {summary}
        table={() => normalYearRows(normal, units)}
      />
    </div>
  {:else if daily.value.status === 'loading'}
    <div class="h-80 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</div>
