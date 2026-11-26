<!-- One model across your sites (/sites/models/{id}, track 3 step 9): the model run over every saved site in one
     request (lib/sites/feed.ts), a row per site with its risk from two weeks back through the forecast, today's answer
     and the next milestone, sorted by risk or in your order. The sites live in this browser (D120). -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import RiskStrip from '@/lib/components/RiskStrip.svelte'
  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import { today as gridToday } from '@/lib/dates'
  import { riskColor } from '@/lib/riskLevels'
  import { trendWords } from '@/lib/riskSpan'
  import { routes } from '@/lib/routes'
  import { siteModelUrl } from '@/lib/siteKey'
  import Failed from '@/lib/components/Failed.svelte'
  import { FEED_DAYS_BACK, feedRequests, feedRows, feedWarnings, pointsParam, sortRows } from '@/lib/sites/feed'
  import { request } from '@/lib/request.svelte'
  import StorageNotice from '@/lib/sites/StorageNotice.svelte'
  import { effectivePrefs, siteLabel, sites } from '@/lib/sites.svelte'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { SiteModelFeedProps } from '@/types'
  import type { TableResponse } from '@/types/api'

  let { model }: SiteModelFeedProps = $props()

  const today = $derived(gridToday())
  const units = $derived(currentUnits())
  const levels = $derived(model.risk_levels.length)

  const view = viewState({ sort: field(codecs.oneOf(['risk', 'order'] as const), 'risk') })
  onDestroy(() => view.destroy())

  const requests = $derived(feedRequests({ sites, model, prefsOf: effectivePrefs, today }))
  const answers = request<TableResponse[]>()
  const requestKey = $derived(JSON.stringify(requests.map((r) => [r.params, r.sites.map((s) => s.key)])) + model.id)
  function load() {
    const asked = untrack(() => requests)
    return answers.load((signal) =>
      Promise.all(
        asked.map((r) =>
          get<TableResponse>(
            `/models/${model.id}/run`,
            { ...r.params, points: pointsParam(r.sites), units: 'metric' },
            { signal },
          ),
        ),
      ),
    )
  }
  $effect(() => {
    void requestKey
    if (untrack(() => requests.length)) untrack(load)
  })
  onDestroy(() => answers.cancel())

  const rows = $derived.by(() => {
    const bodies = answers.value.data
    if (!bodies || bodies.length !== requests.length) return null
    try {
      return feedRows({ requests, bodies, order: sites, model, units, today })
    } catch {
      return null
    }
  })
  const sorted = $derived(rows ? sortRows(rows, $view.sort, levels) : [])
  const warnings = $derived(rows ? feedWarnings(requests, answers.value.data ?? []) : [])
</script>

<svelte:head>
  <title>{model.name} at your sites · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <div class="space-y-2">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.sites()} class="underline hover:text-ink">Your sites</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">{model.name}</li>
      </ol>
    </nav>
    <h1 class="text-3xl font-semibold">{model.name} at your sites</h1>
    <p class="max-w-prose text-ink-muted">
      {`Each of your saved sites, from ${FEED_DAYS_BACK} days ago through the forecast. Each site uses its own settings for this model, such as a planting date or biofix, where you’ve set them. `}
      <a href={routes.model({ model_id: model.id })} class="underline hover:text-ink">How this model works</a>
    </p>
  </div>

  <StorageNotice />

  {#if sites.length === 0}
    <div class="max-w-prose space-y-2 rounded-lg border border-dashed border-line p-6">
      <h2 class="text-lg font-semibold">No sites yet</h2>
      <p>
        {'Save the places you follow on '}<a href={routes.sites()} class="underline">
          Your sites
        </a>{', and this page shows the model at each of them.'}
      </p>
    </div>
  {:else}
    <div class="flex flex-wrap items-center justify-between gap-3">
      {#if levels}
        <SegmentedChoice
          legend="Sort"
          name="feed-sort"
          showLegend
          options={[
            { value: 'risk', label: 'Highest risk first' },
            { value: 'order', label: 'Your order' },
          ]}
          value={$view.sort}
          onchange={(sort) => view.patch({ sort })}
        />
        <ul class="flex flex-wrap gap-x-3 gap-y-1 text-xs" aria-label="Risk levels, lowest first">
          {#each model.risk_levels as level, k (level)}
            <li class="flex items-center gap-1.5">
              <span
                class="size-3 shrink-0 rounded-sm border border-line"
                style:background-color={riskColor(k, model.risk_levels)}
                aria-hidden="true"
              ></span>
              {level}
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    {#if answers.value.status === 'failed'}
      <Failed {...answers.value} retry={load} />
    {/if}
    {#if warnings.length}
      <ul class="list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
        {#each warnings as warning (warning)}<li>{warning}</li>{/each}
      </ul>
    {/if}

    {#if rows}
      <ol
        class="divide-y divide-line rounded-lg border border-line"
        aria-label="Your sites"
        aria-busy={answers.value.status === 'loading'}
      >
        {#each sorted as row (row.site.key)}
          <li class="grid gap-x-4 gap-y-1.5 p-3 sm:grid-cols-[minmax(0,12rem)_10rem_minmax(0,1fr)] sm:items-center">
            <div class="min-w-0">
              <a
                href={siteModelUrl(row.site.key, model.id)}
                class="font-medium text-brand-600 underline hover:text-brand-700"
              >
                {siteLabel(row.site)}
              </a>
            </div>
            {#if levels}
              <RiskStrip
                days={row.days}
                levels={model.risk_levels}
                {today}
                label={`${model.name} at ${siteLabel(row.site)}: ${trendWords({ model: model.id, name: model.name, days: row.days }, today)}.`}
                class="w-40"
              />
            {:else}
              <span class="hidden sm:block" aria-hidden="true"></span>
            {/if}
            <div class="min-w-0 text-sm">
              <p class="flex items-start gap-2">
                {#if row.answer.level !== null && levels}
                  <span
                    class="mt-1 size-3 shrink-0 rounded-full border border-line"
                    style:background-color={riskColor(row.answer.level, model.risk_levels)}
                    aria-hidden="true"
                  ></span>
                {/if}
                <span>{row.answer.headline}</span>
              </p>
              {#if row.next}<p class="text-xs text-ink-muted">{row.next}</p>{/if}
            </div>
          </li>
        {/each}
      </ol>
    {:else if answers.value.status === 'loading'}
      <div class="space-y-2" aria-hidden="true">
        {#each sites.slice(0, 5) as site (site.key)}<div
            class="h-14 animate-pulse rounded-md bg-surface-raised"
          ></div>{/each}
      </div>
    {/if}
  {/if}
</div>
