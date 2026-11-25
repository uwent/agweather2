<script lang="ts">
  import { untrack } from 'svelte'

  import NumberField from '@/lib/components/NumberField.svelte'
  import { currentYear } from '@/lib/dates'
  import type { LayerInfo } from '@/types/api'

  import { DD_METHODS, type DegreeDayPreset, ddParts, ddSetting } from './catalog'
  import { DEFAULT_DD, type ExplorerView } from './view'

  // The degree-day builder (Phase 7 track 2 step 2): a crop's or insect's preset, or a method with a base and an
  // upper threshold, counted from January 1, a biofix, or each place's planting date. Every setting is the
  // `degree_days` layer with `dd` (the API reads its stored totals where they apply); counting from planting is
  // the preset's crop-stage model, whose degree days start at each place's typical planting date.
  let {
    view,
    presets,
    layers,
    onchange,
  }: {
    view: ExplorerView
    presets: DegreeDayPreset[]
    layers: LayerInfo[]
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const fromPlanting = $derived(view.layer !== 'degree_days')
  const setting = $derived(view.dd ?? DEFAULT_DD)
  const parts = $derived(ddParts(setting) ?? { method: 'modified', base: 50, upper: 86 })
  const preset = $derived(
    presets.find((p) =>
      fromPlanting ? p.model === view.layer : p.dd.us === setting && (p.biofix ?? null) === (view.biofix ?? null),
    ) ?? presets.find((p) => p.dd.us === setting),
  )
  const presetId = $derived(preset && (fromPlanting || preset.dd.us === setting) ? preset.id : '')

  // A preset's crop-stage model whose map counts from planting, and its degree-day output
  function plantingLayer(p: DegreeDayPreset | undefined): { layer: LayerInfo; output: string } | null {
    if (!p?.model || p.starts !== 'planting') return null
    const layer = layers.find((l) => l.id === p.model && l.planting?.length)
    const output = layer?.outputs?.find((o) => o.name === 'gdd_total' || o.name === 'dd_total')
    return layer && output ? { layer, output: output.name } : null
  }
  const planting = $derived(plantingLayer(preset))

  const crops = $derived(presets.filter((p) => p.group === 'crop'))
  const insects = $derived(presets.filter((p) => p.group !== 'crop'))

  type From = 'january' | 'biofix' | 'planting'
  const from = $derived<From>(fromPlanting ? 'planting' : view.biofix ? 'biofix' : 'january')

  function pickPreset(id: string) {
    const p = presets.find((p) => p.id === id)
    if (!p) return
    onchange({
      layer: 'degree_days',
      output: null,
      dd: p.dd.us,
      biofix: p.biofix && p.biofix !== '01-01' ? p.biofix : null,
      span: 'season',
    })
  }

  function setParts(changes: Partial<typeof parts>) {
    const next = { ...parts, ...changes }
    if (next.base === null || Number.isNaN(next.base)) return
    onchange({ layer: 'degree_days', output: null, dd: ddSetting(next.method, next.base, next.upper) })
  }

  // The thresholds as typed (in °F, shown in the reader's units), kept in step with the view both ways
  let base = $state<number | null>(untrack(() => parts.base))
  let upper = $state<number | null>(untrack(() => parts.upper))
  $effect(() => {
    const p = parts
    untrack(() => {
      if (p.base !== base) base = p.base
      if (p.upper !== upper) upper = p.upper
    })
  })
  $effect(() => {
    const [b, u] = [base, upper]
    untrack(() => {
      if (b !== null && (b !== parts.base || u !== parts.upper)) setParts({ base: b, upper: u })
    })
  })

  function setFrom(next: From) {
    if (next === 'planting' && planting) {
      onchange({
        layer: planting.layer.id,
        output: planting.output,
        planting: view.planting ?? 'mid',
        dd: setting,
        span: 'day',
      })
    } else if (next === 'biofix') {
      onchange({ layer: 'degree_days', output: null, biofix: view.biofix ?? '04-01', span: 'season' })
    } else {
      onchange({ layer: 'degree_days', output: null, biofix: null, span: fromPlanting ? 'season' : view.span })
    }
  }

  const biofixDay = $derived(
    view.biofix && view.biofix.length === 5 ? `${currentYear()}-${view.biofix}` : (view.biofix ?? ''),
  )
</script>

<div class="space-y-3 text-sm">
  <div class="space-y-1">
    <label for="dd-preset" class="block font-medium">Crop or insect</label>
    <select
      id="dd-preset"
      class="block w-full rounded-md sm:text-sm"
      value={presetId}
      onchange={(event) => pickPreset(event.currentTarget.value)}
    >
      <option value="">Your own setting</option>
      <optgroup label="Crops">
        {#each crops as p (p.id)}<option value={p.id}>{p.label}</option>{/each}
      </optgroup>
      <optgroup label="Insects">
        {#each insects as p (p.id)}<option value={p.id}>{p.label}</option>{/each}
      </optgroup>
    </select>
  </div>

  {#if !fromPlanting}
    <div class="grid grid-cols-2 gap-2">
      <div class="col-span-2 space-y-1">
        <label for="dd-method" class="block font-medium">Method</label>
        <select
          id="dd-method"
          class="block w-full rounded-md sm:text-sm"
          value={parts.method}
          onchange={(event) => setParts({ method: event.currentTarget.value })}
        >
          {#each DD_METHODS as method (method.value)}<option value={method.value}>{method.label}</option>{/each}
        </select>
      </div>
      <NumberField id="dd-base" label="Base" unit="degF" bind:value={base} />
      <NumberField id="dd-upper" label="Upper threshold" optional unit="degF" bind:value={upper} />
    </div>
  {/if}

  <fieldset class="space-y-1">
    <legend class="font-medium">Count from</legend>
    <label class="flex items-center gap-2">
      <input type="radio" name="dd-from" checked={from === 'january'} onchange={() => setFrom('january')} />
      January 1
    </label>
    <label class="flex items-center gap-2">
      <input type="radio" name="dd-from" checked={from === 'biofix'} onchange={() => setFrom('biofix')} />
      A date (biofix)
    </label>
    {#if from === 'biofix'}
      <div class="ml-6">
        <label for="dd-biofix" class="sr-only">Biofix date</label>
        <input
          id="dd-biofix"
          type="date"
          class="rounded-md sm:text-sm"
          value={biofixDay}
          onchange={(event) => event.currentTarget.value && onchange({ biofix: event.currentTarget.value })}
        />
      </div>
    {/if}
    <label class="flex items-center gap-2 {planting ? '' : 'text-ink-muted'}">
      <input
        type="radio"
        name="dd-from"
        checked={from === 'planting'}
        disabled={!planting}
        onchange={() => setFrom('planting')}
      />
      Each place's typical planting date
    </label>
    {#if !planting && from !== 'planting'}
      <p class="ml-6 text-xs text-ink-muted">Choose corn, potato or spring wheat to count from planting.</p>
    {/if}
  </fieldset>
</div>
