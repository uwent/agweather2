<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import { compareTable } from '../charts/climateCharts'
  import { formatDate, MONTH_NAMES, SHORT_MONTHS } from '../dates'
  import Failed from '../components/Failed.svelte'
  import { request } from '../request.svelte'
  import { currentUnits } from '../units'
  import {
    countColumn,
    countLabel,
    countMonths,
    countRows,
    countSpec,
    countWords,
    DAY_COUNTS,
    daysText,
  } from './counts'
  import { DEFAULT_PERIOD, periodWords, periodYears, type Period } from './periods'
  import { climateSlots, type Slots } from './slots'

  // "This month against normal" (track 6.2): how many days this month so far were hot, freezing, dry or wet,
  // against the normal count to the same date with its usual range and last year's; then a typical year's counts
  // by month. `/climate/compare` and `/climate/normals` with D88's counts (`count=`), thresholds in °F and inches
  // (`units=us`), named in the reader's units.
  let {
    lat,
    lng,
    today,
    period = DEFAULT_PERIOD,
    month = null,
    onchange,
    queue = climateSlots,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    period?: Period
    /** The month of this year, 1–12; null for this month */
    month?: number | null
    onchange?: (changes: { month: number | null }) => void
    queue?: Slots
  } = $props()

  const units = $derived(currentUnits())
  const year = $derived(Number(today.slice(0, 4)))
  const thisMonth = $derived(Number(today.slice(5, 7)))
  const shown = $derived(month && month >= 1 && month <= thisMonth ? month : thisMonth)
  const first = $derived(`${year}-${String(shown).padStart(2, '0')}-01`)
  const last = $derived(new Date(Date.UTC(year, shown, 0)).toISOString().slice(0, 10))
  const counts = DAY_COUNTS.map(countSpec)

  const compare = request<TableResponse>()
  const months = request<TableResponse>()
  const compareQuery = $derived({ lat, lng, period, units: 'us', vars: '', count: counts, start: first, end: last })
  const monthsQuery = $derived({ lat, lng, period, units: 'us', count: counts, interval: 'month' })
  const compareKey = $derived(JSON.stringify(compareQuery))
  const monthsKey = $derived(JSON.stringify(monthsQuery))

  function loadCompare() {
    const params = untrack(() => compareQuery)
    compare.load((signal) => queue.run(signal, () => get<TableResponse>('/climate/compare', params, { signal })))
  }
  function loadMonths() {
    const params = untrack(() => monthsQuery)
    months.load((signal) => queue.run(signal, () => get<TableResponse>('/climate/normals', params, { signal })))
  }
  $effect(() => {
    void compareKey
    untrack(loadCompare)
  })
  $effect(() => {
    void monthsKey
    untrack(loadMonths)
  })
  onDestroy(() => [compare, months].forEach((r) => r.cancel()))

  const table = $derived(compare.value.data ? compareTable(compare.value.data) : null)
  const rows = $derived(table ? countRows(table) : [])
  const typical = $derived(months.value.data ? countMonths(months.value.data) : null)
  const years = $derived(table?.years ?? periodYears(period, today))
  const asOf = $derived(table?.asOf && table.asOf >= first ? table.asOf : null)
  const missing = $derived(Math.max(0, ...rows.map((r) => r.missingDays)))
  const warnings = $derived([...new Set([...warningsOf(compare.value.data), ...warningsOf(months.value.data)])])

  const cell = 'py-1.5 pr-3 text-right tabular-nums'
  const head = 'py-1 pr-3 text-right font-medium'
  // The first column stays in view as a table scrolls sideways on a phone
  const sticky = 'sticky left-0 z-10 bg-surface'
</script>

<div class="space-y-4">
  {#if onchange}
    <label class="flex w-fit items-center gap-2 rounded-md border border-line bg-surface-raised p-3 text-xs">
      <span class="text-ink-muted">Month</span>
      <select
        class="rounded-md border border-line bg-surface px-2 py-1 text-xs"
        value={String(shown)}
        onchange={(event) => {
          const next = Number(event.currentTarget.value)
          onchange({ month: next === thisMonth ? null : next })
        }}
      >
        {#each MONTH_NAMES.slice(0, thisMonth) as name, k (name)}<option value={String(k + 1)}>
            {`${name} ${year}`}
          </option>{/each}
      </select>
    </label>
  {/if}

  {#each [compare.value, months.value] as value, k (k)}
    {#if value.status === 'failed'}
      <Failed {...value} retry={k ? loadMonths : loadCompare} />
    {/if}
  {/each}
  {#if warnings.length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on the counts">
      {#each warnings as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if table}
    <p class="max-w-prose text-sm">
      {asOf
        ? `Days in ${MONTH_NAMES[shown - 1]} ${year} through ${formatDate(asOf)}, against the normal count to the same date over ${periodWords(years)}. The usual range holds 8 years in 10.${missing ? ` Days without data aren’t counted (${missing} at most).` : ''}`
        : `No days of ${MONTH_NAMES[shown - 1]} have been observed yet.`}
    </p>
    <!-- Scrolls sideways on a phone; focusable so a keyboard can scroll it -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="overflow-x-auto focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Days counted this month"
      tabindex="0"
      aria-busy={compare.value.status === 'loading'}
    >
      <table class="w-full min-w-xl text-sm">
        <caption class="sr-only">{`Days counted in ${MONTH_NAMES[shown - 1]} ${year}, against normal`}</caption>
        <thead>
          <tr class="border-b border-line text-left text-xs text-ink-muted">
            <th scope="col" class="{sticky} py-1 pr-3 font-medium">Days</th>
            <th scope="col" class={head}>{year}</th>
            <th scope="col" class={head}>Normal</th>
            <th scope="col" class={head}>Usual range</th>
            <th scope="col" class={head}>{year - 1}</th>
            <th scope="col" class="py-1 text-left font-medium">Compared with normal</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row (countColumn(row.count))}
            <tr class="border-b border-line/60">
              <th scope="row" class="{sticky} py-1.5 pr-3 text-left font-normal">{countLabel(row.count, units)}</th>
              <td class="{cell} font-medium">{daysText(row.now)}</td>
              <td class={cell}>{daysText(row.normal, 1)}</td>
              <td class={cell}>
                {row.low !== null && row.high !== null ? `${daysText(row.low)}–${daysText(row.high)}` : '—'}
              </td>
              <td class={cell}>{daysText(row.lastYear)}</td>
              <td class="py-1.5 text-left">{asOf ? countWords(row.percentile) : '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if compare.value.status === 'loading'}
    <div class="h-64 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}

  {#if typical}
    <h3 class="text-sm font-medium">A typical year by month</h3>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="overflow-x-auto focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Normal days by month"
      tabindex="0"
      aria-busy={months.value.status === 'loading'}
    >
      <table class="w-full min-w-3xl text-sm">
        <caption class="mb-2 text-left text-sm text-ink-muted">
          {`The average number of days a month over ${periodWords(years)}.`}
        </caption>
        <thead>
          <tr class="border-b border-line text-left text-xs text-ink-muted">
            <th scope="col" class="{sticky} py-1 pr-3 font-medium">Days</th>
            {#each SHORT_MONTHS as name, k (name)}
              <th scope="col" class="{head} {k + 1 === shown ? 'text-ink' : ''}">{name}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each DAY_COUNTS as count (countColumn(count))}
            {@const values = typical.values[countColumn(count)] ?? []}
            <tr class="border-b border-line/60">
              <th scope="row" class="{sticky} py-1.5 pr-3 text-left font-normal">{countLabel(count, units)}</th>
              {#each SHORT_MONTHS as name, k (name)}
                <td class="{cell} {k + 1 === shown ? 'font-medium' : ''}">{daysText(values[k], 1)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if months.value.status === 'loading'}
    <div class="h-64 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</div>
