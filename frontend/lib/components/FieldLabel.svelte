<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/FieldLabel.svelte -->
<script lang="ts">
  import InfoTip from '@/lib/components/InfoTip.svelte'
  import { fieldInfo, type FieldInfoKey } from '@/lib/fieldInfo'
  import { currentUnits } from '@/lib/units'

  // A form control's label with its info tip at the far end of the line. The tip sits outside
  // the <label> (a button inside one would focus the control) and outside the text a legend's
  // fieldset is named by (`labelId`), so neither the control's name nor the changes prompt
  // (lib/formChanges.ts) picks up its "About …".
  //
  // Required and optional: a required control that's still empty gets a dot before its
  // label (`missing`), gone once it has a value; an optional one says "Optional" after it. Both sit
  // outside the label text, so the control's accessible name stays its label (the control's own
  // `required` tells screen readers).
  let {
    label,
    info,
    for: htmlFor,
    as = 'label',
    labelId,
    hidden = false,
    missing = false,
    optional = false,
    class: className = 'text-sm font-medium',
  }: {
    label: string
    info?: FieldInfoKey
    /** The control's id, for a <label> */
    for?: string | null
    /** A <label>, a <legend> (the fieldset's first child), or a <span> naming a radiogroup */
    as?: 'label' | 'legend' | 'span'
    /** An id for the label's own text, for aria-labelledby */
    labelId?: string
    /** Screen readers only (in table cells); no tip */
    hidden?: boolean
    /** Required and still empty: a dot before the label */
    missing?: boolean
    /** Not required: "Optional" after the label */
    optional?: boolean
    class?: string
  } = $props()

  const tip = $derived(info ? fieldInfo(info, currentUnits()) : null)
</script>

{#snippet dot()}
  {#if missing}<span aria-hidden="true" data-missing class="size-1.5 shrink-0 rounded-full bg-brand-500"></span>{/if}
{/snippet}
{#snippet optionalMark()}
  {#if optional}<span class="text-xs font-normal text-ink-muted">Optional</span>{/if}
{/snippet}

{#if hidden}
  <label for={htmlFor ?? undefined} class="sr-only">{label}</label>
{:else if as === 'legend'}
  <legend class="flex w-full items-center justify-between gap-2 {className}">
    <span class="flex items-center gap-1.5">
      {@render dot()}<span id={labelId}>{label}</span>{@render optionalMark()}
    </span>
    {#if tip}<InfoTip text={tip.text} term={tip.term} label="About {label}" />{/if}
  </legend>
{:else}
  <div class="flex items-center justify-between gap-2">
    <span class="flex items-center gap-1.5">
      {@render dot()}
      {#if as === 'label'}
        <label for={htmlFor ?? undefined} id={labelId} class="block {className}">{label}</label>
      {:else}
        <span id={labelId} class="block {className}">{label}</span>
      {/if}
      {@render optionalMark()}
    </span>
    {#if tip}<InfoTip text={tip.text} term={tip.term} label="About {label}" />{/if}
  </div>
{/if}
