<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/NumberField.svelte -->
<script lang="ts">
  import { type Snippet, untrack } from 'svelte'

  import FieldLabel from '@/lib/components/FieldLabel.svelte'
  import type { FieldInfoKey } from '@/lib/fieldInfo'
  import { currentUnits, parseNumber } from '@/lib/units'

  // A number input in the reader's units (F10). What's typed is shown as-is; a hidden input carries
  // the value converted to the stored unit, under `name`, for Inertia's <Form>.
  let {
    label,
    name,
    unit,
    value = $bindable(null),
    error,
    hint,
    info,
    required = false,
    placeholder,
    unitLabel,
    scale = 1,
    hideLabel = false,
    optional = false,
    trailing,
    center = false,
    precision,
    blankValue = null,
    submitBlankValue = false,
    after,
    id = `field-${(name ?? label).replace(/[^a-z0-9]+/gi, '-')}`,
  }: {
    label: string
    /** Omit for a box that isn't submitted (give it an id) */
    name?: string
    /** The stored unit (a catalog symbol, such as degF_day or mm), shown in the reader's units; omit for plain numbers (percents) */
    unit?: string
    /** The stored value */
    value?: number | null
    error?: string | string[]
    hint?: string
    /** An info tip by the label (lib/fieldInfo.ts) */
    info?: FieldInfoKey
    required?: boolean
    placeholder?: string
    /** Shown after the box when there's no unit, e.g. "%" */
    unitLabel?: string
    /** For plain numbers: shown = stored × scale (e.g. 100 to enter a fraction as a percent) */
    scale?: number
    /** Label for screen readers only (in table cells) */
    hideLabel?: boolean
    /** Beside the box, after its unit (a button that fills it) */
    after?: Snippet
    /** Inside the end of the box (a small icon button: the irrigation calculator) */
    trailing?: Snippet
    /** The value centered in the box, as in a table's cells */
    center?: boolean
    /**
     * Decimal places always shown, in the units shown ("1" reads "1.00" once the box is left); what's
     * typed is rounded to them, so what's saved is what's seen. Omit to show values as typed.
     */
    precision?: number
    /** Says "Optional" by the label */
    optional?: boolean
    /** The stored value a blank box stands for (a default), shown as its placeholder and in change lists */
    blankValue?: number | null
    /** Submit blankValue when the box is blank (a column that needs a value), not '' (NULL: the default) */
    submitBlankValue?: boolean
    id?: string
  } = $props()

  const units = $derived(currentUnits())
  const shown = (stored: number) => (unit ? units.toDisplay(unit, stored) : stored * scale) as number
  const show = (stored: number | null) => {
    if (precision !== undefined && stored !== null) return shown(stored).toFixed(precision)
    return unit ? units.input(unit, stored) : stored === null ? '' : String(Number((stored * scale).toFixed(6)))
  }
  const toStored = (display: number) => (unit ? units.toStored(unit, display) : display / scale)

  let text = $state(untrack(() => show(value)))
  let localError = $state<string | null>(null)
  // The value this box last produced; any other value was set from outside (e.g. the map picker)
  let own = untrack(() => value)

  $effect(() => {
    if (value !== own) {
      own = value
      text = untrack(() => show(value))
      localError = null
    }
  })

  // While what's typed can't be read, the form won't submit (the hidden input still holds the last
  // number read, which would otherwise be saved without a word)
  let box = $state<HTMLInputElement>()
  $effect(() => box?.setCustomValidity(localError ?? ''))

  // Typed in since the box was last left: only then does leaving it round (a saved 0.177 shown as
  // 0.18 stays 0.177 until it's changed)
  let typed = false

  function update(input: string) {
    typed = true
    text = input
    const parsed = unit ? units.parse(unit, input) : parseNumber(input)
    localError = parsed.ok ? null : parsed.error
    if (parsed.ok) value = own = parsed.value === null || unit ? parsed.value : parsed.value / scale
  }

  // With a precision, leaving the box shows the value to it, rounded if more was typed
  function settle() {
    if (!typed) return
    typed = false
    if (precision === undefined || localError || value === null) return
    const rounded = Number(shown(value).toFixed(precision))
    if (rounded !== Number(shown(value).toFixed(12))) value = own = toStored(rounded)
    text = show(value)
  }

  // A default shown in the blank box: its placeholder, and what lib/formChanges.ts reads for blank
  const blankText = $derived(blankValue === null ? undefined : show(blankValue))
  const submitted = $derived(value ?? (submitBlankValue ? blankValue : null) ?? '')
  const message = $derived(localError ?? (Array.isArray(error) ? error[0] : error))
  // Required and still empty: marked until it has a value
  const missing = $derived(required && !text.trim())
  const suffix = $derived(unit ? units.label(unit) : unitLabel)
</script>

<!-- The unit hangs off the end of the box, outside the label's line, so an info tip at the end of
     the label sits over the end of the box -->
<div class={hideLabel ? '' : 'space-y-1'}>
  <!-- First, so space-y's gap after the box comes only with a message below it -->
  {#if name}<input type="hidden" {name} value={submitted} />{/if}
  <div class="flex items-end gap-2">
    <div class="min-w-0 flex-1 {hideLabel ? '' : 'space-y-1'}">
      <FieldLabel {label} {info} {missing} {optional} for={id} hidden={hideLabel} />
      <div class="relative">
        <input
          bind:this={box}
          {id}
          type="text"
          inputmode="decimal"
          class="block w-full min-w-0 rounded-md shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm
            {center ? 'px-1.5 text-center' : ''} {trailing ? (center ? 'px-8' : 'pr-8') : ''} {message
            ? 'border-danger'
            : missing
              ? 'border-l-4 border-l-brand-500'
              : ''}"
          value={text}
          data-unit={suffix}
          oninput={(event) => update(event.currentTarget.value)}
          onblur={settle}
          aria-invalid={message ? 'true' : undefined}
          aria-describedby={message ? `${id}-error` : hint ? `${id}-hint` : undefined}
          data-blank={blankText}
          {required}
          placeholder={placeholder ?? blankText}
        />
        {#if trailing}<div class="absolute inset-y-0 right-0 flex items-center pr-1">{@render trailing()}</div>{/if}
      </div>
    </div>
    {#if suffix && !hideLabel}<span class="flex h-10.5 shrink-0 items-center text-sm text-ink-muted sm:h-9.5">
        {suffix}
      </span>{/if}
    {@render after?.()}
  </div>
  {#if message}
    <p id="{id}-error" class="text-xs text-danger-ink sm:text-sm">{message}</p>
  {:else if hint}
    <p id="{id}-hint" class="text-sm text-ink-muted">{hint}</p>
  {/if}
</div>
