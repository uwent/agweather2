<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import ChartCard from '../charts/ChartCard.svelte'
  import {
    freezeChances,
    freezeDates,
    freezeOddsOption,
    freezeOddsRows,
    FREEZE_DASHES,
    FREEZE_TOKENS,
    freezeSummary,
    type FreezeShow,
    yearFreezes,
  } from '../charts/climateCharts'
  import GlossaryText from '../components/GlossaryText.svelte'
  import { formatDate } from '../dates'
  import Failed from '../sites/Failed.svelte'
  import { request } from '../sites/request.svelte'
  import { currentUnits } from '../units'
  import { DEFAULT_PERIOD, periodWords, periodYears, type Period } from './periods'
  import { FREEZE_THRESHOLDS_F, thresholdLabel, thresholdsInWords } from './words'

  // A place's freeze odds (track 6.1, shared with the freeze tool and the site's Climate tab): for each threshold
  // the dates by which 1 year in 10, half and 9 in 10 had had their last spring freeze or first fall freeze, this
  // year's (or `thisYear`'s) own dates beside them, and the chance of a freeze by date as a chart. Asks
  // `/climate/frost` and `/climate/frost/chances` (kept a day by the browser) and `/freeze` for the year's dates,
  // all in °F (`units=us`, as the thresholds are named), converted at display.
  let {
    lat,
    lng,
    today,
    period = DEFAULT_PERIOD,
    thresholds = [...FREEZE_THRESHOLDS_F],
    show = 'both',
    thisYear,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    period?: Period
    /** °F, coldest last (32, 28, 24 by default; a crop's killing freeze in a tool) */
    thresholds?: number[]
    show?: FreezeShow
    /** The year whose own freeze dates are shown beside the odds: default this year; null for none */
    thisYear?: number | null
  } = $props()

  const units = $derived(currentUnits())
  const current = $derived(Number(today.slice(0, 4)))
  const year = $derived(thisYear === undefined ? current : thisYear)

  const frost = request<TableResponse>()
  const chances = request<TableResponse>()
  const observed = request<TableResponse>()

  const climateQuery = $derived({ lat, lng, period, thresholds, units: 'us' })
  const yearQuery = $derived(
    year === null
      ? null
      : {
          lat,
          lng,
          thresholds,
          units: 'us',
          start: `${year}-01-01`,
          end: year < current ? `${year}-12-31` : undefined,
        },
  )

  function loadClimate() {
    const params = untrack(() => climateQuery)
    frost.load((signal) => get<TableResponse>('/climate/frost', params, { signal }))
    chances.load((signal) => get<TableResponse>('/climate/frost/chances', params, { signal }))
  }
  function loadYear() {
    const params = untrack(() => yearQuery)
    if (params) observed.load((signal) => get<TableResponse>('/freeze', params, { signal }))
  }
  const climateKey = $derived(JSON.stringify(climateQuery))
  const yearKey = $derived(JSON.stringify(yearQuery))
  $effect(() => {
    void climateKey
    untrack(loadClimate)
  })
  $effect(() => {
    void yearKey
    untrack(loadYear)
  })
  onDestroy(() => [frost, chances, observed].forEach((r) => r.cancel()))

  const dates = $derived(frost.value.data ? freezeDates(frost.value.data) : null)
  const odds = $derived(chances.value.data ? freezeChances(chances.value.data) : null)
  // This year's dates by threshold, from `/freeze` (its thresholds as asked, °F)
  const yearDates = $derived(year !== null && observed.value.data ? yearFreezes(observed.value.data) : null)
  const years = $derived(dates?.years ?? odds?.years ?? periodYears(period, today))
  const summary = $derived(dates ? freezeSummary({ dates, units, show }) : '')
  const warnings = $derived([
    ...new Set([
      ...warningsOf(frost.value.data),
      ...warningsOf(chances.value.data),
      ...warningsOf(observed.value.data),
    ]),
  ])

  const spring = $derived(show !== 'fall')
  const fall = $derived(show !== 'spring')
  // A year's date in words: "None yet" this year, "None" in a year that's over
  function ownDate(date: string | null | undefined): string {
    if (date) return formatDate(date)
    return year === current ? 'None yet' : 'None'
  }
  const cell = (date: string | null | undefined) => (date ? formatDate(date) : 'None')
  const headingClass = 'py-1 pr-3 text-right font-medium'
</script>

<div class="space-y-4">
  <GlossaryText
    class="max-w-prose text-sm text-ink-muted"
    paragraphs={[
      `When the last freeze of spring and the first freeze of fall came over ${periodWords(years)}, at ${thresholdsInWords(thresholds, units)}. A typical date is the one by which half the years had had their freeze; an early or late date is the one that only 1 year in 10 came before or after.`,
    ]}
  />

  {#each [frost.value, chances.value] as value, k (k)}
    {#if value.status === 'failed'}
      <Failed {...value} retry={loadClimate} />
    {/if}
  {/each}
  {#if observed.value.status === 'failed'}
    <Failed {...observed.value} retry={loadYear} />
  {/if}
  {#if warnings.length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on the freeze data">
      {#each warnings as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if dates}
    <!-- Scrolls sideways on a phone; focusable so a keyboard can scroll it -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="overflow-x-auto focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Freeze dates"
      tabindex="0"
      aria-busy={frost.value.status === 'loading'}
    >
      <table class="w-full min-w-lg text-sm">
        <caption class="mb-2 text-left text-sm text-ink-muted">
          {`Freeze dates over ${periodWords(years)}${year !== null ? `, and ${year}’s own` : ''}.`}
        </caption>
        <thead>
          <tr class="text-left text-xs text-ink-muted">
            <td></td>
            {#if spring}
              <th scope="colgroup" colspan={year !== null ? 4 : 3} class="pr-3 text-center font-medium">
                Last freeze in spring
              </th>
            {/if}
            {#if fall}
              <th scope="colgroup" colspan={year !== null ? 4 : 3} class="pr-3 text-center font-medium">
                First freeze in fall
              </th>
            {/if}
            {#if show === 'both'}<td></td>{/if}
          </tr>
          <tr class="border-b border-line text-left text-xs text-ink-muted">
            <th scope="col" class="py-1 pr-3 font-medium">Temperature</th>
            {#each [spring, fall] as on, s (s)}
              {#if on}
                <th scope="col" class={headingClass}>Early <span class="block font-normal">1 year in 10</span></th>
                <th scope="col" class={headingClass}>Typical <span class="block font-normal">half the years</span></th>
                <th scope="col" class={headingClass}>Late <span class="block font-normal">1 year in 10</span></th>
                {#if year !== null}<th scope="col" class={headingClass}>{year}</th>{/if}
              {/if}
            {/each}
            {#if show === 'both'}
              <th scope="col" class="py-1 text-right font-medium">
                Season without it <span class="block font-normal">typical days</span>
              </th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each dates.rows as row, k (row.threshold)}
            {@const own = yearDates?.get(row.fahrenheit)}
            <tr class="border-b border-line/60">
              <th scope="row" class="py-1.5 pr-3 text-left font-normal">
                <span
                  class="mr-1.5 inline-block w-4 border-t-2 align-middle"
                  style:border-color="var({FREEZE_TOKENS[k % FREEZE_TOKENS.length]})"
                  style:border-top-style={FREEZE_DASHES[k % FREEZE_DASHES.length]}
                  aria-hidden="true"
                ></span>
                {thresholdLabel(row.fahrenheit, units)}
              </th>
              {#if spring}
                <td class="py-1.5 pr-3 text-right tabular-nums">{cell(row.lastSpring[10])}</td>
                <td class="py-1.5 pr-3 text-right font-medium tabular-nums">{cell(row.lastSpring[50])}</td>
                <td class="py-1.5 pr-3 text-right tabular-nums">{cell(row.lastSpring[90])}</td>
                {#if year !== null}
                  <td class="py-1.5 pr-3 text-right tabular-nums">
                    {observed.value.status === 'loading' && !own ? '…' : ownDate(own?.spring)}
                  </td>
                {/if}
              {/if}
              {#if fall}
                <td class="py-1.5 pr-3 text-right tabular-nums">{cell(row.firstFall[10])}</td>
                <td class="py-1.5 pr-3 text-right font-medium tabular-nums">{cell(row.firstFall[50])}</td>
                <td class="py-1.5 pr-3 text-right tabular-nums">{cell(row.firstFall[90])}</td>
                {#if year !== null}
                  <td class="py-1.5 pr-3 text-right tabular-nums">
                    {observed.value.status === 'loading' && !own ? '…' : ownDate(own?.fall)}
                  </td>
                {/if}
              {/if}
              {#if show === 'both'}
                <td class="py-1.5 text-right tabular-nums">
                  {row.seasonDays[50] ?? '—'}
                  {#if row.seasonDays[10] != null && row.seasonDays[90] != null}
                    <span class="block text-xs text-ink-muted">{`${row.seasonDays[10]}–${row.seasonDays[90]}`}</span>
                  {/if}
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if frost.value.status === 'loading'}
    <div class="h-32 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}

  {#if odds && dates}
    <ChartCard
      title="Chance of a freeze by date"
      info="In spring, each line gives the share of years with a freeze after the date; in fall, the share with one on or before it. Where a line crosses 50%, half the years had had their freeze. The dashed lines mark 10%, 50% and 90%."
      height="18rem"
      build={(palette) => freezeOddsOption({ chances: odds, show, today, units, palette })}
      {summary}
      table={() => freezeOddsRows(odds, units, undefined, show)}
    />
  {:else if chances.value.status === 'loading'}
    <div class="h-72 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</div>
