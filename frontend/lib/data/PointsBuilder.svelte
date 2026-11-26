<script lang="ts">
  import { onDestroy, untrack, type Snippet } from 'svelte'

  import type { VariablesResponse } from '@/types/api'

  import { get } from '../api'
  import SegmentedChoice from '../components/SegmentedChoice.svelte'
  import { addDays } from '../dates'
  import {
    DEFAULT_VARS,
    KINDS,
    choiceDays,
    downloadBytes,
    formatBytes,
    groupVariables,
    pointsRequest,
    variablesFor,
    type DataChoice,
    type DataKind,
    type Point,
  } from '../sites/dataRequest'
  import Failed from '../sites/Failed.svelte'
  import { request } from '../sites/request.svelte'
  import { currentUnits, formatNumber } from '../units'

  // A download builder for one location or several (../sites/dataRequest.ts): a site's Data tab (track 3 step 10)
  // and /data's weather at locations (track 7 step 7.1). What to download (`kind`) is the page's view; the rest is
  // chosen here. The variables come from `/variables`.
  let {
    points,
    today,
    models,
    kind,
    onkind,
    intro,
    headingLevel = 3,
  }: {
    points: Point[]
    today: string
    models: { id: string; name: string; status: string }[]
    kind: DataKind
    onkind: (kind: DataKind) => void
    intro?: Snippet
    /** The level of "Your download"'s heading */
    headingLevel?: 3 | 4
  } = $props()

  const id = $props.id()
  const readerUnits = currentUnits().system === 'metric' ? 'metric' : 'us'
  const catalog = request<VariablesResponse>()
  const loadCatalog = () => catalog.load((signal) => get<VariablesResponse>('/variables', undefined, { signal }))
  loadCatalog()
  onDestroy(() => catalog.cancel())


  // Each kind keeps its own variables while the reader switches between them
  let chosenVars = $state<Record<'daily' | 'hourly' | 'totals', string[]>>({
    daily: [...DEFAULT_VARS.daily],
    hourly: [...DEFAULT_VARS.hourly],
    totals: [...DEFAULT_VARS.totals],
  })
  const firstDay = untrack(() => today)
  let start = $state(`${firstDay.slice(0, 4)}-01-01`)
  let hourStart = $state(addDays(firstDay, -7))
  let end = $state(firstDay)
  let forecast = $state(true)
  let units = $state<'us' | 'metric'>(readerUnits)
  let format = $state<'csv' | 'json'>('csv')
  let dd = $state(readerUnits === 'metric' ? 'modified_10_30' : 'modified_50_86')
  let biofix = $state('')
  const runnable = $derived(models.filter((m) => m.status !== 'retired'))
  let model = $state(untrack(() => models.find((m) => m.id === 'late-blight-dsv')?.id ?? models[0]?.id ?? ''))

  const hasVars = $derived(kind === 'daily' || kind === 'hourly' || kind === 'totals')
  const groups = $derived(groupVariables(variablesFor(kind, catalog.value.data?.data ?? [])))
  const vars = $derived(hasVars ? chosenVars[kind as 'daily' | 'hourly' | 'totals'] : [])

  function toggle(name: string, on: boolean) {
    const key = kind as 'daily' | 'hourly' | 'totals'
    const now = chosenVars[key]
    chosenVars[key] = on ? [...now, name] : now.filter((v) => v !== name)
  }

  function setUnits(next: 'us' | 'metric') {
    // The default setting follows the units its thresholds are read in
    if (dd === 'modified_50_86' && next === 'metric') dd = 'modified_10_30'
    if (dd === 'modified_10_30' && next === 'us') dd = 'modified_50_86'
    units = next
  }

  const choice = $derived<DataChoice>({
    kind,
    vars,
    start: kind === 'hourly' ? hourStart : start,
    end,
    forecast,
    units,
    format,
    dd,
    biofix,
    model,
  })
  const built = $derived(pointsRequest(choice, points, today))
  // Said before the download: the rows (a location's days or hours, or its one row of totals) and about how large
  const size = $derived.by(() => {
    const bytes = downloadBytes(choice, today, points.length)
    const days = choiceDays(choice, today)
    if (bytes === null || days === null) return null
    const rows = (kind === 'totals' ? 1 : kind === 'hourly' ? days * 24 : days) * points.length
    return `About ${formatNumber(rows)} ${rows === 1 ? 'row' : 'rows'}, ${formatBytes(bytes)}.`
  })
  const fullUrl = $derived(typeof window === 'undefined' ? built.url : `${window.location.origin}${built.url}`)

  let copied = $state<'yes' | 'failed' | null>(null)
  async function copy() {
    try {
      await navigator.clipboard.writeText(fullUrl)
      copied = 'yes'
    } catch {
      copied = 'failed'
    }
  }
  $effect(() => {
    void fullUrl
    copied = null
  })

  const inputClass = 'rounded-md border border-line bg-surface px-2 py-1 text-sm'
</script>

<div class="max-w-4xl space-y-5">
  {@render intro?.()}

  <fieldset class="space-y-2">
    <legend class="text-sm font-medium">What to download</legend>
    <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {#each KINDS as option (option.value)}
        <label
          class="flex cursor-pointer gap-2 rounded-md border p-2 text-sm has-checked:border-brand-600 has-checked:bg-brand-50
            has-focus-visible:outline-2 has-focus-visible:outline-brand-600
            {kind === option.value ? 'border-brand-600' : 'border-line'}"
        >
          <input
            type="radio"
            name="{id}-kind"
            class="mt-0.5 accent-brand-600"
            value={option.value}
            checked={kind === option.value}
            onchange={() => onkind(option.value)}
          />
          <span>
            <span class="font-medium">{option.label}</span>
            <span class="block text-xs text-ink-muted">{option.description}</span>
          </span>
        </label>
      {/each}
    </div>
  </fieldset>

  {#if hasVars}
    <fieldset class="space-y-2">
      <legend class="text-sm font-medium">{`Variables (${vars.length} chosen)`}</legend>
      {#if catalog.value.status === 'failed'}
        <Failed {...catalog.value} retry={loadCatalog} />
      {:else if !catalog.value.data}
        <div class="h-24 animate-pulse rounded-md bg-surface-raised" aria-hidden="true"></div>
      {/if}
      <div class="space-y-1">
        {#each groups as group, g (group.label)}
          {@const count = group.variables.filter((v) => vars.includes(v.name)).length}
          <details class="rounded-md border border-line px-3 py-1.5" open={g === 0}>
            <summary class="cursor-pointer text-sm">
              {group.label}{count ? ` (${count} chosen)` : ''}
            </summary>
            <div class="grid gap-x-4 gap-y-1 py-2 sm:grid-cols-2">
              {#each group.variables as variable (variable.name)}
                <label class="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    class="mt-0.5 size-4 shrink-0 accent-brand-600"
                    checked={vars.includes(variable.name)}
                    onchange={(event) => toggle(variable.name, event.currentTarget.checked)}
                  />
                  <span>
                    {variable.long_name}
                    <code class="block text-xs break-all text-ink-muted">{variable.name}</code>
                  </span>
                </label>
              {/each}
            </div>
          </details>
        {/each}
      </div>
    </fieldset>
  {/if}

  {#if kind === 'degree-days'}
    <label class="flex flex-col gap-1 text-sm">
      <span class="font-medium">Degree-day settings</span>
      <input class="{inputClass} max-w-md font-mono" bind:value={dd} aria-describedby="{id}-dd-help" />
      <span id="{id}-dd-help" class="text-xs text-ink-muted">
        {`The method (sine, modified or average), the base and an optional upper threshold, joined by underscores, in ${units === 'metric' ? '°C' : '°F'}; separate several with commas, such as '${units === 'metric' ? 'modified_10_30,sine_5' : 'modified_50_86,sine_41'}'.`}
      </span>
    </label>
  {/if}
  {#if kind === 'model'}
    <label class="flex flex-col gap-1 text-sm">
      <span class="font-medium">Model</span>
      <select class="{inputClass} max-w-md" bind:value={model}>
        {#each runnable as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
      </select>
    </label>
  {/if}

  <fieldset class="space-y-2">
    <legend class="text-sm font-medium">Days</legend>
    <div class="flex flex-wrap items-end gap-3 text-sm">
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">Start date</span>
        {#if kind === 'hourly'}
          <input type="date" class={inputClass} bind:value={hourStart} />
        {:else}
          <input type="date" class={inputClass} bind:value={start} />
        {/if}
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-xs text-ink-muted">End date</span>
        <input type="date" class={inputClass} bind:value={end} disabled={forecast} />
      </label>
      {#if kind === 'degree-days' || kind === 'model'}
        <label class="flex flex-col gap-1">
          <span class="text-xs text-ink-muted">Count from (optional)</span>
          <input type="date" class={inputClass} bind:value={biofix} />
        </label>
      {/if}
      <label class="flex items-center gap-2 pb-1">
        <input type="checkbox" class="size-4 accent-brand-600" bind:checked={forecast} />
        Through the forecast
      </label>
    </div>
    {#if kind === 'hourly'}
      <p class="text-xs text-ink-muted">Hours are in UTC, each labeled by the end of its hour.</p>
    {/if}
  </fieldset>

  <div class="flex flex-wrap gap-x-6 gap-y-3">
    <SegmentedChoice
      legend="Units"
      name="{id}-units"
      showLegend
      options={[
        { value: 'us', label: 'US (°F, inches)' },
        { value: 'metric', label: 'Metric (°C, mm)' },
      ]}
      value={units}
      onchange={setUnits}
    />
    <SegmentedChoice
      legend="Format"
      name="{id}-format"
      showLegend
      options={[
        { value: 'csv', label: 'CSV' },
        { value: 'json', label: 'JSON' },
      ]}
      value={format}
      onchange={(next) => (format = next)}
    />
  </div>

  <section class="space-y-2 rounded-md border border-line bg-surface-raised p-3" aria-labelledby="{id}-request">
    <svelte:element this={`h${headingLevel}`} id="{id}-request" class="text-sm font-medium">Your download</svelte:element>
    {#if built.problem}
      <p class="text-sm text-danger-ink" role="alert">{built.problem}</p>
    {:else}
      {#if size}
        <p class="text-sm" data-testid="download-size">{size}</p>
      {/if}
      <div class="flex flex-wrap items-center gap-3">
        <a
          href={built.url}
          download
          class="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 dark:text-surface"
        >
          {`Download ${format === 'csv' ? 'CSV' : 'JSON'}`}
        </a>
        <button
          type="button"
          class="cursor-pointer rounded-md border border-line bg-surface px-3 py-2 text-sm hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600"
          onclick={copy}
        >
          Copy the address
        </button>
        <span class="text-xs text-ink-muted" role="status">
          {copied === 'yes'
            ? 'Copied.'
            : copied === 'failed'
              ? 'Your browser didn’t allow copying. Select the address and copy it.'
              : ''}
        </span>
      </div>
    {/if}
    <label class="block text-xs text-ink-muted" for="{id}-url">The request’s address, for a script</label>
    <textarea
      id="{id}-url"
      readonly
      rows="3"
      class="w-full resize-y rounded-md border border-line bg-surface p-2 font-mono text-xs break-all"
      onfocus={(event) => event.currentTarget.select()}>{fullUrl}</textarea
    >
    <p class="text-xs text-ink-muted">
      {'CSV files begin with lines starting with # that describe the data; R’s read.csv(url, comment.char = "#") and pandas’ read_csv(url, comment="#") skip them. '}
      <a href="/api/v2/docs" class="underline hover:text-ink">Read the API documentation</a>
      {' for every option.'}
    </p>
  </section>
</div>
