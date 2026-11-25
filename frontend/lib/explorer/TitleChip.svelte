<script lang="ts">
  // The map's title over its top left corner (Phase 7 track 2 step 5): the layer's name, then what the API says
  // the map shows (its `subtitle`: the date and settings) or, until it does, the date in words; and how new the
  // data is. The same text is announced to screen readers by the page's live region.
  let {
    title,
    subtitle,
    when,
    through,
  }: {
    title: string
    subtitle?: string | null
    /** The date or range in words, shown without a subtitle */
    when: string
    /** "Observed through … · forecast to …" */
    through: string | null
  } = $props()
</script>

<div class="max-w-md rounded-md bg-surface-raised/95 px-3 py-1.5 shadow-md ring-1 ring-line" data-testid="title-chip">
  <p class="text-sm/snug font-semibold">{title}</p>
  <p class="text-xs/snug">{subtitle || when}</p>
  {#if through}<p class="text-xs/snug text-ink-muted">{through}</p>{/if}
</div>
