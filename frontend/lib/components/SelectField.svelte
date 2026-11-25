<!-- Ported from WISP 3: app/frontend/lib/components/SelectField.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import type { HTMLSelectAttributes } from 'svelte/elements'

  import FieldLabel from '@/lib/components/FieldLabel.svelte'
  import type { FieldInfoKey } from '@/lib/fieldInfo'

  let {
    label,
    name,
    options,
    value = $bindable(),
    error,
    hint,
    note,
    info,
    optional = false,
    id = `field-${(name ?? label).replace(/[^a-z0-9]+/gi, '-')}`,
    ...rest
  }: HTMLSelectAttributes & {
    label: string
    options: { value: string | number; label: string }[]
    error?: string | string[]
    hint?: string
    /** In place of the hint, for one that needs markup (a warning with a button) */
    note?: Snippet
    /** An info tip by the label (lib/fieldInfo.ts) */
    info?: FieldInfoKey
    /** Says "Optional" by the label */
    optional?: boolean
  } = $props()

  // Required and nothing chosen: marked until it has a value
  const missing = $derived(Boolean(rest.required) && (value === undefined || value === null || value === ''))

  const message = $derived(Array.isArray(error) ? error[0] : error)
</script>

<div class="space-y-1">
  <FieldLabel {label} {info} {missing} {optional} for={id} />
  <select
    {id}
    {name}
    bind:value
    class="block w-full rounded-md shadow-sm focus:border-brand-500 focus:ring-brand-500 disabled:cursor-not-allowed disabled:bg-surface disabled:text-ink-muted sm:text-sm
      {message ? 'border-danger' : missing ? 'border-l-4 border-l-brand-500' : ''}"
    aria-invalid={message ? 'true' : undefined}
    aria-describedby={message || hint || note ? `${id}-note` : undefined}
    {...rest}
  >
    {#each options as option (option.value)}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
  {#if message}
    <p id="{id}-note" class="text-sm text-danger-ink">{message}</p>
  {:else if note}
    <div id="{id}-note" class="text-sm">{@render note()}</div>
  {:else if hint}
    <p id="{id}-note" class="text-sm text-ink-muted">{hint}</p>
  {/if}
</div>
