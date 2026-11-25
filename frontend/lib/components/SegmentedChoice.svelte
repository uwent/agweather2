<!-- Ported from WISP 3: app/frontend/lib/components/SegmentedChoice.svelte -->
<script lang="ts" generics="T extends string">
  // One choice of a few, as small joined pills: radio buttons (one tab stop, arrow keys move between
  // them), each with an optional color swatch (an import card's Skip | New field | Update field, in the
  // map's colors) that tints it when chosen
  let {
    legend,
    name,
    options,
    value,
    onchange,
    showLegend = false,
  }: {
    /** The group's accessible name; shown before the pills with showLegend */
    legend: string
    /** The radios' name, unique on the page */
    name: string
    options: { value: T; label: string; color?: string; disabled?: boolean }[]
    value: T
    onchange: (value: T) => void
    showLegend?: boolean
  } = $props()
</script>

<fieldset class="flex items-center gap-2 text-xs">
  <legend class={showLegend ? 'float-left mr-2 text-ink-muted' : 'sr-only'}>{legend}</legend>
  <div class="flex overflow-hidden rounded-md border border-line">
    {#each options as option (option.value)}
      {@const chosen = value === option.value}
      <label
        class="relative flex cursor-pointer items-center gap-1.5 border-line px-2 py-1 not-first:border-l
          has-focus-visible:outline-2 has-focus-visible:-outline-offset-2 has-focus-visible:outline-brand-500
          has-disabled:cursor-not-allowed has-disabled:opacity-50
          {chosen ? 'font-medium' : 'text-ink-muted hover:bg-surface'}
          {chosen && !option.color ? 'bg-brand-50' : ''}"
        style:background-color={chosen && option.color
          ? `color-mix(in oklch, ${option.color} 22%, transparent)`
          : undefined}
      >
        <input
          type="radio"
          class="sr-only"
          {name}
          value={option.value}
          checked={chosen}
          disabled={option.disabled}
          onchange={() => onchange(option.value)}
        />
        {#if option.color}
          <span class="size-2.5 shrink-0 rounded-sm" style:background-color={option.color}></span>
        {/if}{option.label}
      </label>
    {/each}
  </div>
</fieldset>
