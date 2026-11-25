<script lang="ts">
  import { untrack } from 'svelte'

  import { formatDate } from '@/lib/dates'
  import type { SiteModelInfo } from '@/types'

  import { PLANTING_TIERS, type Chosen } from './modelOptions'

  // A model's settings at a site: the date it counts from, the planting date, and the model's own options. Applied
  // with Save (to the site's preferences when it's saved, else to this page's view, in its Share link); Reset goes
  // back to the defaults.
  let {
    model,
    chosen,
    saved,
    resolved,
    onapply,
  }: {
    model: SiteModelInfo
    chosen: Chosen
    /** Whether the site is saved, so the settings are kept with it */
    saved: boolean
    /** The run's resolved start and planting date, for the defaults' words */
    resolved: { biofix: string | null; planting: string | null }
    onapply: (chosen: Chosen) => void
  } = $props()

  let draft = $state<Chosen>(untrack(() => ({ ...chosen })))
  // A new set of settings from outside (another tab, a reset) replaces the draft
  $effect(() => {
    const next = { ...chosen }
    untrack(() => (draft = next))
  })

  const plantingKind = $derived(
    !draft.planting_date
      ? ''
      : (PLANTING_TIERS as readonly string[]).includes(draft.planting_date)
        ? draft.planting_date
        : 'date',
  )
  let error = $state('')
  let status = $state('')

  function setPlanting(kind: string) {
    draft.planting_date = kind === 'date' ? (resolved.planting ?? '') : kind
  }

  function submit(event: SubmitEvent) {
    event.preventDefault()
    if (plantingKind === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(draft.planting_date ?? '')) {
      error = 'Enter a planting date, or choose a typical one.'
      return
    }
    error = ''
    onapply(Object.fromEntries(Object.entries(draft).filter(([, v]) => v !== '')))
    status = saved ? 'Saved with this site.' : 'Applied. Save this site to keep these settings.'
  }

  function reset() {
    draft = {}
    error = ''
    onapply({})
    status = 'Back to the defaults.'
  }

  const tierLabels: Record<string, string> = { early: 'Early', mid: 'Typical', late: 'Late' }
  const biofixDefault = $derived.by(() => {
    if (!model.biofix) return ''
    const fixed = formatDate(`2001-${model.biofix.default}`)
    return model.biofix.stage
      ? `By default, ${fixed}; with a planting date, the estimated date of ${model.biofix.stage}.`
      : `By default, ${fixed}.`
  })
  const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm'
</script>

<form class="space-y-4" onsubmit={submit} novalidate>
  <div class="grid gap-4 sm:grid-cols-2">
    {#if model.biofix}
      <label class="flex flex-col gap-1 text-sm">
        <span class="font-medium">Count from</span>
        <span class="text-xs text-ink-muted">{`${model.biofix.label}. ${biofixDefault}`}</span>
        <input type="date" class={input} bind:value={draft.biofix} />
      </label>
    {/if}
    {#if model.planting}
      <div class="flex flex-col gap-1 text-sm">
        <label for="model-planting" class="font-medium">Planting date</label>
        <span class="text-xs text-ink-muted" id="model-planting-hint">
          {model.susceptible
            ? `Gives the ${model.planting.crop.toLowerCase()} stages, so the risk counts only while the crop is susceptible.`
            : `Estimates the ${model.planting.crop.toLowerCase()} stages from it.`}
        </span>
        <div class="flex flex-wrap gap-2">
          <select
            id="model-planting"
            class={input}
            aria-describedby="model-planting-hint"
            value={plantingKind}
            onchange={(event) => setPlanting(event.currentTarget.value)}
          >
            <option value="">{model.group === 'crop' ? 'The default date' : 'None'}</option>
            {#if model.planting.typical_dates}
              {#each PLANTING_TIERS as tier (tier)}
                <option value={tier}>{`${tierLabels[tier]} for this location`}</option>
              {/each}
            {/if}
            <option value="date">A date</option>
          </select>
          {#if plantingKind === 'date'}
            <input
              type="date"
              class={input}
              aria-label="Planting date"
              aria-invalid={error ? 'true' : undefined}
              bind:value={draft.planting_date}
            />
          {/if}
        </div>
      </div>
      {#each model.planting.options as option (option.name)}
        {@render choice(option)}
      {/each}
    {/if}
    {#each model.options as option (option.name)}
      {@render choice(option)}
    {/each}
  </div>
  {#if error}<p class="text-sm text-danger-ink" role="alert">{error}</p>{/if}
  <div class="flex flex-wrap items-center gap-3">
    <button
      type="submit"
      class="rounded-md bg-brand-600 px-3 py-1 text-sm font-semibold text-surface hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
    >
      {saved ? 'Save settings' : 'Apply'}
    </button>
    <button type="button" class="text-sm text-ink-muted underline hover:text-ink" onclick={reset}>
      Reset to the defaults
    </button>
    <p class="text-sm text-ink-muted" role="status">{status}</p>
  </div>
</form>

{#snippet choice(option: SiteModelInfo['options'][number])}
  <label class="flex flex-col gap-1 text-sm">
    <span class="font-medium">{option.label}</span>
    {#if option.choices.length}
      <select class={input} bind:value={() => draft[option.name] ?? option.default, (v) => (draft[option.name] = v)}>
        {#each option.choices as c (c.value)}
          <option value={c.value}>{c.label}</option>
        {/each}
      </select>
    {:else}
      <input
        type={option.date ? 'date' : 'text'}
        class={input}
        bind:value={() => draft[option.name] ?? option.default, (v) => (draft[option.name] = v)}
      />
    {/if}
  </label>
{/snippet}
