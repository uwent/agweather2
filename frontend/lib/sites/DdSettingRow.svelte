<script lang="ts">
  import type { PresetInfo } from '@/types/api'

  import { currentUnits } from '../units'
  import { METHODS, parseSetting, settingText, type Method, type Series } from './degreeDays'

  // One compared setting on the Degree days tab: a preset (crops, then insects) or the reader's own method, base and
  // upper threshold, typed in their units and kept in °F. A preset shows how it's used and its sources.
  let {
    index,
    token,
    series,
    presets,
    removable,
    onchange,
    onremove,
  }: {
    index: number
    token: string
    /** The token resolved, null while the presets load or when it names nothing */
    series: Series | null
    presets: PresetInfo[]
    removable: boolean
    onchange: (token: string) => void
    onremove: () => void
  } = $props()

  const units = $derived(currentUnits())
  const id = $props.id()
  const custom = $derived(!presets.some((p) => p.id === token) && parseSetting(token) !== null)
  const crops = $derived(presets.filter((p) => p.group === 'crop'))
  const insects = $derived(presets.filter((p) => p.group === 'insect'))

  // The own setting's fields as typed, in the reader's units
  let method = $state<Method>('sine')
  let base = $state('')
  let upper = $state('')
  let error = $state('')
  $effect(() => {
    const setting = custom ? parseSetting(token) : null
    if (!setting) return
    method = setting.method
    base = units.input('degF', setting.base, 1)
    upper = setting.upper === null ? '' : units.input('degF', setting.upper, 1)
  })

  function choose(value: string) {
    if (value !== 'custom') return onchange(value)
    // The own setting starts from the one shown
    const from = series?.setting ?? { method: 'modified' as Method, base: 50, upper: 86 }
    onchange(settingText(from))
  }

  function apply(event: SubmitEvent) {
    event.preventDefault()
    const low = units.parse('degF', base)
    const high = units.parse('degF', upper)
    const unit = units.label('degF')
    if (!low.ok || low.value === null) {
      error = `Enter a base temperature in ${unit}, such as '${units.system === 'metric' ? '10' : '50'}'.`
      return
    }
    if (!high.ok) {
      error = `Enter the upper threshold as a number in ${unit}, or leave it blank for none.`
      return
    }
    if (high.value !== null && high.value <= low.value) {
      error = 'The upper threshold must be above the base. Raise it, or leave it blank for none.'
      return
    }
    error = ''
    onchange(settingText({ method, base: low.value, upper: high.value }))
  }

  const tempUnit = $derived(units.label('degF'))
</script>

<fieldset class="space-y-2 rounded-md border border-line p-3">
  <legend class="px-1 text-sm font-medium">Setting {index + 1}</legend>
  <div class="flex flex-wrap items-center gap-2">
    <label for="{id}-preset" class="sr-only">Setting {index + 1}</label>
    <select
      id="{id}-preset"
      class="max-w-full min-w-0 rounded-md border border-line bg-surface px-2 py-1 text-sm"
      value={custom ? 'custom' : token}
      onchange={(event) => choose(event.currentTarget.value)}
    >
      {#if !custom && !presets.some((p) => p.id === token)}<option value={token}>Loading…</option>{/if}
      <optgroup label="Crops">
        {#each crops as preset (preset.id)}<option value={preset.id}>{preset.label}</option>{/each}
      </optgroup>
      <optgroup label="Insects">
        {#each insects as preset (preset.id)}<option value={preset.id}>{preset.label}</option>{/each}
      </optgroup>
      <option value="custom">Your own setting</option>
    </select>
    {#if removable}
      <button
        type="button"
        class="cursor-pointer text-sm text-brand-600 underline hover:text-brand-700"
        aria-label="Remove setting {index + 1}"
        onclick={onremove}
      >
        Remove
      </button>
    {/if}
  </div>

  {#if custom}
    <form class="flex flex-wrap items-end gap-3 text-sm" onsubmit={apply} novalidate>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">Method</span>
        <select class="rounded-md border border-line bg-surface px-2 py-1" bind:value={method}>
          {#each METHODS as m (m.value)}<option value={m.value}>{m.label}</option>{/each}
        </select>
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">Base ({tempUnit})</span>
        <input
          class="w-20 rounded-md border border-line bg-surface px-2 py-1"
          inputmode="decimal"
          bind:value={base}
          aria-invalid={error ? 'true' : undefined}
        />
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">Upper ({tempUnit}, optional)</span>
        <input
          class="w-20 rounded-md border border-line bg-surface px-2 py-1"
          inputmode="decimal"
          bind:value={upper}
          aria-invalid={error ? 'true' : undefined}
        />
      </label>
      <button
        type="submit"
        class="rounded-md border border-line bg-surface-raised px-3 py-1 hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
      >
        Apply
      </button>
      <p class="w-full text-xs text-ink-muted">{METHODS.find((m) => m.value === method)?.description}</p>
      {#if error}<p class="w-full text-sm text-danger-ink" role="alert">{error}</p>{/if}
    </form>
  {:else if series?.preset}
    {@const preset = series.preset}
    <div class="space-y-1 text-xs text-ink-muted">
      <p>
        {`${METHODS.find((m) => m.value === preset.method)?.label ?? preset.method}, base ${units.format('degF', preset.base.us, { digits: units.system === 'metric' ? 1 : 0 })}`}{preset.upper
          ? `, upper ${units.format('degF', preset.upper.us, { digits: units.system === 'metric' ? 1 : 0 })}`
          : ''}. {preset.notes}
      </p>
      {#if preset.citations.length}
        <p>
          {'Sources: '}{#each preset.citations as citation, c (c)}{c ? '; ' : ''}{#if citation.url}<a
                href={citation.url}
                class="underline hover:text-ink"
                rel="noopener"
              >
                {citation.text}
              </a>{:else}{citation.text}{/if}{/each}
        </p>
      {/if}
    </div>
  {/if}
</fieldset>
