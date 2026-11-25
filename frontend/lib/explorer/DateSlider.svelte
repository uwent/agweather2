<script lang="ts">
  import {
    bandOf,
    boundaryOf,
    centerOf,
    indexAt,
    indexOf,
    labelPlacement,
    moveBy,
    segmentsOf,
    type Timeline,
    whenAt,
  } from './timeline'

  // The date control's slider (Ben, 2026-11-26, after his alfalfa tool's): a track over a year's days or a week's
  // hours, the observed part plain and the forecast hatched, with the boundary labelled ("Observed through Nov 24",
  // "Forecast"); a range or season shown as a band, the thumb at its last day. Arrow keys move a day (or an hour),
  // Page Up and Page Down a week (6 hours), Home and End to the first and last that can be chosen; a pointer drags.
  let {
    timeline,
    value,
    band = null,
    label,
    observed,
    describe,
    onchange,
  }: {
    timeline: Timeline
    /** The day or hour chosen */
    value: string
    /** A range's or season's first and last day, shown as a band */
    band?: [string, string] | null
    /** The slider's accessible name */
    label: string
    /** The boundary's label: "Observed through Nov 24" */
    observed: string | null
    /** A day or hour in words, for screen readers: "Nov 24, 2026" */
    describe: (when: string) => string
    onchange: (when: string) => void
  } = $props()

  const index = $derived(Math.min(timeline.max, Math.max(timeline.min, indexOf(timeline, value))))
  const segments = $derived(segmentsOf(timeline))
  const boundary = $derived(boundaryOf(timeline))
  const placement = $derived(boundary === null ? null : labelPlacement(boundary))
  const shownBand = $derived(band ? bandOf(timeline, band[0], band[1]) : null)
  const forecast = $derived(index > timeline.observed)
  const bigStep = $derived(timeline.unit === 'day' ? 7 : 6)
  const pct = (at: number) => `${at * 100}%`

  let track: HTMLDivElement | undefined = $state()
  let thumb: HTMLDivElement | undefined = $state()
  let dragging = false

  function choose(next: number) {
    if (next !== index) onchange(whenAt(timeline, next))
  }

  function fromPointer(event: PointerEvent) {
    if (!track) return
    const rect = track.getBoundingClientRect()
    if (rect.width > 0) choose(indexAt(timeline, (event.clientX - rect.left) / rect.width))
  }

  const KEYS: Record<string, (i: number) => number> = {
    ArrowLeft: (i) => moveBy(timeline, i, -1),
    ArrowDown: (i) => moveBy(timeline, i, -1),
    ArrowRight: (i) => moveBy(timeline, i, 1),
    ArrowUp: (i) => moveBy(timeline, i, 1),
    PageDown: (i) => moveBy(timeline, i, -bigStep),
    PageUp: (i) => moveBy(timeline, i, bigStep),
    Home: () => timeline.min,
    End: () => timeline.max,
  }
</script>

<div class="space-y-0.5 select-none" data-testid="date-slider">
  {#if boundary !== null && observed}
    <!-- The boundary's labels, either side of it (or both on the side with room) -->
    <div
      class="grid text-xs/tight"
      style:grid-template-columns="{boundary}fr {1 - boundary}fr"
      aria-hidden="true"
      data-testid="forecast-boundary"
    >
      <span class="pr-1.5 text-right text-ink-muted">
        {#if placement !== 'after'}{observed}{/if}
        {#if placement === 'before'}<span class="font-medium text-ink">{' · Forecast ▸'}</span>{/if}
      </span>
      <span class="pl-1.5 text-left">
        {#if placement === 'after'}<span class="text-ink-muted">{`◂ ${observed} · `}</span>{/if}
        {#if placement !== 'before'}<span class="font-medium">Forecast</span>{/if}
      </span>
    </div>
  {/if}
  <!-- The track takes a pointer; the thumb inside it is the slider a keyboard and screen reader use -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    bind:this={track}
    class="relative h-6 cursor-pointer touch-none"
    onpointerdown={(event) => {
      if (event.button !== 0) return
      dragging = true
      track?.setPointerCapture?.(event.pointerId)
      thumb?.focus()
      fromPointer(event)
    }}
    onpointermove={(event) => dragging && fromPointer(event)}
    onpointerup={() => (dragging = false)}
    onpointercancel={() => (dragging = false)}
  >
    <!-- The window; days that can't be chosen (before the archive, past the forecast) left as an outline -->
    <div class="absolute inset-x-0 top-1/2 h-2.5 -translate-y-1/2 rounded-full border border-line"></div>
    {#if segments.observed}
      <div
        class="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-l-full bg-ink-muted/45"
        style:left={pct(segments.observed[0])}
        style:width={pct(segments.observed[1] - segments.observed[0])}
      ></div>
    {/if}
    {#if segments.forecast}
      <div
        class="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-r-full border border-ink-muted"
        style:left={pct(segments.forecast[0])}
        style:width={pct(segments.forecast[1] - segments.forecast[0])}
        style:background="repeating-linear-gradient(135deg, var(--color-ink-muted) 0 2px, transparent 2px 5px)"
        data-testid="forecast-segment"
      ></div>
    {/if}
    {#if shownBand}
      <div
        class="absolute top-1/2 h-2.5 -translate-y-1/2 bg-brand-600/70"
        style:left={pct(shownBand[0])}
        style:width={pct(shownBand[1] - shownBand[0])}
        data-testid="date-band"
      ></div>
    {/if}
    {#if boundary !== null}
      <div class="absolute top-0 h-full w-0.5 -translate-x-1/2 bg-ink-muted" style:left={pct(boundary)}></div>
    {/if}
    <div
      bind:this={thumb}
      role="slider"
      tabindex="0"
      aria-label={label}
      aria-valuemin={timeline.min}
      aria-valuemax={timeline.max}
      aria-valuenow={index}
      aria-valuetext={`${describe(whenAt(timeline, index))}${forecast ? ', forecast' : ''}`}
      class="absolute top-1/2 size-5 -translate-1/2 rounded-full border-2 border-surface bg-brand-600 shadow-md
        focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      style:left={pct(centerOf(timeline, index))}
      onkeydown={(event) => {
        const move = KEYS[event.key]
        if (!move) return
        event.preventDefault()
        choose(move(index))
      }}
    ></div>
  </div>
  <!-- Months (or days of an hourly layer's week) -->
  <div class="relative h-4 text-[0.6875rem]/4 text-ink-muted" aria-hidden="true">
    {#each timeline.ticks as tick (tick.at)}
      <span
        class={[
          'absolute top-0 border-l border-line pl-0.5 whitespace-nowrap',
          tick.minor && 'max-sm:text-transparent',
        ]}
        style:left={pct(tick.at)}
      >
        {tick.label}
      </span>
    {/each}
  </div>
</div>
