<script lang="ts">
  // The map's title over its top left corner (Phase 7 track 2 step 5): what the map is and nothing else (Ben,
  // 2026-11-26): the layer's name, then what the API says the map shows (the TileJSON's `subtitle`: the date and
  // settings), marked "Forecast" when its day is one, and a link to the API's notes on this map where it has any.
  // How far the data reaches is the date control's to say. The same text is announced by the page's live region.
  let {
    title,
    subtitle,
    forecast = false,
    notes = 0,
  }: {
    title: string
    /** The TileJSON's subtitle; '' until it comes */
    subtitle: string
    /** Whether the map's day (or a range's last) is a forecast */
    forecast?: boolean
    /** How many warnings the API gave about this map (shown below it, in its words) */
    notes?: number
  } = $props()
</script>

<div class="max-w-md rounded-md bg-surface-raised/95 px-3 py-1.5 shadow-md ring-1 ring-line" data-testid="title-chip">
  <p class="text-sm/snug font-semibold">{title}</p>
  {#if subtitle}
    <p class="text-xs/snug">
      {subtitle}{#if forecast}<span class="sr-only">{', '}</span><span
          class="ml-1.5 rounded-sm bg-brand-100 px-1.5 py-px text-xs font-medium text-brand-700"
        >
          Forecast
        </span>{/if}
    </p>
  {/if}
  {#if notes}
    <p class="text-xs/snug">
      <a href="#map-notes" class="text-brand-600 underline hover:text-brand-700">
        {notes === 1 ? 'A note on this map' : `${notes} notes on this map`}
      </a>
    </p>
  {/if}
</div>
