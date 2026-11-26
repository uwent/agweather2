<script lang="ts" module>
  /** A model's option as `/models/{id}` describes it */
  export type ModelOption = {
    name: string
    label: string
    choices: { value: string; label: string }[]
    default: string
  }
</script>

<script lang="ts">
  import type { LayerInfo } from '@/types/api'

  import { orderedOutputs } from './catalog'
  import type { ExplorerView, Planting } from './view'

  // A model layer's settings (Phase 7 track 2 step 2): what it shows (the risk or stage first), the planting dates
  // a crop's map starts from, and the model's options with their choices and defaults from `/models/{id}`.
  let {
    view,
    layer,
    options,
    onchange,
  }: {
    view: ExplorerView
    layer: LayerInfo
    /** The model's options from `/models/{id}`; empty while it loads */
    options: ModelOption[]
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const outputs = $derived(orderedOutputs(layer.outputs ?? []))
  const output = $derived(
    view.output && outputs.some((o) => o.name === view.output) ? view.output : (layer.outputs?.[0]?.name ?? ''),
  )
  const plantings = $derived(layer.planting ?? [])
  const PLANTING_LABELS: Record<string, string> = {
    early: 'Early planting',
    mid: 'Typical (mid) planting',
    late: 'Late planting',
    none: 'No planting date (the model’s own dates)',
  }
  const shownOptions = $derived(options.filter((o) => layer.options?.includes(o.name)))
  const optionValue = (name: string, fallback: string) =>
    view.opts.find((pair) => pair.startsWith(`${name}:`))?.slice(name.length + 1) ?? fallback

  function setOption(option: ModelOption, value: string) {
    const rest = view.opts.filter((pair) => !pair.startsWith(`${option.name}:`))
    onchange({ opts: value === option.default ? rest : [...rest, `${option.name}:${value}`] })
  }
</script>

<div class="space-y-3 text-sm">
  {#if outputs.length > 1}
    <div class="space-y-1">
      <label for="model-output" class="block font-medium">Show</label>
      <select
        id="model-output"
        class="block w-full rounded-md sm:text-sm"
        value={output}
        onchange={(event) =>
          onchange({
            output: event.currentTarget.value === layer.outputs?.[0]?.name ? null : event.currentTarget.value,
          })}
      >
        {#each outputs as o (o.name)}<option value={o.name}>{o.label}</option>{/each}
      </select>
    </div>
  {/if}
  {#if plantings.length}
    <div class="space-y-1">
      <label for="model-planting" class="block font-medium">Planting date</label>
      <select
        id="model-planting"
        class="block w-full rounded-md sm:text-sm"
        value={view.planting ?? 'mid'}
        onchange={(event) =>
          onchange({ planting: event.currentTarget.value === 'mid' ? null : (event.currentTarget.value as Planting) })}
      >
        {#each plantings as tier (tier)}<option value={tier}>{PLANTING_LABELS[tier] ?? tier}</option>{/each}
      </select>
      <p class="text-xs text-ink-muted">
        Each place's typical planting date for the crop, from satellite records of recent years.
      </p>
    </div>
  {/if}
  {#each shownOptions as option (option.name)}
    <div class="space-y-1">
      <label for="model-option-{option.name}" class="block font-medium">{option.label}</label>
      <select
        id="model-option-{option.name}"
        class="block w-full rounded-md sm:text-sm"
        value={optionValue(option.name, option.default)}
        onchange={(event) => setOption(option, event.currentTarget.value)}
      >
        {#each option.choices as choice (choice.value)}<option value={choice.value}>{choice.label}</option>{/each}
      </select>
    </div>
  {/each}
</div>
