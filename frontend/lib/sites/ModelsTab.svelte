<script lang="ts">
  import type { SiteCrop, SiteModel } from '@/types'
  import type { TableResponse } from '@/types/api'

  import RiskStrip from '../components/RiskStrip.svelte'
  import { riskColor } from '../riskLevels'
  import { riskSpans, rowsOn, trendWords } from '../riskSpan'
  import { effectivePrefs, siteAt } from '../sites.svelte'
  import { siteKey, siteModelUrl } from '../siteKey'
  import Failed from './Failed.svelte'
  import { modelShown } from './prefs'
  import type { Request } from './request.svelte'
  import { riskRows } from './text'

  // The Models tab: one site across its models, grouped by crop, each with today's risk in words and its sparkline
  // from two weeks back through the forecast (the page's one `/risk` request, shared with Overview), and a link to the
  // model at this site. A saved site shows the crops chosen for it and leaves out the models hidden from it.
  let {
    lat,
    lng,
    today,
    models,
    crops,
    risk,
    loadRisk,
  }: {
    lat: number
    lng: number
    today: string
    models: SiteModel[]
    crops: SiteCrop[]
    risk: Request<TableResponse>
    loadRisk: () => void
  } = $props()

  const key = $derived(siteKey(lat, lng))
  const prefs = $derived(siteAt(lat, lng) ? effectivePrefs(key) : null)
  const shown = $derived(models.filter((m) => modelShown(prefs, m)))
  const today_ = $derived(
    risk.value.data ? new Map(riskRows(rowsOn(risk.value.data, today)).map((r) => [r.model, r])) : null,
  )
  const spans = $derived(risk.value.data ? riskSpans(risk.value.data, today) : null)

  const groups = $derived.by(() => {
    const chosen = prefs?.crops
    const out = crops
      .filter((c) => !chosen || chosen.includes(c.id))
      .map((crop) => ({ id: crop.id, name: crop.name, models: shown.filter((m) => m.crops.includes(crop.id)) }))
      .filter((g) => g.models.length)
    const other = shown.filter((m) => !m.crops.length)
    if (other.length && !chosen) out.push({ id: '', name: 'Other models', models: other })
    return out
  })

  function word(model: SiteModel): string {
    if (!model.risk_levels.length) return model.group === 'crop' ? 'Crop stages' : 'No risk levels'
    const row = today_?.get(model.id)
    if (!today_) return ''
    if (!row || row.inSeason === false) return 'Not in season'
    return row.label ?? 'No level today'
  }
</script>

{#if risk.value.status === 'failed'}
  <Failed {...risk.value} retry={loadRisk} />
{/if}
<p class="mb-4 text-sm text-ink-muted">
  Each model’s risk today, and a strip from two weeks ago through the forecast (shaded). Choose a model to see its
  season, its numbers and its settings for this location.
</p>
<div class="grid gap-6 lg:grid-cols-2">
  {#each groups as group (group.id)}
    <section class="min-w-0" aria-labelledby="crop-{group.id || 'other'}">
      <h2 id="crop-{group.id || 'other'}" class="mb-2 text-base font-semibold">{group.name}</h2>
      <ul class="divide-y divide-line rounded-md border border-line bg-surface-raised">
        {#each group.models as model (model.id)}
          {@const row = today_?.get(model.id)}
          {@const span = spans?.get(model.id)}
          <li class="px-3 py-2 text-sm">
            <div class="flex items-center gap-2">
              <span
                class="size-3 shrink-0 rounded-full border border-line"
                style:background-color={row?.level != null && row.inSeason !== false
                  ? riskColor(row.level, model.risk_levels)
                  : 'transparent'}
                aria-hidden="true"
              ></span>
              <a href={siteModelUrl(key, model.id)} class="min-w-0 flex-1 truncate underline">{model.name}</a>
              <span class="shrink-0 text-right {row?.label ? 'font-medium' : 'text-ink-muted'}">{word(model)}</span>
            </div>
            {#if span && span.days.length > 1 && model.risk_levels.length}
              <RiskStrip
                class="mt-1 w-full pl-5"
                days={span.days}
                levels={model.risk_levels}
                {today}
                label={`${model.name}: ${trendWords(span, today)}.`}
              />
            {/if}
          </li>
        {/each}
      </ul>
    </section>
  {:else}
    <p class="text-sm text-ink-muted">No models for the crops chosen for this site.</p>
  {/each}
</div>
