<script lang="ts">
  import { onDestroy, untrack } from 'svelte'
  import type { Map as MapLibreMap, Marker } from 'maplibre-gl'

  import { get } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { layout, modelOption, modelRun, modelSummary, modelTable } from '@/lib/charts/modelCharts'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { today as gridToday } from '@/lib/dates'
  import DataMap from '@/lib/map/DataMap.svelte'
  import { loadMapLibre } from '@/lib/map/maplibre'
  import { riskColor } from '@/lib/riskLevels'
  import { routes } from '@/lib/routes'
  import { placeName } from '@/lib/sites/text'
  import Failed from '@/lib/components/Failed.svelte'
  import { request } from '@/lib/request.svelte'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeView, type Place } from '@/lib/tools/place'
  import {
    beforeMap,
    currentWinter,
    DEPTHS,
    FIRST_WINTER_YEAR,
    depthRows,
    depthText,
    KILLING_F,
    KILLING_HOURS,
    mapWinter,
    potatoAnswer,
    potatoGuides,
    potatoPanels,
    potatoWords,
    seasonOf,
    winterChoices,
    winterCodec,
    winterLabel,
    winterName,
    winterYear,
    withAir,
  } from '@/lib/tools/potatoVolunteer'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { PotatoVolunteerToolProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  // Potato volunteer survival (Phase 7 track 5, P1): the model's map by winter (2016–17 on; click to choose a place)
  // and the place's answer: the hours of soil below 27 °F at 2, 4 and 8 in since November 1 and the chance tubers
  // survive, with a chart of the soil's and the air's lows, the hours at each depth and the risk. A winter's map
  // appears on January 1, so before then the place's count since November 1 sits beside last winter's map. The run
  // comes from `/models/potato-volunteer/run` in metric (converted at display), the air's lows from `/weather/daily`.
  let { model, years, management_html }: PotatoVolunteerToolProps = $props()

  const today = $derived(gridToday())
  const units = $derived(currentUnits())
  const MAP_OUTPUTS = ['risk_level', ...DEPTHS.map((d) => d.column)] as const

  const view = viewState({
    ...PLACE_FIELDS,
    winter: field(winterCodec, null),
    show: field(codecs.oneOf(MAP_OUTPUTS), 'risk_level'),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))
  const winters = $derived(winterChoices(today, Math.min(...years)))
  const winter = $derived(
    $view.winter && (winters as string[]).includes($view.winter) ? $view.winter : currentWinter(today),
  )
  const mapShows = $derived(mapWinter(winter, today))
  const waiting = $derived(beforeMap(winter, today))

  function pick(next: Place) {
    view.patch(placeView(next))
  }

  // --- The run and the air's lows

  const params = $derived(place ? { lat: place.lat, lng: place.lng } : null)
  const run = request<TableResponse>()
  const air = request<TableResponse>()
  const runKey = $derived(JSON.stringify([params, winter]))
  function load() {
    const [p, w] = untrack(() => [params, winter] as const)
    if (!p) return
    const start = `${winterYear(w)}-11-01`
    const end = `${winterYear(w) + 1}-03-31`
    air.load((signal) =>
      get<TableResponse>(
        '/weather/daily',
        { ...p, start, end, vars: 'air_temperature_min', units: 'metric' },
        { signal },
      ),
    )
    return run.load((signal) =>
      get<TableResponse>(`/models/${model.id}/run`, { ...p, season: w, units: 'metric' }, { signal }),
    )
  }
  $effect(() => {
    void runKey
    untrack(load)
  })
  onDestroy(() => {
    run.cancel()
    air.cancel()
  })

  const body = $derived(place && run.value.data ? run.value.data : null)
  const result = $derived(body ? modelRun(body) : null)
  const answer = $derived(result && body ? potatoAnswer({ run: result, season: seasonOf(body), today }) : null)
  const location = $derived(result?.table.location ?? null)
  const where = $derived(place?.name ? `near ${place.name}` : placeName(location) ? `in ${placeName(location)}` : null)
  const words = $derived(answer ? potatoWords(answer, units, where) : null)
  const rows = $derived(answer ? depthRows(answer, units) : [])
  const levels = $derived(model.risk_levels)
  const outside = $derived(!!location?.state && model.region.length > 0 && !model.region.includes(location.state))

  // --- The chart

  const charted = $derived(result ? withAir(result, air.value.status === 'done' ? air.value.data : null) : null)
  const panels = $derived(charted ? potatoPanels(charted, units) : [])
  const guides = $derived(potatoGuides(units))
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

  const mapSettled = $derived(today > `${winterYear(mapShows) + 1}-03-31`)
  const outputLabel = (output: string) => {
    const depth = DEPTHS.find((d) => d.column === output)
    return depth
      ? `Hours below ${units.format('degF', KILLING_F)} at ${depthText(depth, units)}`
      : 'Chance tubers survive'
  }

  const siteHref = $derived(
    place ? routes.siteModel({ lat: String(place.lat), lng: String(place.lng), model_id: model.id }) : null,
  )
</script>

<svelte:head>
  <title>Potato volunteer survival · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <header class="space-y-3">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.tools()} class="underline hover:text-ink">Tools</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">Potato volunteer survival</li>
      </ol>
    </nav>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold sm:text-3xl">Potato volunteer survival</h1>
      <ShareButton url={() => view.shareUrl()} />
    </div>
    <p class="max-w-prose">
      {`Potato tubers left in a field after harvest can survive the winter and come up the next season as volunteers, which can carry late blight, viruses and insect pests into new crops. Tubers die when the soil around them stays below ${units.format('degF', KILLING_F)} for long enough. Choose a location to see how cold the soil has been there this winter, or in any winter since ${winterLabel(winters.at(-1) ?? winterName(FIRST_WINTER_YEAR))}.`}
    </p>
  </header>

  <section aria-labelledby="potato-place" class="space-y-3">
    <h2 id="potato-place" class="sr-only">Location</h2>
    <PlacePicker {place} onpick={pick} />
  </section>

  <div class="flex flex-wrap items-center gap-3">
    <label class="flex items-center gap-2 text-sm">
      <span class="text-ink-muted">Winter</span>
      <select
        class="rounded-md border border-line bg-surface px-2 py-1"
        value={winter}
        onchange={(event) => {
          const value = event.currentTarget.value
          view.patch({ winter: value === currentWinter(today) ? null : value })
        }}
      >
        {#each winters as w (w)}
          <option value={w}>{`${winterLabel(w)}${today <= `${winterYear(w) + 1}-03-31` ? ' (so far)' : ''}`}</option>
        {/each}
      </select>
    </label>
  </div>

  {#if place}
    <!-- The answer -->
    <section aria-labelledby="potato-answer" class="rounded-lg border border-line bg-surface-raised p-4">
      <h2 id="potato-answer" class="sr-only">The answer</h2>
      {#if words && answer}
        <div class="space-y-3" aria-live="polite">
          <p class="flex items-start gap-2 text-lg font-semibold">
            <span
              class="mt-1.5 size-3.5 shrink-0 rounded-full border border-line"
              style:background-color={riskColor(answer.level, levels)}
              aria-hidden="true"
            ></span>
            <span>{words.headline}</span>
          </p>
          {#each words.details as detail (detail)}<p class="max-w-prose">{detail}</p>{/each}
          <table class="text-sm">
            <caption class="sr-only">Hours below {units.format('degF', KILLING_F)} at each depth</caption>
            <thead>
              <tr class="text-left text-ink-muted">
                <th scope="col" class="pr-6 font-normal">Depth</th>
                <th scope="col" class="pr-6 font-normal">
                  {`Hours below ${units.format('degF', KILLING_F)}`}
                </th>
                <th scope="col" class="font-normal">{`Reached ${KILLING_HOURS} hours`}</th>
              </tr>
            </thead>
            <tbody>
              {#each rows as row (row.depth)}
                <tr>
                  <th scope="row" class="pr-6 text-left font-medium">{row.depth}</th>
                  <td class="pr-6 tabular-nums">{row.hours}</td>
                  <td>{row.reached}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else if run.value.status === 'loading'}
        <div class="h-24 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
      {/if}
      {#if run.value.status === 'failed'}
        <Failed {...run.value} retry={load} />
      {/if}
      {#if waiting}
        <p class="mt-3 max-w-prose text-sm">
          {`This winter’s map appears on January 1. Until then, the map below shows last winter, ${winterLabel(mapShows)}, and the numbers here are this winter’s at your location since November 1.`}
        </p>
      {/if}
      {#if outside}
        <p class="mt-2 max-w-prose text-sm">
          This location is outside the area the model was developed for. Check with your own state’s extension service
          before relying on it here.
        </p>
      {/if}
      {#if result?.warnings.length}
        <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
          {#each result.warnings as warning (warning)}<li>{warning}</li>{/each}
        </ul>
      {/if}
      <p class="mt-3 text-xs text-ink-muted">
        Soil temperatures are from weather models for this location’s 2.5 km grid cell, not from sensors in your field.
        They are guidance; scout for volunteers whatever the risk shows.
      </p>
    </section>
  {/if}

  <!-- The map -->
  <section aria-labelledby="potato-map" class="space-y-2">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <h2 id="potato-map" class="text-lg font-semibold">{`Winter ${winterLabel(mapShows)} on the map`}</h2>
      <label class="flex items-center gap-2 text-sm">
        <span class="text-ink-muted">Show</span>
        <select
          class="rounded-md border border-line bg-surface px-2 py-1"
          value={$view.show}
          onchange={(event) => view.patch({ show: event.currentTarget.value as (typeof MAP_OUTPUTS)[number] })}
        >
          {#each MAP_OUTPUTS as output (output)}<option value={output}>{outputLabel(output)}</option>{/each}
        </select>
      </label>
    </div>
    <p class="text-sm text-ink-muted">
      {mapSettled
        ? `Each location’s result for the whole winter, November 1 to March 31.`
        : `Each location’s count so far this winter, since November 1.`}
      {' Click the map to choose a location.'}
    </p>
    <DataMap
      bind:map
      layer={model.id}
      time={mapShows}
      params={$view.show === 'risk_level' ? {} : { output: $view.show }}
      label={`Map of ${model.name}, winter ${winterLabel(mapShows)}: ${outputLabel($view.show)}`}
      prefsKey="potato-volunteer-map"
      class="h-96 sm:h-112"
      onpick={(p) => pick({ lat: p.lat, lng: p.lng, name: null })}
    />
  </section>

  {#if place}
    <!-- The chart -->
    <section aria-labelledby="potato-chart" class="space-y-3">
      <h2 id="potato-chart" class="text-lg font-semibold">
        {`The winter ${answer?.label ?? winterLabel(winter)} at this location`}
      </h2>
      {#if charted && panels.length}
        <div aria-busy={run.value.status === 'loading'}>
          <ChartCard
            title={`${model.name}, winter ${answer?.label ?? winterLabel(winter)}`}
            info={`From the top: the chance tubers survive each day; the hours below ${units.format('degF', KILLING_F)} since November 1 at each depth, with the ${KILLING_HOURS}-hour line that kills tubers there; the soil’s daily low at 2, 4 and 12 in; and the air’s daily low. The dotted lines on the temperatures are ${units.format('degF', 32)} and ${units.format('degF', KILLING_F)}. The shaded part is the forecast.`}
            height={chartHeight}
            build={(palette) => modelOption({ model, run: charted, panels, units, palette, today, guides })}
            summary={modelSummary({ model, run: charted, units })}
            table={() => modelTable({ model, run: charted, panels, units })}
          />
        </div>
      {:else if run.value.status === 'loading'}
        <div class="h-96 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
      {/if}
      {#if air.value.status === 'failed' && result}
        <p class="text-sm text-ink-muted">{`The air’s daily lows couldn’t be loaded: ${air.value.message}`}</p>
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

  <!-- How it works -->
  <section aria-labelledby="potato-how" class="space-y-3">
    <h2 id="potato-how" class="text-lg font-semibold">How the risk is worked out</h2>
    <p class="max-w-prose">
      A rule developed at Michigan State University by Willie Kirk and Phil Wharton counts the hours with soil below 27
      °F from November 1 through March 31. At least 120 hours at a depth kills tubers there. We count three depths, 2, 4
      and 8 inches, as the Wisconsin potato volunteer tool did. The chance that tubers survive starts each winter at
      Very high and falls a level as each depth reaches 120 hours: High after one depth, Moderate after two and Low
      after all three. It never rises again within a winter.
    </p>
    <p class="max-w-prose">
      The count starts on November 1 and ends on March 31, so cold in April doesn’t count. The older Wisconsin tool’s
      map counted from October 1, which makes little difference, since the soil seldom falls below 27 °F in October.
      Snow insulates the soil, so a cold winter with deep snow can still leave tubers alive, while an open winter lets
      the frost go deep.
    </p>
    <p class="max-w-prose">
      Our soil temperatures come from weather models, not from soil sensors. Compared with Wisconet’s stations, they
      count more hours below 27 °F, so our risk may run lower than the stations’ would. A day missing some hours of data
      adds nothing to the counts, which leans the risk higher where data are short.
    </p>
    <p class="text-sm">
      <a href={routes.model({ model_id: model.id })} class="text-brand-600 underline hover:text-brand-700">
        The potato volunteer survival model
      </a>{': its sources, its checks against soil sensors and its versions.'}
    </p>
  </section>

  <!-- The topic's advice -->
  <section aria-labelledby="potato-guidance" class="space-y-3">
    <h2 id="potato-guidance" class="text-lg font-semibold">Managing volunteers</h2>
    {#if management_html}
      <!-- Our own Markdown, rendered on the server with raw HTML off (updates.render) -->
      <!-- eslint-disable-next-line svelte/no-at-html-tags -->
      <div class="prose max-w-prose">{@html management_html}</div>
    {/if}
    <p class="text-sm">
      <a href={routes.topic({ topic_id: 'potato-volunteers' })} class="text-brand-600 underline hover:text-brand-700">
        Potato volunteers
      </a>{': why they matter, how winter weather drives survival and how to manage them, with sources.'}
    </p>
  </section>
</div>
