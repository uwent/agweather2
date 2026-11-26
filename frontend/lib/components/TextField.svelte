<!-- Ported from WISP 3: app/frontend/lib/components/TextField.svelte -->
<script lang="ts">
  import FieldLabel from '@/lib/components/FieldLabel.svelte'
  import type { FieldInfoKey } from '@/lib/fieldInfo'
  import type { HTMLInputAttributes } from 'svelte/elements'

  let {
    label,
    name,
    error,
    hint,
    info,
    value = $bindable(),
    optional = false,
    class: className = '',
    id = `field-${name.replace(/[^a-z0-9]+/gi, '-')}`,
    ...rest
  }: HTMLInputAttributes & {
    label: string
    name: string
    error?: string | string[]
    hint?: string
    /** An info tip by the label (lib/fieldInfo.ts) */
    info?: FieldInfoKey
    /** Says "Optional" by the label */
    optional?: boolean
  } = $props()

  // Required and still empty: marked until it has a value
  const missing = $derived(Boolean(rest.required) && !String(value ?? '').trim())

  const message = $derived(Array.isArray(error) ? error[0] : error)
  // Only one of the error or the hint is rendered, so only reference that one
  const describedBy = $derived(message ? `${id}-error` : hint ? `${id}-hint` : undefined)
</script>

<div class="space-y-1">
  <FieldLabel {label} {info} {missing} {optional} for={id} />
  <input
    {id}
    {name}
    class="block w-full rounded-md shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm
      {message ? 'border-danger' : missing ? 'border-l-4 border-l-brand-500' : ''} {className}"
    aria-invalid={message ? 'true' : undefined}
    aria-describedby={describedBy}
    bind:value
    {...rest}
  />
  {#if message}
    <p id="{id}-error" class="text-sm text-danger-ink">{message}</p>
  {:else if hint}
    <p id="{id}-hint" class="text-sm text-ink-muted">{hint}</p>
  {/if}
</div>
