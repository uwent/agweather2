<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { LocateData, PresetsResponse, TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import ChartCard from '../charts/ChartCard.svelte'
  import SegmentedChoice from '../components/SegmentedChoice.svelte'
  import GlossaryText from '../components/GlossaryText.svelte'
  import { downloadCsv, toCsv } from '../csv'
  import { currentYear, formatDate } from '../dates'
  import { currentUnits } from '../units'
  import DdSettingRow from './DdSettingRow.svelte'
  import {
    DD_UNIT,
    MAX_SETTINGS,
    ddCsvRows,
    ddOption,
    ddQuery,
    ddRun,
    ddTable,
    ddWords,
    decodeTokens,
    defaultStart,
    encodeTokens,
    resolveSeries,
    seriesName,
    seriesTotals,
    startWords,
    type CountFrom,
  } from './degreeDays'
  import Failed from './Failed.svelte'
  import { request } from './request.svelte'

  export type DegreeDaysView = {
    /** The settings compared: preset ids or settings (`corn;sine_41_86`) */
    dd: string
    from: CountFrom
    /** The planting date or biofix, YYYY-MM-DD; null for the default */
    since: string | null
    /** The season, a year */
    year: number | null
    projection: boolean
  }

  // A site's Degree days tab (track 3 step 7): see ./degreeDays.ts. The presets come from `/degree-days/presets`
  // once; every setting runs in one `/degree-days` request, in °F (`units=us`, as the settings are named), converted
  // at display. The settings are the page's view (its Share link).
  let {
    lat,
    lng,
    today,
    location,
    planting = null,
    view,
    onchange,
  }: {
    lat: number
    lng: number
    today: string
    location: LocateData | null
    /** The site's saved planting date, if it's saved with one */
    planting?: string | null
    view: DegreeDaysView
    onchange: (changes: Partial<DegreeDaysView>) => void
  } = $props()

  const DEFAULT = 'modified_50_86'
  const units = $derived(currentUnits())
  const thisYear = currentYear()
  const years = Array.from({ length: 11 }, (_, k) => thisYear - k)
  const year = $derived(view.year && years.includes(view.year) ? view.year : thisYear)

  const presets = request<PresetsResponse>()
  presets.load((signal) => get<PresetsResponse>('/degree-days/presets', undefined, { signal }))
  const presetList = $derived(presets.value.data?.data ?? [])

  const tokens = $derived.by(() => {
    const found = decodeTokens(view.dd)
    return found.length ? found : [DEFAULT]
  })
  // A preset's id can't be read until the presets come; a setting can
  const ready = $derived(presets.value.status !== 'loading' || tokens.every((t) => !/^[a-z]+(-[a-z]+)*$/.test(t)))
  const series = $derived(resolveSeries(tokens, presetList))

  const fallback = $derived(
    defaultStart({ from: view.from, series, year, planting: location?.planting ?? null, saved: planting }),
  )
  const start = $derived(
    view.from !== 'jan1' && view.since && view.since.startsWith(`${year}-`) ? view.since : fallback.date,
  )

  const answer = request<TableResponse>()
  const query = $derived(
    ddQuery({ lat, lng, series, start, year, thisYear, projection: view.projection && year === thisYear }),
  )
  const requestKey = $derived(ready && series.length ? JSON.stringify(query) : '')
  function load() {
    const params = untrack(() => query)
    return answer.load((signal) => get<TableResponse>('/degree-days', params, { signal }))
  }
  $effect(() => {
    if (requestKey) untrack(load)
  })
  onDestroy(() => [answer, presets].forEach((r) => r.cancel()))

  const run = $derived(answer.value.data ? ddRun(answer.value.data, series) : null)
  const totals = $derived(run ? seriesTotals(run, today) : [])
  const words = $derived(run ? ddWords({ run, units, today, from: view.from, start }) : '')

  function setToken(k: number, token: string) {
    const next = [...tokens]
    next[k] = token
    onchange({ dd: encodeTokens(next) })
  }
  function remove(k: number) {
    onchange({ dd: encodeTokens(tokens.filter((_, i) => i !== k)) })
  }
  function addSetting() {
    // The next setting not yet shown, starting with common ones
    const next = ['corn', 'sine_50_86', 'average_40', 'sine_41'].find((t) => !tokens.includes(t)) ?? 'sine_45'
    onchange({ dd: encodeTokens([...tokens, next]) })
  }

  function download() {
    if (run) downloadCsv(`agweather-degree-days-${lat},${lng}.csv`, toCsv(ddCsvRows(run, units)))
  }

  const fromOptions = [
    { value: 'jan1' as const, label: 'January 1' },
    { value: 'planting' as const, label: 'Planting date' },
    { value: 'biofix' as const, label: 'Biofix' },
  ]
  const total = (value: number | null | undefined) => units.format(DD_UNIT, value ?? null)
</script>

<div class="space-y-4">
  <GlossaryText
    class="max-w-prose text-sm text-ink-muted"
    paragraphs={[
      'Growing degree days add up the heat above a base temperature from a start date. Compare up to three settings: a crop’s or an insect’s usual one, or your own. Count from January 1, a planting date or a biofix.',
    ]}
  />

  {#if presets.value.status === 'failed'}
    <Failed
      {...presets.value}
      retry={() => presets.load((signal) => get('/degree-days/presets', undefined, { signal }))}
    />
  {/if}

  <div class="grid gap-3 lg:grid-cols-3">
    {#each tokens as token, k (`${k}:${token}`)}
      <DdSettingRow
        index={k}
        {token}
        series={series.find((s) => s.token === token) ?? null}
        presets={presetList}
        removable={tokens.length > 1}
        onchange={(next) => setToken(k, next)}
        onremove={() => remove(k)}
      />
    {/each}
  </div>
  {#if tokens.length < MAX_SETTINGS}
    <button
      type="button"
      class="cursor-pointer rounded-md border border-line bg-surface-raised px-3 py-1 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
      onclick={addSetting}
    >
      Add a setting to compare
    </button>
  {/if}

  <div class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-md border border-line bg-surface-raised p-3">
    <label class="flex items-center gap-2 text-xs">
      <span class="text-ink-muted">Season</span>
      <select
        class="rounded-md border border-line bg-surface px-2 py-1 text-xs"
        value={String(year)}
        onchange={(event) => onchange({ year: Number(event.currentTarget.value) })}
      >
        {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
      </select>
    </label>
    <SegmentedChoice
      legend="Count from"
      name="dd-from"
      showLegend
      options={fromOptions}
      value={view.from}
      onchange={(from) => onchange({ from })}
    />
    {#if view.from !== 'jan1'}
      <label class="flex items-center gap-2 text-xs">
        <span class="text-ink-muted">{view.from === 'planting' ? 'Planting date' : 'Biofix date'}</span>
        <input
          type="date"
          class="rounded-md border border-line bg-surface px-2 py-1 text-xs"
          min="{year}-01-01"
          max="{year}-12-31"
          value={start}
          onchange={(event) => {
            const value = event.currentTarget.value
            if (value) onchange({ since: value })
          }}
        />
      </label>
    {/if}
    {#if year === thisYear}
      <label class="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          class="size-4 accent-brand-600"
          checked={view.projection}
          onchange={(event) => onchange({ projection: event.currentTarget.checked })}
        />
        Project to December 31 from past years’ weather
      </label>
    {/if}
  </div>
  {#if view.from !== 'jan1' && !(view.since && view.since.startsWith(`${year}-`))}
    <p class="text-xs text-ink-muted">
      {fallback.reason
        ? `Starting from ${fallback.reason}, ${formatDate(fallback.date)}. Choose your own date above.`
        : `Starting from ${formatDate(fallback.date)}. Choose your own date above.`}
    </p>
  {/if}

  {#if answer.value.status === 'failed'}
    <Failed {...answer.value} retry={load} />
  {/if}
  {#if answer.value.data && warningsOf(answer.value.data).length}
    <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on this data">
      {#each warningsOf(answer.value.data) as warning (warning)}<li>{warning}</li>{/each}
    </ul>
  {/if}

  {#if run && run.series.length}
    <div class="space-y-4" aria-busy={answer.value.status === 'loading'}>
      <ChartCard
        title="Degree days"
        info="Bars are each day’s degree days; lines below are the running totals. The forecast is shaded. Hollow points and outlined bars are days whose temperatures were estimated across a short gap. With the projection, a dashed line continues the total on the middle of past years’ weather, over the range from the 10th to the 90th percentile."
        height="22rem"
        build={(palette) => ddOption({ run, units, palette, today })}
        summary={words}
        table={() => ddTable(run, units)}
        {download}
      />

      <div class="overflow-x-auto">
        <table class="w-full min-w-lg text-sm">
          <caption class="mb-2 text-left text-sm text-ink-muted">{`${startWords(view.from, start)}.`}</caption>
          <thead>
            <tr class="border-b border-line text-left text-xs text-ink-muted">
              <th scope="col" class="py-1 pr-3 font-medium">Setting</th>
              <th scope="col" class="py-1 pr-3 text-right font-medium">
                {totals[0]?.now ? `Through ${formatDate(totals[0].now.date)}` : 'To date'}
              </th>
              {#if totals[0]?.forecast}
                <th scope="col" class="py-1 pr-3 text-right font-medium">
                  {`By ${formatDate(totals[0].forecast.date)} (forecast)`}
                </th>
              {/if}
              {#if totals[0]?.projected}
                <th scope="col" class="py-1 pr-3 text-right font-medium">
                  {`By ${formatDate(totals[0].projected.date)} (projected)`}
                </th>
              {/if}
              <th scope="col" class="py-1 text-right font-medium">Estimated days</th>
            </tr>
          </thead>
          <tbody>
            {#each totals as t (t.series.dd)}
              <tr class="border-b border-line/60">
                <th scope="row" class="py-1.5 pr-3 text-left font-normal">{seriesName(t.series, units)}</th>
                <td class="py-1.5 pr-3 text-right tabular-nums">{total(t.now?.value)}</td>
                {#if totals[0]?.forecast}<td class="py-1.5 pr-3 text-right tabular-nums">
                    {total(t.forecast?.value)}
                  </td>{/if}
                {#if totals[0]?.projected}
                  <td class="py-1.5 pr-3 text-right tabular-nums">
                    {total(t.projected?.p50)}
                    {#if t.projected?.p10 != null && t.projected?.p90 != null}
                      <span class="block text-xs text-ink-muted">
                        {`likely ${units.format(DD_UNIT, t.projected.p10, { unit: false })}–${units.format(DD_UNIT, t.projected.p90, { unit: false })}`}
                      </span>
                    {/if}
                  </td>
                {/if}
                <td class="py-1.5 text-right tabular-nums">{t.estimated}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {:else if answer.value.status === 'loading' || !ready}
    <div class="h-80 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</div>
