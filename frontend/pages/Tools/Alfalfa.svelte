<!-- The alfalfa growth and cutting planner (Phase 7 track 5 P1, D129), replacing the UW alfalfa tool's growth and
     timing tabs. "Since the last cut": GDD (41/86 °F) since a cut or since January 1 from `/models/alfalfa-growth/run`
     with `biofix`, extended by past years' weather (`projection=true` to December 31), against the 900–1,100 GDD
     cutting window. "Season plan": `/models/alfalfa-growth/plan`, scheduled by an interval or a number of cuts with
     held cuts kept, or the reader's own dates checked as they are (`cuts=`, `held=`), with the fall rule over the
     period's years. Both asked in °F (`units=us`) and converted at display. The Shiny tool's map and weather tabs
     aren't rebuilt here: the map explorer and the site page's Climate tab cover them (Ben, 2026-11-26). -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import PeriodChoice from '@/lib/climate/PeriodChoice.svelte'
  import { temperatureText } from '@/lib/climate/words'
  import { DEFAULT_PERIOD, NORMAL_PERIODS, periodWords, periodYears, type Period } from '@/lib/climate/periods'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { addDays, today as gridToday } from '@/lib/dates'
  import { routes } from '@/lib/routes'
  import Failed from '@/lib/sites/Failed.svelte'
  import { request } from '@/lib/sites/request.svelte'
  import {
    COUNTS,
    cutLine,
    DEFAULT_COUNT,
    editCuts,
    fallWords,
    gddText,
    INTERVAL_F,
    MAX_CUTS,
    parsePlan,
    PLAN_CHART_HEIGHT,
    planOption,
    planQuery,
    planSummary,
    planTable,
    seasonWords,
    sinceCut,
    sinceCutOption,
    sinceCutTable,
    sinceCutWords,
    windowText,
    WINDOW_F,
    type CutEdit,
    type ScheduleBy,
  } from '@/lib/tools/alfalfa'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeView } from '@/lib/tools/place'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { AlfalfaToolProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  let { years: archiveYears }: AlfalfaToolProps = $props()

  const today = $derived(gridToday())
  const thisYear = $derived(Number(today.slice(0, 4)))
  const units = $derived(currentUnits())
  const yearOptions = $derived(archiveYears.includes(thisYear) ? archiveYears : [thisYear, ...archiveYears])

  const view = viewState({
    ...PLACE_FIELDS,
    cut: field(codecs.date, null),
    year: field(codecs.integer({ min: 2000, max: 2100 }), null),
    period: field(codecs.oneOf(NORMAL_PERIODS), DEFAULT_PERIOD),
    by: field(codecs.oneOf(['interval', 'count'] as const), 'interval'),
    target: field(codecs.integer({ min: 1, max: INTERVAL_F.max }), null),
    cuts: field(codecs.list(codecs.date), []),
    held: field(codecs.list(codecs.date), []),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))

  // --- Since the last cut ----------------------------------------------------------------------------------------

  // A cut this year, on or before today; anything else counts from January 1
  const cutDate = $derived($view.cut && $view.cut.startsWith(String(thisYear)) && $view.cut <= today ? $view.cut : null)
  const run = request<TableResponse>()
  const runQuery = $derived(
    place
      ? {
          lat: place.lat,
          lng: place.lng,
          biofix: cutDate ?? undefined,
          projection: true,
          end: `${thisYear}-12-31`,
          units: 'us',
        }
      : null,
  )
  const runKey = $derived(JSON.stringify(runQuery))
  function loadRun() {
    const params = untrack(() => runQuery)
    if (params) return run.load((signal) => get<TableResponse>('/models/alfalfa-growth/run', params, { signal }))
  }
  $effect(() => {
    void runKey
    untrack(loadRun)
  })
  const since = $derived(place && run.value.status === 'done' ? sinceCut(run.value.data, today) : null)
  const sinceWords = $derived(since ? sinceCutWords(since, units) : null)

  function chooseSpring() {
    view.patch({ cut: null })
  }
  function chooseCut() {
    const start = `${thisYear}-01-01`
    const guess = addDays(today, -30)
    view.patch({ cut: guess < start ? start : guess })
  }

  // --- The season plan ---------------------------------------------------------------------------------------------

  const year = $derived($view.year !== null && yearOptions.includes($view.year) ? $view.year : thisYear)
  const period = $derived<Period>($view.period)
  const inYear = (dates: string[]) => dates.filter((d) => d.startsWith(String(year)))
  const cuts = $derived(inYear($view.cuts))
  const held = $derived(inYear($view.held))

  // The schedule's settings as the reader edits them, applied with Apply
  let draftBy = $state<ScheduleBy>('interval')
  let draftInterval = $state<number>(INTERVAL_F.default)
  let draftCount = $state<number>(DEFAULT_COUNT)
  $effect(() => {
    const [by, target] = [$view.by, $view.target]
    untrack(() => {
      draftBy = by
      if (by === 'interval') draftInterval = target ?? INTERVAL_F.default
      else draftCount = target ?? DEFAULT_COUNT
    })
  })
  const intervals = Array.from(
    { length: (INTERVAL_F.max - INTERVAL_F.min) / INTERVAL_F.step + 1 },
    (_, k) => INTERVAL_F.min + k * INTERVAL_F.step,
  )

  const plan = request<TableResponse>()
  const planParams = $derived(
    place
      ? {
          lat: place.lat,
          lng: place.lng,
          ...planQuery({ year, thisYear, period, by: $view.by, target: $view.target, cuts, held }),
        }
      : null,
  )
  const planKey = $derived(JSON.stringify(planParams))
  function loadPlan() {
    const params = untrack(() => planParams)
    if (params) return plan.load((signal) => get<TableResponse>('/models/alfalfa-growth/plan', params, { signal }))
  }
  $effect(() => {
    void planKey
    untrack(loadPlan)
  })
  onDestroy(() => [run, plan].forEach((r) => r.cancel()))

  const planned = $derived(place && plan.value.data ? parsePlan(plan.value.data) : null)
  const planLoading = $derived(plan.value.status === 'loading')
  const fall = $derived(planned ? fallWords(planned, units, thisYear) : null)
  const periodShown = $derived(planned?.years ?? periodYears(period, today))

  function apply() {
    const target = draftBy === 'interval' ? draftInterval : draftCount
    const isDefault = draftBy === 'interval' && target === INTERVAL_F.default
    view.patch({ by: draftBy, target: isDefault ? null : target, cuts: [] })
  }
  function edit(change: CutEdit) {
    if (!planned) return
    const next = editCuts(planned.cuts, change)
    view.patch({ cuts: next.cuts, held: next.held })
  }
  function addCut() {
    if (!planned) return
    // One more cut, scheduled again around the held ones (as the UW tool's Add a cut)
    view.patch({ by: 'count', target: Math.min(MAX_CUTS, planned.cuts.length + 1), cuts: [] })
  }
  function chooseYear(next: number) {
    view.patch({ year: next === thisYear ? null : next, cuts: [], held: [] })
  }

  const siteHref = $derived(place ? routes.site({ lat: String(place.lat), lng: String(place.lng) }) : null)
  const mapHref = $derived(
    `${routes.map()}?${new URLSearchParams({
      layer: 'alfalfa-growth',
      ...(place ? { at: `${Number(place.lat.toFixed(4))},${Number(place.lng.toFixed(4))}` } : {}),
    })
      .toString()
      .replaceAll('%2C', ',')}`,
  )
  // The card's left edge by status (the line under it says which in words)
  const statusClass = (status: string) =>
    status === 'window' ? 'border-l-success' : status === 'late' ? 'border-l-danger' : 'border-l-line'
  const deg = (f: number) => temperatureText(f, units)
</script>

<svelte:head>
  <title>Alfalfa growth and cutting planner · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <header class="space-y-3">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.tools()} class="underline hover:text-ink">Tools</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">Alfalfa cutting planner</li>
      </ol>
    </nav>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold sm:text-3xl">Alfalfa growth and cutting planner</h1>
      {#if place}<ShareButton url={() => view.shareUrl()} />{/if}
    </div>
    <p class="max-w-prose">
      {`Alfalfa’s growth can be tracked with growing degree days (GDD): each day’s warmth above ${deg(41)}, up to ${deg(86)}. A stand is generally ready to cut once ${windowText(WINDOW_F, units)} have built up since spring or the last cut. Choose a location to see how far alfalfa has grown since its last cut and to plan the season’s cuts.`}
    </p>
  </header>

  <section aria-labelledby="alfalfa-place" class="space-y-3">
    <h2 id="alfalfa-place" class="sr-only">Location</h2>
    <PlacePicker {place} onpick={(picked) => view.patch(placeView(picked))} />
  </section>

  {#if place}
    <!-- Since the last cut -->
    <section aria-labelledby="alfalfa-since" class="space-y-4">
      <h2 id="alfalfa-since" class="text-lg font-semibold">Since the last cut</h2>
      <fieldset class="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <legend class="mb-1 font-medium">Count from</legend>
        <label class="flex items-center gap-2">
          <input type="radio" name="alfalfa-from" checked={cutDate === null} onchange={chooseSpring} />
          Spring green-up (January 1)
        </label>
        <div class="flex flex-wrap items-center gap-2">
          <label class="flex items-center gap-2">
            <input type="radio" name="alfalfa-from" checked={cutDate !== null} onchange={chooseCut} />
            The last cut, on
          </label>
          <input
            type="date"
            aria-label="Date of the last cut"
            class="rounded-md border border-line bg-surface px-2 py-1"
            min={`${thisYear}-01-01`}
            max={today}
            value={cutDate ?? ''}
            disabled={cutDate === null}
            onchange={(event) => {
              const value = event.currentTarget.value
              if (value) view.patch({ cut: value })
            }}
          />
        </div>
      </fieldset>

      <div class="rounded-lg border border-line bg-surface-raised p-4">
        <div class="space-y-2" aria-live="polite">
          {#if sinceWords}
            <p class="text-lg font-semibold">{sinceWords.headline}</p>
            {#each sinceWords.details as detail (detail)}<p class="max-w-prose">{detail}</p>{/each}
          {:else if run.value.status === 'loading'}
            <div class="h-12 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
          {/if}
        </div>
        {#if run.value.status === 'failed'}
          <Failed {...run.value} retry={loadRun} />
        {/if}
        {#if since?.warnings.length}
          <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
            {#each since.warnings as warning (warning)}<li>{warning}</li>{/each}
          </ul>
        {/if}
      </div>

      {#if since}
        <div aria-busy={run.value.status === 'loading'}>
          <ChartCard
            title={`GDD since ${cutDate ? 'the cut' : 'January 1'}, ${thisYear}`}
            info={`Growing degree days (base ${deg(41)}, upper ${deg(86)}) since the cut. The band across the chart is the cutting window. The shaded part is the forecast; after it, a dashed line shows the middle of what past years’ weather would give, over the range of 8 years in 10.`}
            height="16rem"
            build={(palette) => sinceCutOption({ since, units, palette, today })}
            summary={sinceWords ? [sinceWords.headline, ...sinceWords.details].join(' ') : ''}
            table={() => sinceCutTable(since, units)}
          />
        </div>
      {:else if run.value.status === 'loading'}
        <div class="h-64 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
      {/if}
    </section>

    <!-- The season plan -->
    <section aria-labelledby="alfalfa-plan" class="space-y-4">
      <h2 id="alfalfa-plan" class="text-lg font-semibold">Season plan</h2>
      <p class="max-w-prose">
        {`Plan the season’s cuts from this year’s weather, then the normal: for each day after the forecast, the average of that day’s degree days over ${periodWords(periodShown)}. Change any date, hold the cuts you’re sure of, and schedule the rest again.`}
      </p>

      <div class="flex flex-wrap items-end gap-x-8 gap-y-4 text-sm">
        <label class="flex flex-col gap-1">
          <span class="font-medium">Year</span>
          <select
            class="rounded-md border border-line bg-surface px-2 py-1"
            value={String(year)}
            onchange={(event) => chooseYear(Number(event.currentTarget.value))}
          >
            {#each yearOptions as y (y)}<option value={String(y)}>{y}</option>{/each}
          </select>
        </label>
        <div class="space-y-1">
          <PeriodChoice value={period} {today} onchange={(p) => view.patch({ period: p })} name="alfalfa-period" />
          <p class="max-w-xs text-xs text-ink-muted">The years the normal and the fall check come from.</p>
        </div>
        <fieldset class="space-y-2">
          <legend class="mb-1 font-medium">Schedule by</legend>
          <div class="flex flex-wrap items-center gap-2">
            <label class="flex items-center gap-2">
              <input
                type="radio"
                name="alfalfa-by"
                value="interval"
                checked={draftBy === 'interval'}
                onchange={() => (draftBy = 'interval')}
              />
              GDD between cuts
            </label>
            <select
              aria-label="GDD between cuts"
              class="rounded-md border border-line bg-surface px-2 py-1"
              value={String(draftInterval)}
              disabled={draftBy !== 'interval'}
              onchange={(event) => (draftInterval = Number(event.currentTarget.value))}
            >
              {#each intervals as gdd (gdd)}<option value={String(gdd)}>{gddText(gdd, units)}</option>{/each}
            </select>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <label class="flex items-center gap-2">
              <input
                type="radio"
                name="alfalfa-by"
                value="count"
                checked={draftBy === 'count'}
                onchange={() => (draftBy = 'count')}
              />
              Number of cuts
            </label>
            <select
              aria-label="Number of cuts"
              class="rounded-md border border-line bg-surface px-2 py-1"
              value={String(draftCount)}
              disabled={draftBy !== 'count'}
              onchange={(event) => (draftCount = Number(event.currentTarget.value))}
            >
              {#each [...new Set([...COUNTS, draftCount])].sort((a, b) => a - b) as n (n)}
                <option value={String(n)}>{n}</option>
              {/each}
            </select>
          </div>
        </fieldset>
        <button
          type="button"
          class="cursor-pointer rounded-md bg-brand-600 px-3 py-1.5 font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 dark:text-surface"
          onclick={apply}
        >
          Apply
        </button>
      </div>
      {#if held.length}
        <p class="text-sm text-ink-muted">Apply keeps held cuts where they are and schedules the rest around them.</p>
      {/if}

      {#if plan.value.status === 'failed'}
        <Failed {...plan.value} retry={loadPlan} />
      {/if}

      {#if planned}
        <div class="space-y-4" aria-busy={planLoading}>
          <p class="max-w-prose text-sm">{seasonWords(planned, units, thisYear)}</p>
          <ol class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Cuts">
            {#each planned.cuts as cut, k (`${k}-${cut.date}`)}
              <li class="rounded-lg border border-l-4 border-line {statusClass(cut.status)} bg-surface-raised p-3">
                <div class="flex items-center justify-between gap-2">
                  <h3 class="font-semibold">{`Cut ${k + 1}`}</h3>
                  <div class="flex items-center gap-1">
                    <button
                      type="button"
                      class="cursor-pointer rounded-md border border-line px-2 py-0.5 text-xs hover:bg-surface aria-pressed:bg-ink aria-pressed:font-medium aria-pressed:text-surface"
                      aria-pressed={cut.held}
                      aria-label={`Hold cut ${k + 1} in place`}
                      title="Hold this date when the rest are scheduled again"
                      onclick={() => edit({ kind: 'hold', index: k })}
                    >
                      {cut.held ? 'Held' : 'Hold'}
                    </button>
                    {#if planned.cuts.length > 1}
                      <button
                        type="button"
                        class="cursor-pointer rounded-md border border-line px-2 py-0.5 text-xs hover:bg-surface"
                        aria-label={`Remove cut ${k + 1}`}
                        onclick={() => edit({ kind: 'remove', index: k })}
                      >
                        Remove
                      </button>
                    {/if}
                  </div>
                </div>
                <input
                  type="date"
                  aria-label={`Cut ${k + 1} date`}
                  class="mt-2 rounded-md border border-line bg-surface px-2 py-1 text-sm"
                  min={`${year}-01-01`}
                  max={`${year}-12-31`}
                  value={cut.date}
                  onchange={(event) => {
                    const value = event.currentTarget.value
                    if (value && value !== cut.date) edit({ kind: 'date', index: k, date: value })
                  }}
                />
                <p class="mt-2 text-sm">{cutLine(planned, k, units)}</p>
              </li>
            {/each}
          </ol>
          {#if !planned.cuts.length}
            <p class="text-sm">This plan has no cuts. Schedule by GDD or a number of cuts and choose Apply.</p>
          {/if}
          {#if planned.cuts.length < MAX_CUTS}
            <button
              type="button"
              class="cursor-pointer rounded-md border border-line px-3 py-1.5 text-sm hover:bg-surface"
              onclick={addCut}
            >
              Add a cut
            </button>
          {/if}

          {#if fall}
            <div class="space-y-2">
              <h3 class="font-semibold">The last cut and winter</h3>
              <p class="max-w-prose text-sm">{fall.rule}</p>
              {#each fall.check as line (line)}<p class="max-w-prose text-sm">{line}</p>{/each}
            </div>
          {/if}

          <ChartCard
            title={`Cutting plan, ${planned.year}`}
            info="Top: growing degree days since the season began or the last cut, falling to zero after each cut (the diamonds; filled ones are held). The band is the cutting window. This year’s weather is solid, the forecast shaded; the dashed line is the normal. Bottom: from January through June, the chance that a killing freeze is still to come after each date; from July through December, the chance that one has come by it."
            height={PLAN_CHART_HEIGHT}
            build={(palette) => planOption({ plan: planned, units, palette, today })}
            summary={planSummary(planned, units, thisYear)}
            table={() => planTable(planned, units)}
          />
          {#if planned.warnings.length}
            <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on this plan">
              {#each planned.warnings as warning (warning)}<li>{warning}</li>{/each}
            </ul>
          {/if}
        </div>
      {:else if planLoading}
        <div class="h-64 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
      {/if}
      <p class="max-w-prose text-xs text-ink-muted">
        A plan is guidance based on weather data and the normal, not a guarantee for any one field or year. Growth also
        depends on the variety, the soil and its moisture, and the stand’s health. Plans are available only inside the
        area we cover.
      </p>
    </section>

    <section aria-labelledby="alfalfa-more" class="space-y-2">
      <h2 id="alfalfa-more" class="text-lg font-semibold">More for this location</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>
          <a href={mapHref} class="text-brand-600 underline hover:text-brand-700">Alfalfa growth on the map</a>
          {', across the region.'}
        </li>
        {#if siteHref}
          <li>
            <a href={`${siteHref}?tab=climate`} class="text-brand-600 underline hover:text-brand-700">
              This location’s climate
            </a>
            {', with degree days, temperatures and freeze dates against the normal.'}
          </li>
        {/if}
      </ul>
    </section>
  {/if}

  <section aria-labelledby="alfalfa-about" class="space-y-2">
    <h2 id="alfalfa-about" class="text-lg font-semibold">About these numbers</h2>
    <p class="max-w-prose">
      {`GDD here are single-sine degree days with a base of ${deg(41)} and an upper threshold of ${deg(86)}, counted from January 1 or from a cut. The cutting window of ${windowText(WINDOW_F, units)} comes from the UW alfalfa cutting tool this planner replaces. The fall rule (under ${gddText(360, units)} or over ${gddText(900, units)} of regrowth before the killing freeze) is from UW–Madison Extension’s guidance on fall cutting.`}
    </p>
    <p class="text-sm">
      <a href={routes.model({ model_id: 'alfalfa-growth' })} class="text-brand-600 underline hover:text-brand-700">
        The alfalfa growth model
      </a>{', with its sources and how we checked it.'}
    </p>
  </section>
</div>
