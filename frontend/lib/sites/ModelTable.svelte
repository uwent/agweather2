<script lang="ts">
  import type { SiteModelInfo } from '@/types'

  import { formatValue, riskWords, shownDigits, shownUnit, type ModelRun } from '../charts/modelCharts'
  import { isForecast } from '../charts/kinds'
  import { formatDate } from '../dates'
  import { riskColor } from '../riskLevels'
  import type { Units } from '../units'
  import { allWindowSums, WINDOWS } from '../windowSums'
  import { dailyPair, recentRows } from './modelText'

  // NEWA's table: the past 7 days and the forecast, a row a day, with the model's inputs, its daily value and that
  // value's 2-, 7- and 14-day sums (computed here from the run's rows: lib/windowSums) and season total, and the
  // risk. A missing value shows as a dash; an estimated one is marked, and a sum over missing days says so.
  let { model, run, units, today }: { model: SiteModelInfo; run: ModelRun; units: Units; today: string } = $props()

  const rows = $derived(recentRows(run, today))
  const days = $derived(run.table.days)
  const pair = $derived(dailyPair(model))
  const sums = $derived(pair ? allWindowSums(days, pair.daily) : null)
  const inputs = $derived(model.inputs.filter((q) => days.some((d) => d.values[q.name] != null)))
  const dailyLabel = $derived(pair ? (model.outputs.find((q) => q.name === pair.daily)?.label ?? pair.daily) : '')
  const primary = $derived(
    pair ? null : model.outputs.find((q) => q.name !== 'stage' && days.some((d) => d.values[q.name] != null)),
  )
  const withUnit = (label: string, column: string) => {
    const unit = shownUnit(run.table, units, column)
    return unit ? `${label} (${unit})` : label
  }
  const sumText = (value: number | null, column: string) => {
    if (value === null) return '—'
    const symbol = run.table.units[column]
    const shown = symbol ? (units.toDisplay(symbol, value) ?? value) : value
    const digits = shownDigits(run.table, units, column)
    return shown.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  }
  const levels = $derived(model.risk_levels.length)
  const cell = 'px-2 py-1 text-right whitespace-nowrap tabular-nums'
  const head = 'min-w-20 px-2 py-1 text-right align-bottom font-medium'
</script>

<div class="overflow-x-auto rounded-md border border-line">
  <table class="w-full border-collapse text-sm">
    <caption class="sr-only">
      {`${model.name}: the past 7 days and the forecast, a row a day`}
    </caption>
    <thead class="bg-surface-raised text-xs text-ink-muted">
      <tr>
        <th scope="col" class="px-2 py-1 text-left font-medium">Date</th>
        {#each inputs as q (q.name)}
          <th scope="col" class={head}>{withUnit(q.label, q.name)}</th>
        {/each}
        {#if pair && sums}
          <th scope="col" class={head}>{withUnit(dailyLabel, pair.daily)}</th>
          {#each WINDOWS as n (n)}<th scope="col" class={head}>{`${n}-day total`}</th>{/each}
          <th scope="col" class={head}>Season total</th>
        {:else if primary}
          <th scope="col" class={head}>{withUnit(primary.label, primary.name)}</th>
        {/if}
        {#if run.stage}<th scope="col" class="px-2 py-1 text-left font-medium">Crop stage</th>{/if}
        {#if levels}<th scope="col" class="px-2 py-1 text-left font-medium">Risk</th>{/if}
      </tr>
    </thead>
    <tbody>
      {#each rows as i (i)}
        {@const day = days[i]}
        {@const ahead = isForecast(day) || day.kind === 'projection'}
        <tr class="border-t border-line {ahead ? 'bg-surface-raised' : ''}">
          <th scope="row" class="px-2 py-1 text-left font-normal whitespace-nowrap">
            {formatDate(day.date, { weekday: true })}
            {#if ahead}<span class="text-xs text-ink-muted">
                {day.kind === 'partial' ? ' (today)' : ' (forecast)'}
              </span>{/if}
          </th>
          {#each inputs as q (q.name)}
            <td class={cell}>
              {formatValue(run.table, units, q.name, day).replace(/ .*$/, '')}{day.estimated.has(q.name) &&
              day.values[q.name] != null
                ? '*'
                : ''}
            </td>
          {/each}
          {#if pair && sums}
            <td class={cell}>
              {sumText(day.values[pair.daily] ?? null, pair.daily)}{day.estimated.has(pair.daily) &&
              day.values[pair.daily] != null
                ? '*'
                : ''}
            </td>
            {#each WINDOWS as n (n)}
              {@const sum = sums[n][i]}
              <td class={cell} title={sum.missing ? `${sum.missing} of ${sum.days} days missing` : undefined}>
                {sumText(sum.value, pair.daily)}{sum.missing ? '†' : ''}
              </td>
            {/each}
            <td class={cell}>{sumText(day.values[pair.total] ?? null, pair.total)}</td>
          {:else if primary}
            <td class={cell}>{formatValue(run.table, units, primary.name, day).replace(/ .*$/, '')}</td>
          {/if}
          {#if run.stage}<td class="px-2 py-1">{run.stage[i] ?? '—'}</td>{/if}
          {#if levels}
            <td class="px-2 py-1">
              {#if run.level[i] !== null}
                <span
                  class="mr-1 inline-block size-2.5 rounded-full border border-line align-middle"
                  style:background-color={riskColor(run.level[i], levels)}
                  aria-hidden="true"
                ></span>
              {/if}
              {riskWords(run, i) ?? '—'}
            </td>
          {/if}
        </tr>
      {:else}
        <tr><td class="p-2 text-ink-muted">No days to show yet.</td></tr>
      {/each}
    </tbody>
  </table>
</div>
<p class="mt-1 text-xs text-ink-muted">
  {`Shaded rows are forecast. * An estimated value, filling a gap in the weather data.${pair ? ' † A total over days with missing values, which add nothing to it.' : ''}`}
</p>
