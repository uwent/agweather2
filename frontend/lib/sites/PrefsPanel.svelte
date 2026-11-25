<!-- Preferences at one level, all sites, a group or a site (track 3 step 8; F3, F11): the crops and models its sites
     show, a planting date for every model, a group's map layer, and each model's settings. Each choice says where its
     value comes from (set here, a group, all sites or AgWeather's default) and has its own reset; "Reset to my
     defaults" clears the level so it follows the levels above it again. Changes are saved as they're made. -->
<script lang="ts">
  import Button from '@/lib/components/Button.svelte'
  import { formatDate } from '@/lib/dates'
  import { resetPrefs, setPrefs, sitesSnapshot, sitesState, type PrefsLevel } from '@/lib/sites.svelte'
  import type { ModelSettings } from '@/types'

  import {
    explainPrefs,
    hasOwn,
    hiddenPatch,
    inheritanceWords,
    joinWords,
    optionPatch,
    ownPrefs,
    sourceWords,
    toggled,
    type Explained,
  } from './prefs'

  let {
    level,
    models,
    crops,
    settings,
  }: {
    level: PrefsLevel
    /** The models a site can show (the catalog's, without retired ones) */
    models: readonly { id: string; name: string; crops: string[] }[]
    crops: readonly { id: string; name: string }[]
    /** The models that have settings */
    settings: readonly ModelSettings[]
  } = $props()

  const doc = $derived(sitesSnapshot())
  const own = $derived(ownPrefs(doc, level))
  const explained = $derived(explainPrefs(doc, level))
  const readOnly = $derived(sitesState.readOnly)
  const uid = $derived(
    (level.kind === 'all' ? 'all' : level.kind === 'group' ? `g-${level.id}` : `s-${level.key}`).replace(
      /[^\w-]/g,
      '_',
    ),
  )
  const levelWords = $derived(level.kind === 'all' ? 'all sites' : `this ${level.kind}`)

  let status = $state('')
  function done(message: string) {
    status = message
  }

  function change(patch: Parameters<typeof setPrefs>[1], message = 'Saved.') {
    const result = setPrefs(level, patch)
    done(result.ok ? message : result.message)
  }

  // --- Crops and models

  const cropName = (id: string) => crops.find((c) => c.id === id)?.name ?? id
  const modelName = (id: string) =>
    models.find((m) => m.id === id)?.name ?? settings.find((m) => m.id === id)?.name ?? id
  const chosenCrops = $derived(explained.crops.value)
  const shownModels = $derived(
    [...models]
      .filter((m) => !chosenCrops || m.crops.some((c) => chosenCrops.includes(c)))
      .sort((a, b) => a.name.localeCompare(b.name)),
  )
  const hidden = $derived(explained.hiddenModels.value ?? [])

  function line<T>(item: Explained<T>, value: string, none: string): string {
    if (item.value === undefined || (Array.isArray(item.value) && !item.value.length && item.source.kind === 'default'))
      return item.source.kind === 'default' ? none : `${sourceWords(item.source, level)}: ${none}`
    return `${sourceWords(item.source, level)}: ${value}`
  }
  const cropsLine = $derived(
    line(
      explained.crops,
      `${joinWords((chosenCrops ?? []).map(cropName))}.`,
      'no crops chosen, so every model in season and developed for the region shows.',
    ),
  )
  const hiddenLine = $derived(
    line(
      explained.hiddenModels,
      hidden.length ? `${joinWords(hidden.map(modelName))} hidden.` : 'none hidden.',
      'none hidden.',
    ),
  )

  function toggleCrop(id: string, on: boolean) {
    change({ crops: toggled(chosenCrops, id, on) }, on ? `${cropName(id)} added.` : `${cropName(id)} removed.`)
  }

  function toggleModel(id: string, show: boolean) {
    change(
      { hiddenModels: hiddenPatch(explained, id, !show) },
      show ? `${modelName(id)} shown.` : `${modelName(id)} hidden.`,
    )
  }

  // --- Planting date (for every model that takes one) and the map's layer

  const TIERS = [
    { value: 'early', label: 'Early for each site' },
    { value: 'mid', label: 'Typical for each site' },
    { value: 'late', label: 'Late for each site' },
  ]
  const isTier = (value: string | undefined) => TIERS.some((t) => t.value === value)
  const plantingWords = (value: string | undefined) =>
    !value
      ? ''
      : isTier(value)
        ? TIERS.find((t) => t.value === value)!.label.toLowerCase()
        : formatDate(value, { year: true })
  // A date being typed in, before it's whole (the date input's own state)
  let plantingKind = $state<Record<string, string>>({})
  const kindOf = (key: string, value: string | undefined) =>
    plantingKind[key] ?? (!value ? '' : isTier(value) ? value : 'date')

  const layerChoices = $derived(shownModels)

  // --- Model settings

  let editing = $state('')
  const editable = $derived(
    settings.filter((s) => shownModels.some((m) => m.id === s.id)).length
      ? settings.filter((s) => shownModels.some((m) => m.id === s.id))
      : settings,
  )
  const editingModel = $derived(settings.find((s) => s.id === editing) ?? null)
  // Every model with a setting in effect here, set here or followed
  const inEffect = $derived(
    Object.entries(explained.options)
      .map(([model, names]) => ({ model, names: Object.entries(names) }))
      .filter((m) => m.names.length),
  )

  type Field = {
    name: string
    label: string
    date?: boolean
    choices?: { value: string; label: string }[]
    default?: string
  }
  function fieldsOf(model: ModelSettings): Field[] {
    const fields: Field[] = []
    if (model.biofix)
      fields.push({ name: 'biofix', label: `Count from (${model.biofix.label.toLowerCase()})`, date: true })
    if (model.planting) {
      fields.push({ name: 'planting_date', label: `${model.planting.crop} planting date` })
      for (const o of model.planting.options)
        fields.push({ name: o.name, label: o.label, date: o.date, choices: o.choices, default: o.default })
    }
    for (const o of model.options)
      fields.push({ name: o.name, label: o.label, date: o.date, choices: o.choices, default: o.default })
    return fields
  }
  const fieldLabel = (model: string, name: string) => {
    const found = settings.find((s) => s.id === model)
    return (found && fieldsOf(found).find((f) => f.name === name)?.label) ?? name
  }
  function valueWords(model: string, name: string, value: string | undefined): string {
    if (value === undefined) return ''
    const found = settings.find((s) => s.id === model)
    const choice =
      found &&
      fieldsOf(found)
        .find((f) => f.name === name)
        ?.choices?.find((c) => c.value === value)
    if (choice) return choice.label
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return formatDate(value, { year: true })
    return isTier(value) ? plantingWords(value) : value
  }

  function setOption(model: string, name: string, value: string | null) {
    const label = fieldLabel(model, name)
    change(optionPatch(own, model, name, value), value === null ? `${label} reset.` : `${label} saved.`)
  }

  function resetLevel() {
    const result = resetPrefs(level)
    plantingKind = {}
    done(
      result.ok ? (level.kind === 'all' ? 'Back to AgWeather’s defaults.' : 'Back to your defaults.') : result.message,
    )
  }

  const resetClass = 'text-ink-muted underline hover:text-ink'
  const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm'
</script>

<div class="space-y-5 text-sm" data-testid="prefs-{level.kind}">
  <p class="max-w-prose">{inheritanceWords(doc, level)}</p>

  <fieldset class="space-y-2" disabled={readOnly}>
    <legend class="text-base font-semibold">Crops</legend>
    <p class="flex flex-wrap gap-x-3 text-ink-muted" id="{uid}-crops-from">
      <span>{cropsLine}</span>
      {#if explained.crops.source.kind === 'here' && !readOnly}
        <button
          type="button"
          class={resetClass}
          aria-label="Reset crops for {levelWords}"
          onclick={() => change({ crops: null }, 'Crops reset.')}
        >
          Reset
        </button>
      {/if}
    </p>
    <div class="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
      {#each crops as crop (crop.id)}
        <label class="flex items-center gap-2">
          <input
            type="checkbox"
            class="rounded-sm"
            checked={chosenCrops?.includes(crop.id) ?? false}
            onchange={(event) => toggleCrop(crop.id, event.currentTarget.checked)}
          />
          {crop.name}
        </label>
      {/each}
    </div>
  </fieldset>

  <fieldset class="space-y-2" disabled={readOnly}>
    <legend class="text-base font-semibold">Models to show</legend>
    <p class="flex flex-wrap gap-x-3 text-ink-muted">
      <span>{hiddenLine}</span>
      {#if explained.hiddenModels.source.kind === 'here' && !readOnly}
        <button
          type="button"
          class={resetClass}
          aria-label="Reset hidden models for {levelWords}"
          onclick={() => change({ hiddenModels: null }, 'Hidden models reset.')}
        >
          Reset
        </button>
      {/if}
    </p>
    <p class="text-ink-muted">
      {chosenCrops
        ? 'The models for the crops chosen above. Clear a box to hide a model.'
        : 'Every model. Choose crops above to list only theirs; clear a box to hide a model.'}
    </p>
    <div class="grid max-h-72 gap-1 overflow-y-auto rounded-md border border-line p-2 sm:grid-cols-2 lg:grid-cols-3">
      {#each shownModels as model (model.id)}
        <label class="flex items-center gap-2">
          <input
            type="checkbox"
            class="rounded-sm"
            checked={!hidden.includes(model.id)}
            onchange={(event) => toggleModel(model.id, event.currentTarget.checked)}
          />
          {model.name}
        </label>
      {/each}
    </div>
  </fieldset>

  <div class="space-y-1">
    <label for="{uid}-planting" class="block text-base font-semibold">Planting date</label>
    <p class="text-ink-muted" id="{uid}-planting-hint">
      For every model that takes a planting date, unless a model’s own setting below says otherwise.
    </p>
    {@render planting(`${uid}-planting`, explained.planting.value, `${uid}-planting-hint`, (value) =>
      change({ planting: value }, value === null ? 'Planting date reset.' : 'Planting date saved.'),
    )}
    <p class="flex flex-wrap gap-x-3 text-ink-muted">
      <span>
        {line(
          explained.planting,
          `${plantingWords(explained.planting.value)}.`,
          'none chosen, so each model uses its own default.',
        )}
      </span>
      {#if explained.planting.source.kind === 'here' && !readOnly}
        <button
          type="button"
          class={resetClass}
          aria-label="Reset the planting date for {levelWords}"
          onclick={() => {
            delete plantingKind[`${uid}-planting`]
            change({ planting: null }, 'Planting date reset.')
          }}
        >
          Reset
        </button>
      {/if}
    </p>
  </div>

  {#if level.kind !== 'site'}
    <div class="space-y-1">
      <label for="{uid}-layer" class="block text-base font-semibold">Map</label>
      <p class="text-ink-muted" id="{uid}-layer-hint">
        {level.kind === 'group'
          ? 'The map this group opens with when you choose Show on the map.'
          : 'The map each group opens with when you choose Show on the map, unless the group chooses its own.'}
      </p>
      <select
        id="{uid}-layer"
        class={input}
        aria-describedby="{uid}-layer-hint"
        disabled={readOnly}
        value={explained.layer.value ?? ''}
        onchange={(event) =>
          change({ layer: event.currentTarget.value || null }, event.currentTarget.value ? 'Map saved.' : 'Map reset.')}
      >
        <option value="">The map’s own choice for the season</option>
        {#each layerChoices as model (model.id)}
          <option value={model.id}>{model.name}</option>
        {/each}
      </select>
      {#if explained.layer.source.kind !== 'here' && explained.layer.value}
        <p class="text-ink-muted">
          {`${sourceWords(explained.layer.source, level)}: ${modelName(explained.layer.value)}.`}
        </p>
      {/if}
    </div>
  {/if}

  <section class="space-y-2" aria-labelledby="{uid}-settings">
    <h3 id="{uid}-settings" class="text-base font-semibold">Model settings</h3>
    {#if inEffect.length}
      <ul class="space-y-1">
        {#each inEffect as item (item.model)}
          {#each item.names as [name, value] (name)}
            <li class="flex flex-wrap gap-x-3">
              <span>
                {`${modelName(item.model)}, ${fieldLabel(item.model, name).toLowerCase()}: ${valueWords(item.model, name, value.value)}`}
                <span class="text-ink-muted">{` (${sourceWords(value.source, level).toLowerCase()})`}</span>
              </span>
              {#if value.source.kind === 'here' && !readOnly}
                <button
                  type="button"
                  class={resetClass}
                  aria-label="Reset {modelName(item.model)}, {fieldLabel(item.model, name).toLowerCase()}"
                  onclick={() => setOption(item.model, name, null)}
                >
                  Reset
                </button>
              {/if}
            </li>
          {/each}
        {/each}
      </ul>
    {:else}
      <p class="text-ink-muted">
        No model settings yet: each model uses its own defaults. A setting chosen on a model’s page at a saved site is
        kept with that site.
      </p>
    {/if}
    {#if !readOnly}
      <div class="flex flex-wrap items-center gap-2">
        <label for="{uid}-model" class="font-medium">Change a model’s settings</label>
        <select id="{uid}-model" class={input} bind:value={editing}>
          <option value="">Choose a model</option>
          {#each editable as model (model.id)}
            <option value={model.id}>{model.name}</option>
          {/each}
        </select>
      </div>
      {#if editingModel}
        {@const model = editingModel}
        <div class="grid gap-4 rounded-md border border-line p-3 sm:grid-cols-2" data-testid="model-settings">
          {#each fieldsOf(model) as f (f.name)}
            {@const value = explained.options[model.id]?.[f.name]}
            {@const id = `${uid}-${model.id}-${f.name}`}
            <div class="flex flex-col gap-1">
              <label for={id} class="font-medium">{f.label}</label>
              {#if f.name === 'planting_date'}
                {@render planting(id, value?.value, undefined, (v) => setOption(model.id, f.name, v))}
              {:else if f.choices?.length}
                <select
                  {id}
                  class={input}
                  value={value?.value ?? f.default}
                  onchange={(event) => setOption(model.id, f.name, event.currentTarget.value)}
                >
                  {#each f.choices as c (c.value)}
                    <option value={c.value}>{c.label}</option>
                  {/each}
                </select>
              {:else}
                <input
                  {id}
                  type={f.date ? 'date' : 'text'}
                  class={input}
                  value={value?.value ?? ''}
                  onchange={(event) => setOption(model.id, f.name, event.currentTarget.value || null)}
                />
              {/if}
              <p class="flex flex-wrap gap-x-3 text-xs text-ink-muted">
                <span>{value ? sourceWords(value.source, level) : 'The model’s default'}</span>
                {#if value?.source.kind === 'here'}
                  <button
                    type="button"
                    class={resetClass}
                    aria-label="Reset {f.label.toLowerCase()}"
                    onclick={() => {
                      delete plantingKind[id]
                      setOption(model.id, f.name, null)
                    }}
                  >
                    Reset
                  </button>
                {/if}
              </p>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </section>

  {#if !readOnly}
    <div class="flex flex-wrap items-center gap-3 border-t border-line pt-3">
      <Button variant="secondary" class="px-3 py-1" disabled={!hasOwn(own)} onclick={resetLevel}>
        {level.kind === 'all' ? 'Reset to AgWeather’s defaults' : 'Reset to my defaults'}
      </Button>
      <span class="text-ink-muted">
        {level.kind === 'all'
          ? 'Clears every choice above.'
          : `Clears every choice made for ${levelWords}, so it follows ${level.kind === 'site' ? 'its groups and ' : ''}your choices for all sites.`}
      </span>
    </div>
  {/if}
  <p role="status" class="text-ink-muted">{status}</p>
</div>

{#snippet planting(
  id: string,
  value: string | undefined,
  describedBy: string | undefined,
  onchange: (v: string | null) => void,
)}
  {@const kind = kindOf(id, value)}
  <div class="flex flex-wrap gap-2">
    <select
      {id}
      class={input}
      aria-describedby={describedBy}
      disabled={readOnly}
      value={kind}
      onchange={(event) => {
        const next = event.currentTarget.value
        if (next === 'date') {
          plantingKind[id] = 'date'
          return
        }
        delete plantingKind[id]
        onchange(next || null)
      }}
    >
      <option value="">None chosen</option>
      {#each TIERS as tier (tier.value)}
        <option value={tier.value}>{tier.label}</option>
      {/each}
      <option value="date">A date</option>
    </select>
    {#if kind === 'date'}
      <input
        type="date"
        class={input}
        aria-label="Planting date"
        disabled={readOnly}
        value={value && !isTier(value) ? value : ''}
        onchange={(event) => {
          if (event.currentTarget.value) {
            delete plantingKind[id]
            onchange(event.currentTarget.value)
          }
        }}
      />
    {/if}
  </div>
{/snippet}
