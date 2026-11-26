<script lang="ts">
  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import PeriodChoice from '@/lib/climate/PeriodChoice.svelte'
  import type { Period } from '@/lib/climate/periods'
  import { thresholdLabel } from '@/lib/climate/words'
  import { currentUnits } from '@/lib/units'
  import type { LayerInfo } from '@/types/api'

  import { ddLabel, ddParts } from './catalog'
  import {
    type ClimateKind,
    climateKinds,
    FREEZE_MAP_F,
    KIND_LABELS,
    MAP_PERIODS,
    type MapPeriod,
    storedDd,
  } from './climate'
  import { climateOf, countOf, DEFAULT_DD, type ExplorerView, spanFor } from './view'

  // Climate on the map (Phase 7 track 6 step 6.3, D86): "Compare with normal" (Off, Normal, Departure and, where the
  // map is a running total from January 1 that has them, Percentile) with the years the normal comes from, under a
  // map that has normals; and the freeze maps' threshold and years.
  let {
    view,
    layer,
    layers,
    today,
    onchange,
  }: {
    view: ExplorerView
    layer: LayerInfo
    /** Every layer, for the degree-day settings with kept normals */
    layers: LayerInfo[]
    today: string
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const units = $derived(currentUnits())
  const stored = $derived(storedDd(layers))
  const freeze = $derived(layer.group === 'climate')
  const listed = $derived(!freeze && layer.time_axis === 'day' && (layer.climate?.length ?? 0) > 0)
  const span = $derived(spanFor(view, layer))
  const dd = $derived(layer.group === 'degree_days' ? (view.dd ?? DEFAULT_DD) : null)
  const kinds = $derived(
    climateKinds({ layer, span, dd, biofix: view.biofix, count: countOf(view, layer), period: view.period, stored }),
  )
  // Percentile over the 30 or 10 years only: what the kinds would be over those
  const kindsLonger = $derived(
    climateKinds({ layer, span, dd, biofix: view.biofix, count: countOf(view, layer), period: 'last30', stored }),
  )
  const shown = $derived(climateOf(view, layer, { stored }))
  const choice = $derived<ClimateKind | 'off'>(shown ?? 'off')
  const options = $derived(
    (['off', ...kindsLonger] as (ClimateKind | 'off')[]).map((value) => ({
      value,
      label: KIND_LABELS[value],
      disabled: value !== 'off' && !kinds.includes(value),
    })),
  )
  const periods = $derived<readonly Period[]>(
    shown === 'percentile' ? MAP_PERIODS.filter((p) => p !== 'last5') : MAP_PERIODS,
  )

  // Why a map that lists normals can't be compared now
  const why = $derived.by(() => {
    if (!listed || kinds.length) return null
    if (layer.group === 'degree_days' && dd) return `${storedWords(stored)} Choose one of those to compare with normal.`
    return null
  })
  const percentileNote = $derived(
    listed && layer.climate?.includes('percentile') && !kindsLonger.includes('percentile')
      ? 'Percentiles are kept for totals since January 1 of precipitation and of modified 50 to 86 °F and single sine 41 to 86 °F degree days.'
      : null,
  )

  /** The kept settings in words: single sine from its bases (any two as a base and upper threshold), the rest each */
  function storedWords(settings: readonly string[]): string {
    const sine = settings.map((s) => ddParts(s)).filter((p) => p?.method === 'sine' && p.upper === null)
    const others = settings
      .filter((s) => !s.startsWith('sine_'))
      .map((s) => ddLabel(s).replace(/^./, (c) => c.toLowerCase()))
    const bases = sine.map((p) => p!.base).join(', ')
    const parts = [
      ...(bases ? [`single sine from a base of ${bases} °F, or any two of those as a base and upper threshold`] : []),
      ...others,
    ]
    return `Normals are kept for these degree days: ${parts.join('; ')}.`
  }

  const KIND_WORDS: Record<ClimateKind, string> = {
    normal: 'The map shows the average over the years you choose, for the same days.',
    departure:
      'The map shows how far the days you chose were from the average over the years you choose: above normal is positive.',
    percentile:
      'The map shows where this year’s total ranks among the years you choose: 50 is a typical year, 90 higher than 9 years in 10.',
  }

  function setPeriod(period: Period) {
    onchange({ period: period as MapPeriod })
  }
</script>

{#if freeze}
  <section class="space-y-3 text-sm" aria-labelledby="climate-heading">
    <h2 id="climate-heading" class="text-base font-semibold">Freeze</h2>
    <SegmentedChoice
      legend="Freeze temperature"
      name="climate-threshold"
      showLegend
      options={FREEZE_MAP_F.map((f) => ({ value: String(f), label: thresholdLabel(f, units) }))}
      value={String(view.threshold ?? 32)}
      onchange={(next) => onchange({ threshold: next === '32' ? null : Number(next) })}
    />
    <PeriodChoice value={view.period} {today} onchange={setPeriod} name="climate-period" periods={MAP_PERIODS} />
    <p class="text-xs text-ink-muted">
      Fewer years follow recent change more closely, but one unusual year counts for more.
    </p>
  </section>
{:else if listed}
  <section class="space-y-3 text-sm" aria-labelledby="climate-heading">
    <h2 id="climate-heading" class="text-base font-semibold">Compare with normal</h2>
    <SegmentedChoice
      legend="Compare with normal"
      name="climate-kind"
      {options}
      value={choice}
      onchange={(next) => onchange({ climate: next === 'off' ? null : next })}
    />
    {#if shown}
      <PeriodChoice value={view.period} {today} onchange={setPeriod} name="climate-period" {periods} />
      <p class="text-xs text-ink-muted" data-testid="climate-words">{KIND_WORDS[shown]}</p>
    {/if}
    {#if why}<p class="text-xs text-ink-muted">{why}</p>{/if}
    {#if percentileNote}<p class="text-xs text-ink-muted">{percentileNote}</p>{/if}
  </section>
{/if}
