<script lang="ts">
  import type { SiteModel } from '@/types'

  import RiskStrip from '../components/RiskStrip.svelte'
  import { trendWords, type ModelRisk } from '../riskSpan'
  import { siteKey, siteModelUrl } from '../siteKey'
  import { riskColor } from '../riskLevels'
  import { plural } from '../words'
  import type { RiskRow } from './text'

  // "Risk now": each model with a risk above the lowest today, in words first ("High risk") with the level's
  // color beside it, highest first; the lowest level's models in one line, so the list leads with what needs
  // attention; then how many have no level today (out of season, or a crop stage model). A model whose days
  // are missing says how many. Each name links to the model at this site; a raised risk has its sparkline from two
  // weeks back through the forecast, with the trend in words.
  let {
    rows,
    models,
    spans = new Map(),
    today = '',
    lat,
    lng,
  }: {
    rows: RiskRow[]
    models: SiteModel[]
    spans?: Map<string, ModelRisk>
    today?: string
    lat: number
    lng: number
  } = $props()

  const key = $derived(siteKey(lat, lng))
  const href = (model: string) => siteModelUrl(key, model)

  const catalog = $derived(new Map(models.map((model) => [model.id, model])))
  const withLevel = $derived(rows.filter((row) => row.level !== null && row.label))
  const raised = $derived(withLevel.filter((row) => row.level! > 0))
  // The lowest level's models by its word (a four-level model's lowest may be named differently)
  const lowestByLabel = $derived.by(() => {
    const lowest = withLevel.filter((row) => row.level === 0)
    const labels = [...new Set(lowest.map((row) => row.label!))]
    return labels.map((label) => [label, lowest.filter((row) => row.label === label)] as const)
  })
  const others = $derived(rows.length - withLevel.length)
  const levels = (row: RiskRow) => catalog.get(row.model)?.risk_levels ?? 5
  const days = (count: number) => plural(count, 'missing day')
</script>

{#if withLevel.length}
  <ul class="divide-y divide-line rounded-md border border-line bg-surface-raised" aria-label="Risk today by model">
    {#each raised as row (row.model)}
      <li class="flex items-start gap-3 px-3 py-2 text-sm">
        <span
          class="mt-1 size-3.5 shrink-0 rounded-full border border-line"
          style:background-color={riskColor(row.level!, levels(row))}
          aria-hidden="true"
        ></span>
        <span class="min-w-0 flex-1">
          <strong class="font-semibold">{`${row.label} risk`}</strong>{': '}<a href={href(row.model)} class="underline">
            {row.name}
          </a>{'.'}
          {#if spans.get(row.model)}<span class="text-ink-muted">
              {` ${trendWords(spans.get(row.model)!, today)}.`}
            </span>{/if}
          {#if row.missingDays}<span class="text-ink-muted">{` Includes ${days(row.missingDays)}.`}</span>{/if}
        </span>
        {#if (spans.get(row.model)?.days.length ?? 0) > 1}
          <RiskStrip
            class="mt-1 w-24 shrink-0 sm:w-40"
            days={spans.get(row.model)!.days}
            levels={levels(row)}
            {today}
            label={`${row.name}, two weeks back through the forecast: ${trendWords(spans.get(row.model)!, today)}.`}
          />
        {/if}
      </li>
    {/each}
    {#each lowestByLabel as [label, group] (label)}
      <li class="flex items-start gap-3 px-3 py-2 text-sm">
        <span
          class="mt-1 size-3.5 shrink-0 rounded-full border border-line"
          style:background-color={riskColor(0, levels(group[0]))}
          aria-hidden="true"
        ></span>
        <span class="min-w-0 flex-1">
          <strong class="font-semibold">{`${label} risk`}</strong>{': '}{#each group as row, k (row.model)}<a
              href={href(row.model)}
              class="underline"
            >
              {row.name}
            </a>{k < group.length - 1 ? ', ' : '.'}{/each}
        </span>
      </li>
    {/each}
  </ul>
{:else}
  <p class="text-sm text-ink-muted">No model gives a risk for this location today.</p>
{/if}
{#if others && withLevel.length}
  <p class="mt-2 text-xs text-ink-muted">
    {`${others} more ${others === 1 ? 'model has' : 'models have'} no risk level today: out of season here, or a crop stage model.`}
  </p>
{/if}
