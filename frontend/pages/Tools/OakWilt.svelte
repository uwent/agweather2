<script lang="ts">
  import { onDestroy, untrack } from 'svelte'
  import type { Map as MapLibreMap, Marker } from 'maplibre-gl'

  import { get } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { layout, modelOption, modelPanels, modelRun, modelSummary, modelTable } from '@/lib/charts/modelCharts'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { currentYear, today as gridToday } from '@/lib/dates'
  import DataMap from '@/lib/map/DataMap.svelte'
  import { loadMapLibre } from '@/lib/map/maplibre'
  import { longDate } from '@/lib/models/format'
  import { riskColor } from '@/lib/riskLevels'
  import { routes } from '@/lib/routes'
  import Failed from '@/lib/sites/Failed.svelte'
  import { request } from '@/lib/sites/request.svelte'
  import {
    defaultMapDate,
    DNR_LINKS,
    DNR_PERIODS,
    END,
    flownWords,
    oakWiltAnswer,
    oakWiltWords,
    periodText,
    RESTRICTED_DD_F,
  } from '@/lib/tools/oakWilt'
  // TO BE REPLACED by '@/lib/tools/PlacePicker.svelte' (w7-tools) once it merges: same props
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  // TO BE REPLACED by '@/lib/tools/place' (w7-tools) once it merges: same names
  import { PLACE_FIELDS, placeOf, placeView, type Place } from '@/lib/tools/place'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { OakWiltToolProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  // Oak wilt (Phase 7 track 5, T1 d): whether Wisconsin's restricted period for pruning, wounding and harvesting oaks
  // has begun at a place, in DNR's terms (from 231 degree days, base 41 °F, through July 15), with the model's level
  // beside it; the model's map (click to choose a place), its chart with the 231 and July 15 lines, DNR's calendar
  // periods and links, and the topic's management advice. The run comes from `/models/oak-wilt-vectors/run` in
  // metric, converted at display; before 231 is reached, a second run with the extended forecast says when it's likely.
  let { model, years, management_html }: OakWiltToolProps = $props()

  const today = $derived(gridToday())
  const thisYear = currentYear()
  const units = $derived(currentUnits())

  const view = viewState({
    ...PLACE_FIELDS,
    year: field(codecs.integer({ min: 2000, max: 2100 }), thisYear),
    date: field(codecs.date, null),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))
  const year = $derived(years.includes($view.year) || $view.year === thisYear ? $view.year : thisYear)
  const mapDate = $derived($view.date ?? defaultMapDate(today))

  function pick(next: Place) {
    view.patch(placeView(next))
  }

  // --- The run, and the extended forecast when 231 isn't reached yet

  const params = $derived.by(() => {
    if (!place) return null
    const p: Record<string, string | number> = { lat: place.lat, lng: place.lng }
    if (year < thisYear) Object.assign(p, { start: `${year}-01-01`, end: `${year}-${model.season?.[1] ?? '12-31'}` })
    return p
  })
  const run = request<TableResponse>()
  const projected = request<TableResponse>()
  const runKey = $derived(JSON.stringify(params))
  function load() {
    const p = untrack(() => params)
    if (!p) return
    return run.load((signal) => get<TableResponse>(`/models/${model.id}/run`, { ...p, units: 'metric' }, { signal }))
  }
  $effect(() => {
    void runKey
    untrack(load)
  })
  onDestroy(() => {
    run.cancel()
    projected.cancel()
  })

  const result = $derived(place && run.value.data ? modelRun(run.value.data) : null)
  const answer = $derived(result ? oakWiltAnswer({ run: result, today, year }) : null)

  // Before 231 this season, the forecast may not reach it: past years' weather after it says when it's likely
  const wantsProjection = $derived(answer?.phase === 'before' && answer.start === null && year === thisYear)
  function loadProjection() {
    const p = untrack(() => params)
    if (!p) return
    return projected.load((signal) =>
      get<TableResponse>(`/models/${model.id}/run`, { ...p, units: 'metric', projection: true }, { signal }),
    )
  }
  $effect(() => {
    if (wantsProjection) untrack(loadProjection)
  })
  const projectedResult = $derived(
    wantsProjection && projected.value.status === 'done' && projected.value.data
      ? modelRun(projected.value.data)
      : null,
  )
  const shown = $derived(projectedResult ?? result)
  const shownAnswer = $derived(shown ? oakWiltAnswer({ run: shown, today, year }) : null)
  const words = $derived(shownAnswer ? oakWiltWords(shownAnswer, units) : null)
  const flown = $derived(shownAnswer && shownAnswer.phase !== 'past' ? flownWords(shownAnswer.flown) : null)
  const levels = $derived(model.risk_levels.length)
  const stateCode = $derived(shown?.table.location?.state ?? null)

  // --- The chart, with DNR's 231 degree days and July 15

  const panels = $derived(shown ? modelPanels(model, shown) : [])
  const guides = $derived({
    dates: [{ date: `${year}-${END}`, label: 'July 15' }],
    values: [{ column: 'dd_total', value: RESTRICTED_DD_F / 1.8, label: units.format('degF_day', RESTRICTED_DD_F) }],
  })
  const chartHeight = $derived(`${layout(panels).height}px`)

  // --- The map: a marker at the chosen place

  let map = $state<MapLibreMap>()
  let marker: Marker | undefined
  $effect(() => {
    const [m, p] = [map, place]
    untrack(() => {
      if (!m || !p) {
        marker?.remove()
        marker = undefined
        return
      }
      loadMapLibre().then((maplibre) => {
        marker ??= new maplibre.Marker({ color: '#1f2937' })
        marker.setLngLat([p.lng, p.lat]).addTo(m)
      })
    })
  })
  onDestroy(() => marker?.remove())

  const mapCaption = $derived(
    $view.date || mapDate === today
      ? `The model’s level on ${longDate(mapDate)}.`
      : `Out of season, the map shows April 15, ${mapDate.slice(0, 4)}, when Wisconsin’s north-zone calendar period begins.`,
  )

  const siteHref = $derived(
    place ? routes.siteModel({ lat: String(place.lat), lng: String(place.lng), model_id: model.id }) : null,
  )
</script>

<svelte:head>
  <title>Oak wilt · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <header class="space-y-3">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.tools()} class="underline hover:text-ink">Tools</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">Oak wilt</li>
      </ol>
    </nav>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold sm:text-3xl">Oak wilt: when to avoid wounding oaks</h1>
      <ShareButton url={() => view.shareUrl()} />
    </div>
    <p class="max-w-prose">
      Small sap beetles carry the oak wilt fungus to fresh wounds on oaks in spring and early summer. Wisconsin’s
      Department of Natural Resources (DNR) restricts pruning, wounding and harvesting oaks from the time 231 degree
      days (°F) have built up since January 1 through July 15. Choose a location to see where that period stands there.
    </p>
  </header>

  <section aria-labelledby="oak-place" class="space-y-3">
    <h2 id="oak-place" class="sr-only">Location</h2>
    <PlacePicker {place} onpick={pick} />
  </section>

  {#if place}
    <!-- The answer -->
    <section aria-labelledby="oak-answer" class="rounded-lg border border-line bg-surface-raised p-4">
      <h2 id="oak-answer" class="sr-only">The answer</h2>
      {#if words && shownAnswer}
        <div class="space-y-2" aria-live="polite">
          <p class="text-lg font-semibold">{words.headline}</p>
          {#each words.details as detail (detail)}<p class="max-w-prose">{detail}</p>{/each}
          {#if flown}<p class="max-w-prose">{flown}</p>{/if}
          {#if shownAnswer.label !== null && shownAnswer.phase !== 'past'}
            <p class="flex flex-wrap items-center gap-2 text-sm">
              <span
                class="size-3.5 shrink-0 rounded-full border border-line"
                style:background-color={riskColor(shownAnswer.level, levels)}
                aria-hidden="true"
              ></span>
              <span>
                {`The oak wilt vector model’s level ${shownAnswer.date === today ? 'today' : `on ${longDate(shownAnswer.date ?? today)}`}: `}<strong>
                  {shownAnswer.label}
                </strong>{'. '}
                <a href={routes.model({ model_id: model.id })} class="text-brand-600 underline hover:text-brand-700">
                  How the model sets its levels
                </a>
              </span>
            </p>
          {/if}
        </div>
      {:else if run.value.status === 'loading'}
        <div class="h-16 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
      {/if}
      {#if run.value.status === 'failed'}
        <Failed {...run.value} retry={load} />
      {/if}
      {#if stateCode && stateCode !== 'WI'}
        <p class="mt-2 max-w-prose text-sm">
          This location is outside Wisconsin. The restricted period is Wisconsin’s, and the beetles’ timing was measured
          in Wisconsin oak stands; check your own state’s forestry agency or extension service for its advice.
        </p>
      {/if}
      {#if shown?.warnings.length}
        <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
          {#each shown.warnings as warning (warning)}<li>{warning}</li>{/each}
        </ul>
      {/if}
      <p class="mt-2 text-xs text-ink-muted">
        Degree days are from weather data for this location’s 2.5 km grid cell. They are guidance alongside DNR’s
        guidelines, not a replacement for them.
      </p>
    </section>
  {/if}

  <!-- The map -->
  <section aria-labelledby="oak-map" class="space-y-2">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <h2 id="oak-map" class="text-lg font-semibold">Oak wilt vector flight on the map</h2>
      <label class="flex items-center gap-2 text-sm">
        <span class="text-ink-muted">Date</span>
        <input
          type="date"
          class="rounded-md border border-line bg-surface px-2 py-1"
          min="2016-01-01"
          max={today}
          value={mapDate}
          onchange={(event) => {
            const value = event.currentTarget.value
            if (value) view.patch({ date: value })
          }}
        />
      </label>
    </div>
    <p class="text-sm text-ink-muted">{mapCaption} Click the map to choose a location.</p>
    <DataMap
      bind:map
      layer={model.id}
      time={mapDate}
      label={`Map of ${model.name}, ${longDate(mapDate)}`}
      prefsKey="oak-wilt-map"
      class="h-96 sm:h-112"
      onpick={(p) => pick({ lat: p.lat, lng: p.lng, name: null })}
    />
  </section>

  {#if place}
    <!-- The chart -->
    <section aria-labelledby="oak-chart" class="space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 id="oak-chart" class="text-lg font-semibold">The season</h2>
        <label class="flex items-center gap-2 text-sm">
          <span class="text-ink-muted">Season</span>
          <select
            class="rounded-md border border-line bg-surface px-2 py-1"
            value={String(year)}
            onchange={(event) => view.patch({ year: Number(event.currentTarget.value) })}
          >
            {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
          </select>
        </label>
      </div>
      {#if shown && panels.length}
        <div aria-busy={run.value.status === 'loading'}>
          <ChartCard
            title={`${model.name}, ${year}`}
            info="From the top: the model’s level each day, degree days since January 1 with DNR’s 231 °F·d line, the degree days each day and the temperatures they come from. The dotted line on July 15 ends the restricted period. The shaded part is the forecast; after it, a dashed line shows the middle of what past years’ weather would give."
            height={chartHeight}
            build={(palette) => modelOption({ model, run: shown, panels, units, palette, today, guides })}
            summary={modelSummary({ model, run: shown, units })}
            table={() => modelTable({ model, run: shown, panels, units })}
          />
        </div>
      {:else if run.value.status === 'loading'}
        <div class="h-96 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
      {/if}
      {#if siteHref}
        <p class="text-sm">
          <a href={siteHref} class="text-brand-600 underline hover:text-brand-700">
            See this model at the location
          </a>{', with its table of the past week and the forecast.'}
        </p>
      {/if}
    </section>
  {/if}

  <!-- DNR's rules -->
  <section aria-labelledby="oak-dnr" class="space-y-3">
    <h2 id="oak-dnr" class="text-lg font-semibold">Wisconsin’s restricted periods</h2>
    <p class="max-w-prose">
      DNR’s Oak Harvesting Guidelines restrict harvesting where a stand is in a county with oak wilt or within six miles
      of one. The calendar periods are:
    </p>
    <ul class="max-w-prose list-disc space-y-0.5 pl-5">
      {#each DNR_PERIODS as period (period.zone)}
        <li><span class="font-medium">{period.zone}:</span>{` ${periodText(period)}`}</li>
      {/each}
    </ul>
    <p class="max-w-prose">
      DNR’s degree-day rule, developed with UW–Madison from beetles trapped in Wisconsin, refines when the period
      begins: at 231 degree days (°F, base 41 °F) since January 1, when about 5% of the season’s <i>
        Colopterus truncatus
      </i>
      have flown. In a cold spring that can be days or weeks after the calendar date. It doesn’t change the end on July 15.
      The guidelines also allow exceptions for some stands; read them before you plan a harvest.
    </p>
    <ul class="max-w-prose list-disc space-y-0.5 pl-5">
      <li>
        <a href={DNR_LINKS.guidelines} class="text-brand-600 underline hover:text-brand-700">
          Oak Harvesting Guidelines (PUB-FR-560, PDF)
        </a>
      </li>
      <li>
        <a href={DNR_LINKS.harvestingMap} class="text-brand-600 underline hover:text-brand-700">
          DNR’s map of counties with oak wilt and the zones
        </a>
      </li>
      <li>
        <a href={DNR_LINKS.oakWilt} class="text-brand-600 underline hover:text-brand-700">DNR’s oak wilt page</a>
      </li>
      <li>
        <a href={DNR_LINKS.degreeDayGuide} class="text-brand-600 underline hover:text-brand-700">
          DNR’s guide to the degree-day rule
        </a>
      </li>
    </ul>
  </section>

  <!-- The topic's advice -->
  <section aria-labelledby="oak-guidance" class="space-y-3">
    <h2 id="oak-guidance" class="text-lg font-semibold">Managing oak wilt</h2>
    {#if management_html}
      <!-- Our own Markdown, rendered on the server with raw HTML off (updates.render) -->
      <!-- eslint-disable-next-line svelte/no-at-html-tags -->
      <div class="prose max-w-prose">{@html management_html}</div>
    {/if}
    <p class="text-sm">
      <a href={routes.topic({ topic_id: 'oak-wilt' })} class="text-brand-600 underline hover:text-brand-700">
        Oak wilt
      </a>{': the disease, its beetles and its management, with sources.'}
    </p>
  </section>
</div>
