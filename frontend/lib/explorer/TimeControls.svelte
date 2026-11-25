<script lang="ts">
  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import { addDays } from '@/lib/dates'
  import type { LayerInfo } from '@/types/api'

  import TimeStepper from './TimeStepper.svelte'
  import {
    dayBounds,
    dayOf,
    type ExplorerView,
    rangeStart,
    seasonStart,
    type Span,
    spanFor,
    spansFor,
    type Stat,
    statFor,
  } from './view'
  import { formatDay, formatHour } from './words'

  // When the map shows (Phase 7 track 2 step 3): a day, a range of days combined by a statistic, the season to
  // date, or an hour of an hourly layer, within the layer's archive and forecast.
  let {
    view,
    layer,
    today,
    onchange,
  }: {
    view: ExplorerView
    layer: LayerInfo
    today: string
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const spans = $derived(spansFor(layer))
  const span = $derived(spanFor(view, layer))
  const bounds = $derived(dayBounds(layer))
  const day = $derived(dayOf(view, layer) ?? today)
  const hour = $derived(view.hour ?? layer.range.last?.slice(0, 13) ?? '')

  const SPAN_LABELS: Record<Span, string> = {
    day: 'Day',
    hour: 'Hour',
    range: 'Range',
    season: 'Season to date',
  }
  const STAT_LABELS: Record<Stat, string> = { sum: 'Total', mean: 'Average', min: 'Lowest', max: 'Highest' }
  const stats = $derived((layer.group === 'degree_days' ? ['sum', 'mean', 'min', 'max'] : layer.stats) as Stat[])
  const QUICK = [7, 14, 30]

  // An hour typed as a CST date and clock hour, kept in UTC
  const cstDate = $derived(hour ? new Date(Date.parse(`${hour}:00:00Z`) - 6 * 3600_000).toISOString() : '')
  function setHour(date: string, clock: number) {
    const at = Date.parse(`${date}T00:00:00Z`) + (clock + 6) * 3600_000
    onchange({ hour: new Date(at).toISOString().slice(0, 13) })
  }
  const hourChoices = Array.from({ length: 24 }, (_, h) => ({
    value: h,
    label: formatHour(`2026-01-01T${String((h + 6) % 24).padStart(2, '0')}`, false),
  }))
</script>

<section class="space-y-3" aria-labelledby="time-heading">
  <h2 id="time-heading" class="text-base font-semibold">When</h2>

  {#if spans.length > 1}
    <SegmentedChoice
      legend="Time span"
      name="time-span"
      options={spans.map((s) => ({ value: s, label: SPAN_LABELS[s] }))}
      value={span ?? spans[0]}
      onchange={(next) => onchange({ span: next })}
    />
  {/if}

  {#if span === 'hour'}
    <div class="flex flex-wrap items-end gap-2 text-sm">
      <div class="space-y-1">
        <label for="time-hour-date" class="block font-medium">Date</label>
        <input
          id="time-hour-date"
          type="date"
          class="rounded-md sm:text-sm"
          value={cstDate.slice(0, 10)}
          min={bounds.first ?? undefined}
          max={bounds.last ?? undefined}
          onchange={(event) =>
            event.currentTarget.value && setHour(event.currentTarget.value, Number(cstDate.slice(11, 13)))}
        />
      </div>
      <div class="space-y-1">
        <label for="time-hour" class="block font-medium">Hour</label>
        <select
          id="time-hour"
          class="rounded-md sm:text-sm"
          value={Number(cstDate.slice(11, 13))}
          onchange={(event) => setHour(cstDate.slice(0, 10), Number(event.currentTarget.value))}
        >
          {#each hourChoices as choice (choice.value)}<option value={choice.value}>{choice.label}</option>{/each}
        </select>
      </div>
    </div>
    {#if hour}<TimeStepper {layer} when={hour} {today} onstep={(next) => onchange({ hour: next })} />{/if}
  {:else if span === 'range'}
    {@const start = rangeStart(view, day)}
    <div class="flex flex-wrap items-end gap-2 text-sm">
      <div class="space-y-1">
        <label for="time-start" class="block font-medium">From</label>
        <input
          id="time-start"
          type="date"
          class="rounded-md sm:text-sm"
          value={start}
          min={bounds.first ?? undefined}
          max={day}
          onchange={(event) => event.currentTarget.value && onchange({ start: event.currentTarget.value })}
        />
      </div>
      <div class="space-y-1">
        <label for="time-end" class="block font-medium">Through</label>
        <input
          id="time-end"
          type="date"
          class="rounded-md sm:text-sm"
          value={day}
          min={start}
          max={bounds.last ?? undefined}
          onchange={(event) => event.currentTarget.value && onchange({ date: event.currentTarget.value })}
        />
      </div>
      {#if stats.length}
        <div class="space-y-1">
          <label for="time-stat" class="block font-medium">Combine by</label>
          <select
            id="time-stat"
            class="rounded-md sm:text-sm"
            value={statFor(view, layer)}
            onchange={(event) => onchange({ stat: event.currentTarget.value as Stat })}
          >
            {#each stats as stat (stat)}<option value={stat}>{STAT_LABELS[stat]}</option>{/each}
          </select>
        </div>
      {/if}
    </div>
    <div class="flex flex-wrap gap-2 text-sm" role="group" aria-label="Quick ranges">
      {#each QUICK as days (days)}
        <button
          type="button"
          class="rounded-md border border-line px-2 py-0.5 hover:bg-brand-50"
          onclick={() => onchange({ start: addDays(day, -(days - 1)) })}
        >
          {days} days
        </button>
      {/each}
    </div>
    <TimeStepper
      {layer}
      when={day}
      {today}
      onstep={(next) =>
        onchange({ date: next, start: addDays(next, -Math.round((Date.parse(day) - Date.parse(start)) / 86_400_000)) })}
    />
  {:else if span === 'day' || span === 'season'}
    <div class="flex flex-wrap items-end gap-2 text-sm">
      {#if span === 'season'}
        <p class="w-full text-ink-muted">
          From {formatDay(seasonStart(view, layer, day))} through the day you choose.
        </p>
      {/if}
      <div class="space-y-1">
        <label for="time-day" class="block font-medium">{span === 'season' ? 'Through' : 'Date'}</label>
        <input
          id="time-day"
          type="date"
          class="rounded-md sm:text-sm"
          value={day}
          min={bounds.first ?? undefined}
          max={bounds.last ?? undefined}
          onchange={(event) => event.currentTarget.value && onchange({ date: event.currentTarget.value })}
        />
      </div>
    </div>
    <TimeStepper {layer} when={day} {today} onstep={(next) => onchange({ date: next })} />
  {:else}
    <p class="text-sm text-ink-muted">This map has no date.</p>
  {/if}
</section>
