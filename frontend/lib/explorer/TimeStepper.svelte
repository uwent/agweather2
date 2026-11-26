<script lang="ts">
  import type { LayerInfo } from '@/types/api'

  import { monthDayText } from './climate'
  import { stepNoYear } from './timeline'
  import { formatDay, formatHour } from './words'
  import { dayBounds, isForecast, stepDay, stepHour } from './view'

  // Steps the map's day (−7, −1, +1, +7, Today) or hour (−6, −1, +1, +6, Now) within the layer's archive and
  // forecast (Phase 7 track 2 step 3). The page waits 300 ms after the last step before asking for tiles. A layer
  // by day of the year (the chance of a freeze) steps round its year without one: the day shows as "May 1", and
  // December 31 steps on to January 1.
  let {
    layer,
    when,
    today,
    onstep,
  }: {
    layer: LayerInfo
    /** The day (`2026-07-08`) or hour (`2026-07-08T15`, UTC) shown */
    when: string
    /** The grid's today */
    today: string
    onstep: (when: string) => void
  } = $props()

  const hourly = $derived(when.length > 10)
  const noYear = $derived(layer.time_axis === 'day_of_year')
  const steps = $derived(hourly ? [-6, -1, 1, 6] : [-7, -1, 1, 7])
  const unit = $derived(hourly ? 'hour' : 'day')
  const step = (by: number) =>
    hourly ? stepHour(when, by, layer) : noYear ? stepNoYear(when, by) : stepDay(when, by, layer)
  const bounds = $derived(dayBounds(layer))
  const now = $derived.by(() => {
    if (noYear) return `${when.slice(0, 4)}${today.slice(4, 10)}`
    if (!hourly) return stepDay(today, 0, layer)
    const last = layer.range.last?.slice(0, 13)
    return last ?? when
  })
  const label = (by: number) => `${by > 0 ? '+' : '−'}${Math.abs(by)}`
  const name = (by: number) => `${by > 0 ? 'Forward' : 'Back'} ${Math.abs(by)} ${unit}${Math.abs(by) > 1 ? 's' : ''}`
  const atStart = $derived(noYear ? false : hourly ? step(-1) === when : bounds.first !== null && when <= bounds.first)
  const atEnd = $derived(!noYear && step(1) === when)
  const forecast = $derived(!noYear && isForecast(when, layer))
</script>

<div class="flex flex-wrap items-center gap-2">
  <div class="flex overflow-hidden rounded-md border border-line text-sm" role="group" aria-label="Step the {unit}">
    {#each steps as by (by)}
      <button
        type="button"
        class="px-2.5 py-1 tabular-nums not-first:border-l not-first:border-line hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label={name(by)}
        title={name(by)}
        disabled={by < 0 ? atStart : atEnd}
        onclick={() => onstep(step(by))}
      >
        {label(by)}
      </button>
    {/each}
    <button
      type="button"
      class="border-l border-line px-2.5 py-1 font-medium hover:bg-brand-50"
      onclick={() => onstep(now)}
    >
      {hourly ? 'Now' : 'Today'}
    </button>
  </div>
  <p class="text-sm">
    <span class="font-medium">{hourly ? formatHour(when) : noYear ? monthDayText(when) : formatDay(when)}</span>
    {#if forecast}<span
        data-testid="forecast-badge"
        class="ml-1 rounded-sm bg-brand-100 px-1.5 py-0.5 text-xs font-medium text-brand-700"
      >
        Forecast
      </span>{/if}
  </p>
</div>
