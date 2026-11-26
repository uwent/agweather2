<!-- WISP 3: app/frontend/lib/components/ForecastStrip.svelte (adapted: rows from lib/tableRows over our API's
     daily columns, in the units the answer gives, converted at display) -->
<script lang="ts">
  import { formatDate } from '../dates'
  import { dayName, skyFor } from '../forecast'
  import type { Day } from '../tableRows'
  import { convert, type Units } from '../units'
  import WeatherIcon from './WeatherIcon.svelte'

  // Days in brief, a card each: the sky in words and as an icon, high and low, precipitation, and reference ET.
  // As many across as fit, so a phone wraps rather than scrolling sideways. label names the list for screen
  // readers. columns: each value's unit symbol (lib/tableRows' Table.units). soFar: today's precipitation added up
  // from its hours (lib/sites/rainSoFar), shown on today's card while the day has no total.
  let {
    days,
    columns,
    units,
    today,
    label,
    soFar = null,
  }: {
    days: Day[]
    columns: Record<string, string>
    units: Units
    today: string
    label: string
    soFar?: { short: string; full: string } | null
  } = $props()

  const value = (day: Day, column: string) => day.values[column] ?? null
  const degrees = (day: Day, column: string) => {
    const symbol = columns[column]
    const shown = symbol ? units.format(symbol, value(day, column), { unit: false }) : '—'
    return shown === '—' ? shown : `${shown}°`
  }
  const amount = (day: Day, column: string) => {
    const symbol = columns[column]
    return symbol ? units.format(symbol, value(day, column)) : '—'
  }
  // The sky is worded from metric values: convert what came in some other unit
  const metricOf = (day: Day, column: string, metric: string) => {
    const symbol = columns[column]
    return symbol ? convert(value(day, column), symbol, metric) : null
  }
  const sky = (day: Day) =>
    skyFor({
      precipitation_mm: metricOf(day, 'precipitation_sum', 'mm'),
      high_c: metricOf(day, 'air_temperature_max', 'degC'),
      cloud_cover_percent: value(day, 'cloud_cover_mean'),
    })
</script>

{#if days.length}
  <ol class="grid grid-cols-[repeat(auto-fill,minmax(5.75rem,1fr))] gap-1.5" aria-label={label}>
    {#each days as day (day.date)}
      {@const words = sky(day)}
      {@const wet = (value(day, 'precipitation_sum') ?? 0) > 0}
      <li
        class="flex flex-col items-center gap-0.5 rounded-md border px-1 py-2 text-center {day.date === today
          ? 'border-brand-600 bg-surface-raised'
          : 'border-line bg-surface-raised'}"
      >
        <span class="text-sm font-medium">
          {dayName(day.date, today)}<span class="sr-only">{`, ${formatDate(day.date)}`}</span>
        </span>
        <span class="text-xs text-ink-muted" aria-hidden="true">{formatDate(day.date)}</span>
        {#if words}
          <WeatherIcon sky={words.sky} class="my-0.5 size-8" />
          <span class="text-xs/tight">{words.label}</span>
        {/if}
        <span class="text-sm">
          <span class="font-semibold"><span class="sr-only">High </span>{degrees(day, 'air_temperature_max')}</span>
          <span class="text-ink-muted"><span class="sr-only">, low </span>{degrees(day, 'air_temperature_min')}</span>
        </span>
        {#if soFar && day.date === today && value(day, 'precipitation_sum') === null}
          <span class="text-xs" title={soFar.full}>
            <span class="sr-only">{`Precipitation ${soFar.full}`}</span>
            <span aria-hidden="true">{soFar.short}</span>
          </span>
        {:else}
          <span class="text-xs {wet ? '' : 'text-ink-muted'}">
            <span class="sr-only">Precipitation </span>{amount(day, 'precipitation_sum')}
          </span>
        {/if}
        <span class="text-xs text-ink-muted">
          <abbr title="Reference evapotranspiration" class="no-underline">ET</abbr>
          {amount(day, 'et0_sum')}
        </span>
      </li>
    {/each}
  </ol>
{:else}
  <p class="text-sm text-ink-muted">No days to show yet for this location.</p>
{/if}
