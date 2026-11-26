<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { apiUrl, get } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { modelOption, modelPanels, modelRun, modelSummary, modelTable, layout } from '@/lib/charts/modelCharts'
  import { currentYear, today as gridToday } from '@/lib/dates'
  import { riskColor } from '@/lib/riskLevels'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { routes } from '@/lib/routes'
  import Failed from '@/lib/sites/Failed.svelte'
  import ModelOptions from '@/lib/sites/ModelOptions.svelte'
  import { decodeChosen, encodeChosen, runParams, settingNames, type Chosen } from '@/lib/sites/modelOptions'
  import ModelTable from '@/lib/sites/ModelTable.svelte'
  import { seasonText } from '@/lib/models/format'
  import { answer, nextMilestone, seasonWords } from '@/lib/sites/modelText'
  import { request } from '@/lib/sites/request.svelte'
  import { coordinates } from '@/lib/sites/text'
  import { effectivePrefs, prefsAt, setPrefs, siteAt } from '@/lib/sites.svelte'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { SiteModelProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  // A model at a site (track 3 step 6; frontend.md, Sites): the answer first (the risk in words and the next
  // milestone), then one chart of stacked grids on a shared time axis (lib/charts/modelCharts), the NEWA-style table of
  // the past week and the forecast, the model's settings, and how to read it. The model's content comes as props
  // (D117); its run from `/models/{id}/run` in metric, converted at display. The settings are the site's preferences
  // once it's saved, else the page's view; the season and the extended forecast are the view (its Share link).
  let { lat, lng, name, model, years }: SiteModelProps = $props()

  const today = $derived(gridToday())
  const thisYear = currentYear()
  const units = $derived(currentUnits())

  const view = viewState({
    year: field(codecs.integer({ min: 2000, max: 2100 }), thisYear),
    projection: field(codecs.boolean, false),
    settings: field(codecs.string, ''),
  })
  onDestroy(() => view.destroy())

  const saved = $derived(siteAt(lat, lng))
  const siteTitle = $derived(saved?.name || name || 'Unsaved location')
  const siteHref = $derived.by(() => {
    const url = routes.site({ lat: String(lat), lng: String(lng) })
    return !saved && name ? `${url}?name=${encodeURIComponent(name)}` : url
  })
  const aboutHref = $derived(routes.model({ model_id: model.id }))

  // The settings: the site's (with its groups' and all sites') once it's saved, else the view's
  const chosen = $derived.by((): Chosen => {
    const names = settingNames(model)
    if (saved) {
      const prefs = effectivePrefs(saved.key)
      const own = { ...prefs.options[model.id] }
      if (model.planting && !own.planting_date && prefs.planting) own.planting_date = prefs.planting
      return Object.fromEntries(Object.entries(own).filter(([n]) => names.includes(n)))
    }
    return Object.fromEntries(Object.entries(decodeChosen($view.settings)).filter(([n]) => names.includes(n)))
  })

  function apply(next: Chosen) {
    if (saved) {
      const options = { ...prefsAt({ kind: 'site', key: saved.key }).options }
      if (Object.keys(next).length) options[model.id] = next
      else delete options[model.id]
      setPrefs({ kind: 'site', key: saved.key }, { options: Object.keys(options).length ? options : null })
    } else {
      view.patch({ settings: encodeChosen(next) })
    }
  }

  const year = $derived(years.includes($view.year) || $view.year === thisYear ? $view.year : thisYear)
  const query = $derived(
    runParams({ model, chosen, year, thisYear, projection: $view.projection && year === thisYear }),
  )
  const params = $derived({ lat, lng, ...query.params })

  const run = request<TableResponse>()
  const requestKey = $derived(JSON.stringify(params))
  function load() {
    const p = untrack(() => params)
    return run.load((signal) => get<TableResponse>(`/models/${model.id}/run`, { ...p, units: 'metric' }, { signal }))
  }
  $effect(() => {
    void requestKey
    untrack(load)
  })
  onDestroy(() => run.cancel())

  const result = $derived(run.value.data ? modelRun(run.value.data) : null)
  const panels = $derived(result ? modelPanels(model, result) : [])
  const said = $derived(result ? answer({ model, run: result, units, today }) : null)
  const next = $derived(result ? nextMilestone({ run: result, today }) : null)
  const levels = $derived(model.risk_levels.length)
  const csvUrl = $derived(
    apiUrl(`/models/${model.id}/run`, { ...params, units: units.system === 'metric' ? 'metric' : 'us', format: 'csv' }),
  )
  const chartHeight = $derived(`${layout(panels).height}px`)
  const projectionShown = $derived(result?.table.days.some((d) => d.kind === 'projection') ?? false)

  function shareUrl() {
    const url = new URL(view.shareUrl())
    const label = saved?.name || name
    if (label) url.searchParams.set('name', label)
    return url.toString()
  }

  const where = $derived.by(() => {
    const items: string[] = []
    const season = seasonWords(model.season)
    if (model.season_opens && model.season) items.push(seasonText(model.season, model.season_opens))
    else items.push(season ? `It runs each year from ${season}.` : 'It runs all year.')
    if (model.region.length)
      items.push(`It was developed for ${model.region.join(', ')}, and gives no output elsewhere.`)
    if (model.trained)
      items.push(
        `It was fitted to ${model.trained.description}, ${model.trained.years[0]}–${model.trained.years[1]}. Elsewhere its timing is less certain.`,
      )
    if (model.crops.length) items.push(`Crops: ${model.crops.join(', ')}.`)
    if (model.susceptible)
      items.push(`The crop is susceptible: ${model.susceptible.charAt(0).toLowerCase()}${model.susceptible.slice(1)}`)
    return items
  })
</script>

<svelte:head>
  <title>{model.name} at {siteTitle} · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <div class="space-y-2">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.sites()} class="underline hover:text-ink">Your sites</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li><a href={siteHref} class="underline hover:text-ink">{siteTitle}</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">{model.name}</li>
      </ol>
    </nav>
    <header class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div class="min-w-0">
        <h1 class="text-2xl font-semibold wrap-break-word sm:text-3xl">{model.name}</h1>
        <p class="text-sm text-ink-muted">
          {`At ${siteTitle} · ${coordinates(lat, lng)}${model.crops.length ? ` · ${model.crops.join(', ')}` : ''}`}
          {#if model.status === 'beta'}<span class="ml-1 rounded-sm border border-line px-1 text-xs">Beta</span>{/if}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-3">
        <a href={aboutHref} class="text-sm text-brand-600 underline hover:text-brand-700">About this model</a>
        <ShareButton url={shareUrl} />
      </div>
    </header>
  </div>

  <!-- The answer -->
  <section aria-labelledby="model-answer" class="rounded-lg border border-line bg-surface-raised p-4">
    <h2 id="model-answer" class="sr-only">The answer</h2>
    {#if said}
      <div class="flex items-start gap-3" aria-live="polite">
        {#if said.level !== null && levels}
          <span
            class="mt-1.5 size-4 shrink-0 rounded-full border border-line"
            style:background-color={riskColor(said.level, levels)}
            aria-hidden="true"
          ></span>
        {/if}
        <div class="space-y-1">
          <p class="text-lg font-semibold">{said.headline}</p>
          {#if said.detail}<p>{said.detail}</p>{/if}
          {#if next}<p>{next}</p>{/if}
        </div>
      </div>
    {:else if run.value.status === 'loading'}
      <div class="h-14 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
    {/if}
    {#if run.value.status === 'failed'}
      <Failed {...run.value} retry={load} />
    {/if}
    {#if result && (result.warnings.length || query.notes.length)}
      <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
        {#each [...query.notes, ...result.warnings] as warning (warning)}<li>{warning}</li>{/each}
      </ul>
    {/if}
    <p class="mt-2 text-xs text-ink-muted">
      A model’s result is guidance from weather data for this location’s 2.5 km grid cell, not a guarantee.
    </p>
  </section>

  <!-- The chart -->
  <section aria-labelledby="model-chart" class="space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="model-chart" class="text-lg font-semibold">The season</h2>
      <div class="flex flex-wrap items-center gap-4 text-sm">
        <label class="flex items-center gap-2">
          <span class="text-ink-muted">Season</span>
          <select
            class="rounded-md border border-line bg-surface px-2 py-1"
            value={String(year)}
            onchange={(event) => view.patch({ year: Number(event.currentTarget.value) })}
          >
            {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
          </select>
        </label>
        {#if year === thisYear}
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              class="size-4 accent-brand-600"
              checked={$view.projection}
              onchange={(event) => view.patch({ projection: event.currentTarget.checked })}
            />
            Extended forecast
          </label>
        {/if}
      </div>
    </div>
    {#if $view.projection && year === thisYear}
      <p class="text-sm text-ink-muted">
        {projectionShown
          ? 'After the forecast, the dashed line is the middle of what past years’ weather would give from here, with the band covering the middle 80 % of those years. It shows what’s likely, not a forecast.'
          : ''}
      </p>
    {/if}
    {#if result && panels.length}
      <div aria-busy={run.value.status === 'loading'}>
        <ChartCard
          title={`${model.name}, ${year}`}
          info="From the top: the risk each day, colored by level (faded when it’s out of season or the crop isn’t susceptible), action windows, crop stages, the model’s results and the weather it reads. The shaded part is the forecast; hollow points are estimated values, and gaps are missing data."
          height={chartHeight}
          build={(palette) => modelOption({ model, run: result, panels, units, palette, today })}
          summary={modelSummary({ model, run: result, units })}
          table={() => modelTable({ model, run: result, panels, units })}
        />
      </div>
    {:else if result}
      <p class="text-sm text-ink-muted">The model has no results to chart for these days.</p>
    {:else if run.value.status === 'loading'}
      <div class="h-96 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
    {/if}
  </section>

  <!-- The table -->
  {#if result}
    <section aria-labelledby="model-table" class="space-y-2">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="model-table" class="text-lg font-semibold">
          {year === thisYear ? 'The past week and the forecast' : `The last week of ${year}`}
        </h2>
        <a href={csvUrl} class="text-sm text-brand-600 underline hover:text-brand-700" download>
          Download the season as CSV
        </a>
      </div>
      <ModelTable {model} run={result} {units} {today} />
    </section>
  {/if}

  <!-- The settings -->
  {#if model.biofix || model.planting || model.options.length}
    <section aria-labelledby="model-settings" class="space-y-2">
      <h2 id="model-settings" class="text-lg font-semibold">Settings for this site</h2>
      <p class="text-sm text-ink-muted">
        {saved
          ? `These settings are kept with ${siteTitle} in this browser.`
          : 'Save this site to keep these settings; until then they apply to this page and its Share link.'}
      </p>
      <ModelOptions
        {model}
        {chosen}
        saved={!!saved}
        resolved={{ biofix: result?.request.biofix ?? null, planting: result?.request.planting ?? null }}
        onapply={apply}
      />
    </section>
  {/if}

  <!-- How to read it -->
  <section aria-labelledby="model-guidance" class="space-y-3">
    <h2 id="model-guidance" class="text-lg font-semibold">How to read it</h2>
    {#if model.guidance_html}
      <!-- Our own Markdown, rendered on the server with raw HTML off (updates.render) -->
      <!-- eslint-disable-next-line svelte/no-at-html-tags -->
      <div class="prose max-w-prose">{@html model.guidance_html}</div>
    {:else}
      <p class="max-w-prose">{model.summary}</p>
    {/if}
    {#if model.risk_criteria}
      <details class="max-w-prose text-sm">
        <summary class="cursor-pointer font-semibold">How the risk levels are set</summary>
        <p class="mt-1">{model.risk_criteria}</p>
      </details>
    {/if}
    <h3 class="font-semibold">Where and when it applies</h3>
    <ul class="max-w-prose list-disc space-y-0.5 pl-5 text-sm">
      {#each where as item (item)}<li>{item}</li>{/each}
    </ul>
    <p class="text-sm">
      <a href={aboutHref} class="text-brand-600 underline hover:text-brand-700">{`About ${model.name}`}</a>
      {', its sources and how it was checked.'}
    </p>
  </section>
</div>
