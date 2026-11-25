<script lang="ts">
  // The map's title over its top left corner (Phase 7 track 2 step 5): the layer's name, then what the API says the
  // map shows (the TileJSON's `subtitle`: the date and settings), how new the data is, and a link to the API's notes
  // on this map where it has any. The same text is announced to screen readers by the page's live region.
  let {
    title,
    subtitle,
    through,
    notes = 0,
  }: {
    title: string
    /** The TileJSON's subtitle; '' until it comes */
    subtitle: string
    /** "Observed through … · forecast to …" */
    through: string | null
    /** How many warnings the API gave about this map (shown below it, in its words) */
    notes?: number
  } = $props()
</script>

<div class="max-w-md rounded-md bg-surface-raised/95 px-3 py-1.5 shadow-md ring-1 ring-line" data-testid="title-chip">
  <p class="text-sm/snug font-semibold">{title}</p>
  {#if subtitle}<p class="text-xs/snug">{subtitle}</p>{/if}
  {#if through}<p class="hidden text-xs/snug text-ink-muted sm:block">{through}</p>{/if}
  {#if notes}
    <p class="text-xs/snug">
      <a href="#map-notes" class="text-brand-600 underline hover:text-brand-700">
        {notes === 1 ? 'A note on this map' : `${notes} notes on this map`}
      </a>
    </p>
  {/if}
</div>
