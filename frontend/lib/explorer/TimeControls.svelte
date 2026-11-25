<script lang="ts">
  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import { addDays } from '@/lib/dates'
  import type { LayerInfo } from '@/types/api'

  import DateSlider from './DateSlider.svelte'
  import { dayTimeline, hourTimeline, inYear, isRecent, recentTimeline, yearsOf } from './timeline'
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
    stepTo,
  } from './view'
  import { availableWords, formatDay, formatHour, observedLabel } from './words'

  // When the map shows (Phase 7 track 2 step 3; the date control fleshed out after Ben's alfalfa tool, 2026-11-26):
  // a day, a range of days combined by a statistic, the season to date, or an hour of an hourly layer. The date as
  // typed, the year, a slider over the year's days (an hourly layer's week of hours) with the forecast's part
  // hatched and its boundary labelled, the stepper, and in words what the layer reaches: the archive's first day to
  // the forecast's last.
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
  const years = $derived(yearsOf(layer))
  const observed = $derived(observedLabel(layer))
  const available = $derived(availableWords(layer))

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

  // The band a range or season shows on the slider
  const band = $derived.by((): [string, string] | null => {
    if (span === 'range') return [rangeStart(view, day), day]
    if (span === 'season') return [seasonStart(view, layer, day), day]
    return null
  })
  // Moving the day: a range keeps its length
  const toDay = (next: string) => onchange(stepTo(view, layer, next))

  // The slider's window: the recent weeks and the forecast (the first choice, so the forecast's days have room), or
  // a whole year as the alfalfa tool's; the recent weeks only while the day is in them
  let wantRecent = $state(true)
  const recent = $derived(wantRecent && span !== 'season' && isRecent(day, layer))
  const dayLine = $derived(recent ? recentTimeline(layer) : dayTimeline(layer, day))
  function chooseWindow(choice: string) {
    if (choice === 'recent') {
      wantRecent = true
      if (!isRecent(day, layer) && layer.range.last) toDay(layer.range.last.slice(0, 10))
    } else {
      wantRecent = false
      toDay(inYear(day, Number(choice), layer))
    }
  }
</script>

{#snippet year()}
  {#if years.length > 1}
    <div class="space-y-1">
      <label for="time-year" class="block font-medium">Timeline</label>
      <select
        id="time-year"
        class="rounded-md sm:text-sm"
        value={recent ? 'recent' : day.slice(0, 4)}
        onchange={(event) => chooseWindow(event.currentTarget.value)}
      >
        {#if span !== 'season'}<option value="recent">Recent weeks</option>{/if}
        {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
      </select>
    </div>
  {/if}
{/snippet}

{#snippet slider(timeline: ReturnType<typeof dayTimeline>, value: string, label: string, onslide: (w: string) => void)}
  {#if timeline}
    <DateSlider
      {timeline}
      {value}
      {band}
      {label}
      {observed}
      describe={timeline.unit === 'day' ? formatDay : formatHour}
      onchange={onslide}
    />
  {/if}
{/snippet}

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
    {#if hour}
      {@render slider(hourTimeline(layer, hour), hour, 'Hour on the timeline', (next) => onchange({ hour: next }))}
      <TimeStepper {layer} when={hour} {today} onstep={(next) => onchange({ hour: next })} />
    {/if}
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
      {@render year()}
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
    {@render slider(dayLine, day, 'Last day on the timeline', toDay)}
    <TimeStepper {layer} when={day} {today} onstep={toDay} />
    <div class="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Quick ranges">
      <span class="text-ink-muted">The last</span>
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
      {@render year()}
    </div>
    {@render slider(dayLine, day, span === 'season' ? 'Last day on the timeline' : 'Day on the timeline', toDay)}
    <TimeStepper {layer} when={day} {today} onstep={toDay} />
  {:else}
    <p class="text-sm text-ink-muted">This map has no date.</p>
  {/if}

  {#if span && available}<p class="text-xs text-ink-muted" data-testid="date-reach">{available}</p>{/if}
</section>
