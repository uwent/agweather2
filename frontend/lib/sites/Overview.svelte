<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import type { SiteModel } from '@/types'
  import type { TableResponse } from '@/types/api'

  import { get, warningsOf } from '../api'
  import { formatHour } from '../charts/kinds'
  import ForecastStrip from '../components/ForecastStrip.svelte'
  import { addDays, formatDate } from '../dates'
  import { isForecast, tableRows, unitSymbol, type Day, type Table } from '../tableRows'
  import { currentUnits } from '../units'
  import Failed from './Failed.svelte'
  import { request } from './request.svelte'
  import RiskList from './RiskList.svelte'
  import { riskRows } from './text'

  // The Overview tab: the past week and the days ahead (ForecastStrip), the latest hour, rain and reference ET
  // over the last 7 days and since January 1, and the risk now from every model in season. Values come in
  // metric (`units=metric`) and are converted at display, so a change of units redraws without a request.
  // latest: the newest observed hour, from the page's request (it also dates the header).
  let {
    lat,
    lng,
    today,
    latest,
    models,
  }: {
    lat: number
    lng: number
    today: string
    latest: { table: Table; day: Day } | null
    models: SiteModel[]
  } = $props()

  const units = $derived(currentUnits())
  const point = $derived({ lat, lng })

  const daily = request<TableResponse>()
  const week = request<TableResponse>()
  const year = request<TableResponse>()
  const risk = request<TableResponse>()

  const yesterday = $derived(addDays(today, -1))
  const january = $derived(`${today.slice(0, 4)}-01-01`)

  const loadDaily = () =>
    daily.load((signal) =>
      get<TableResponse>(
        '/weather/daily',
        {
          ...point,
          start: addDays(today, -7),
          vars: ['air_temperature_max', 'air_temperature_min', 'precipitation_sum', 'et0_sum', 'cloud_cover_mean'],
          units: 'metric',
        },
        { signal },
      ),
    )
  const totals = (start: string) => (signal: AbortSignal) =>
    get<TableResponse>(
      '/weather/totals',
      { ...point, start, end: yesterday, vars: ['precipitation_sum', 'et0_sum'], forecast: false, units: 'metric' },
      { signal },
    )
  const loadWeek = () => week.load(totals(addDays(today, -7)))
  // On January 1 there's no day of the year done yet
  const loadYear = () => (today > january ? year.load(totals(january)) : undefined)
  const loadRisk = () => risk.load((signal) => get<TableResponse>('/risk', { ...point, date: today }, { signal }))

  // Again whenever the point or the day changes, as text: Inertia hands the page equal props again after it
  // mounts, which mustn't refetch. The loads write the state they read, so they run untracked.
  const requestKey = $derived(`${lat},${lng},${today}`)
  $effect(() => {
    void requestKey
    untrack(() => {
      loadDaily()
      loadWeek()
      loadYear()
      loadRisk()
    })
  })
  onDestroy(() => [daily, week, year, risk].forEach((r) => r.cancel()))

  const strip = $derived(daily.value.data ? tableRows(daily.value.data) : null)
  const past = $derived(strip?.days.filter((day) => day.kind === 'observed') ?? [])
  const ahead = $derived(strip?.days.filter((day) => isForecast(day)) ?? [])

  // Every note the answers carry, once, in the API's words
  const warnings = $derived([
    ...new Set([daily, week, year, risk].flatMap((r) => (r.value.data ? warningsOf(r.value.data) : []))),
  ])

  type Total = { amount: number | null; missing: number; estimated: number; days: number }
  function total(body: TableResponse | null, column: string): Total | null {
    if (!body) return null
    const data = body.data as Record<string, (number | null)[]>
    return {
      amount: data[column]?.[0] ?? null,
      missing: data[`${column}_missing_days`]?.[0] ?? 0,
      estimated: data[`${column}_estimated_days`]?.[0] ?? 0,
      days: data.days?.[0] ?? 0,
    }
  }
  function amountText(body: TableResponse | null, column: string): string {
    const t = total(body, column)
    if (!t || !body) return '…'
    return units.format(unitSymbol(body.meta.units[column] ?? 'mm') ?? 'mm', t.amount)
  }
  function noteText(body: TableResponse | null, column: string): string {
    const t = total(body, column)
    if (!t) return ''
    const plural = (n: number) => `${n} ${n === 1 ? 'day' : 'days'}`
    const parts = []
    if (t.estimated) parts.push(`includes ${plural(t.estimated)} estimated`)
    if (t.missing)
      parts.push(`${plural(t.missing)} missing${column === 'precipitation_sum' ? ', counted as no rain' : ''}`)
    return parts.length ? ` (${parts.join('; ')})` : ''
  }

  const hourValue = (column: string) => {
    if (!latest) return '—'
    const symbol = latest.table.units[column]
    const value = latest.day.values[column] ?? null
    return symbol ? units.format(symbol, value) : value === null ? '—' : String(value)
  }
  const hourRows = [
    ['Temperature', 'air_temperature'],
    ['Dew point', 'dew_point'],
    ['Relative humidity', 'relative_humidity'],
    ['Wind', 'wind_speed'],
    ['Precipitation', 'precipitation'],
  ] as const
</script>

<div class="space-y-8">
  <section aria-labelledby="overview-days" class="space-y-3">
    <h2 id="overview-days" class="text-lg font-semibold">The past week and the forecast</h2>
    {#if daily.value.status === 'failed'}
      <Failed {...daily.value} retry={loadDaily} />
    {/if}
    {#if strip}
      <div class="space-y-4">
        <div>
          <h3 class="mb-1.5 text-sm font-medium text-ink-muted">Past 7 days</h3>
          <ForecastStrip days={past} columns={strip.units} {units} {today} label="Weather for the past 7 days" />
        </div>
        <div>
          <h3 class="mb-1.5 text-sm font-medium text-ink-muted">Today and the forecast</h3>
          <ForecastStrip
            days={ahead}
            columns={strip.units}
            {units}
            {today}
            label="Weather for today and the days ahead"
          />
        </div>
      </div>
    {:else if daily.value.status === 'loading'}
      <div class="h-44 animate-pulse rounded-md bg-surface-raised" aria-hidden="true"></div>
    {/if}
  </section>

  <div class="grid gap-8 md:grid-cols-2">
    <section aria-labelledby="overview-latest" class="space-y-2">
      <h2 id="overview-latest" class="text-lg font-semibold">Latest hour</h2>
      {#if latest}
        <p class="text-sm text-ink-muted">
          {`The hour ending ${formatHour(latest.day.date, latest.table.location?.timezone ?? undefined)}.`}
        </p>
        <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
          {#each hourRows as [label, column] (column)}
            <dt class="text-ink-muted">{label}</dt>
            <dd class="font-medium tabular-nums">{hourValue(column)}</dd>
          {/each}
        </dl>
      {:else}
        <p class="text-sm text-ink-muted">No observed hour yet.</p>
      {/if}
    </section>

    <section aria-labelledby="overview-totals" class="space-y-2">
      <h2 id="overview-totals" class="text-lg font-semibold">Rain and evapotranspiration</h2>
      <p class="text-sm text-ink-muted">
        {`Observed days through ${formatDate(yesterday, { year: true })}. Reference evapotranspiration (ET) is the water a well-watered grass would use.`}
      </p>
      {#each [week, year] as r, i (i)}
        {#if r.value.status === 'failed'}
          <Failed {...r.value} retry={i === 0 ? loadWeek : loadYear} />
        {/if}
      {/each}
      <table class="w-full text-sm">
        <caption class="sr-only">Rain and reference evapotranspiration totals</caption>
        <thead class="text-ink-muted">
          <tr>
            <th scope="col" class="py-1 text-left font-medium"><span class="sr-only">Period</span></th>
            <th scope="col" class="py-1 text-right font-medium">Rain</th>
            <th scope="col" class="py-1 text-right font-medium">ET</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line tabular-nums">
          <tr>
            <th scope="row" class="py-1 text-left font-normal">Last 7 days</th>
            <td class="py-1 text-right">{amountText(week.value.data, 'precipitation_sum')}</td>
            <td class="py-1 text-right">{amountText(week.value.data, 'et0_sum')}</td>
          </tr>
          {#if today > january}
            <tr>
              <th scope="row" class="py-1 text-left font-normal">Since January 1</th>
              <td class="py-1 text-right">{amountText(year.value.data, 'precipitation_sum')}</td>
              <td class="py-1 text-right">{amountText(year.value.data, 'et0_sum')}</td>
            </tr>
          {/if}
        </tbody>
      </table>
      {#each [['Last 7 days', week], ['Since January 1', year]] as const as [label, r] (label)}
        {@const notes = [
          noteText(r.value.data, 'precipitation_sum') && `rain${noteText(r.value.data, 'precipitation_sum')}`,
          noteText(r.value.data, 'et0_sum') && `ET${noteText(r.value.data, 'et0_sum')}`,
        ].filter(Boolean)}
        {#if notes.length}<p class="text-xs text-ink-muted">{`${label}: ${notes.join('; ')}.`}</p>{/if}
      {/each}
    </section>
  </div>

  <section aria-labelledby="overview-risk" class="space-y-2">
    <h2 id="overview-risk" class="text-lg font-semibold">Risk now</h2>
    <p class="text-sm text-ink-muted">
      {`Today's risk from each model in season here, from the weather so far and the forecast. Risk is guidance from weather data, not a guarantee.`}
    </p>
    {#if risk.value.status === 'failed'}
      <Failed {...risk.value} retry={loadRisk} />
    {:else if risk.value.data}
      <RiskList rows={riskRows(risk.value.data)} {models} />
    {:else}
      <div class="h-24 animate-pulse rounded-md bg-surface-raised" aria-hidden="true"></div>
    {/if}
  </section>

  {#if warnings.length}
    <section aria-labelledby="overview-notes" class="space-y-1">
      <h2 id="overview-notes" class="text-sm font-semibold">Notes on these numbers</h2>
      <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted">
        {#each warnings as warning (warning)}<li>{warning}</li>{/each}
      </ul>
    </section>
  {/if}
</div>
