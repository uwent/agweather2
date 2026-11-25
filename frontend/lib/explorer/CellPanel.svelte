<script lang="ts" module>
  /** What `/locate` says of a clicked point (the fields the panel reads) */
  export type CellPlace = {
    county: string | null
    state: string | null
    in_box: boolean
    cell: { lat: number; lng: number } | null
    corners: [number, number][] | null
  }
</script>

<script lang="ts">
  // The clicked cell in words (Phase 7 track 2 step 6): its value first, then where it is ("Dane County, WI ·
  // 43.07° N, 89.40° W"), with a link to its chart below. A site page link comes with track 3.
  let {
    value,
    title,
    when,
    place,
    placeError,
    onclear,
  }: {
    /** The value as the reader sees it ("38 °F", "High"), or null while it loads */
    value: string | null
    title: string
    when: string
    place: CellPlace | null
    placeError: string | null
    onclear: () => void
  } = $props()

  const where = $derived.by(() => {
    if (!place) return null
    const county = [place.county, place.state].filter(Boolean).join(', ')
    const at = place.cell
      ? `${Math.abs(place.cell.lat).toFixed(2)}° ${place.cell.lat >= 0 ? 'N' : 'S'}, ${Math.abs(place.cell.lng).toFixed(2)}° ${place.cell.lng < 0 ? 'W' : 'E'}`
      : ''
    return [county, at].filter(Boolean).join(' · ')
  })
</script>

<section class="rounded-md border border-line bg-surface p-3" aria-labelledby="cell-heading" data-testid="cell-panel">
  <div class="flex items-start justify-between gap-2">
    <h2 id="cell-heading" class="text-base font-semibold">The cell you chose</h2>
    <button
      type="button"
      class="rounded-md px-1.5 text-sm text-ink-muted hover:bg-brand-50 hover:text-ink"
      aria-label="Clear the cell you chose"
      onclick={onclear}
    >
      ✕
    </button>
  </div>
  <p class="mt-1 text-lg font-semibold">{value ?? 'Loading…'}</p>
  <p class="text-sm">{title}, {when}</p>
  {#if where}<p class="text-sm text-ink-muted">{where}</p>{/if}
  {#if placeError}<p class="text-sm text-danger-ink">{placeError}</p>{/if}
  {#if place && !place.in_box}
    <p class="mt-1 text-sm text-ink-muted">
      This place is outside the area AgWeather maps, so the map has no value here.
    </p>
  {/if}
  <p class="mt-2 text-sm">
    <a href="#cell-chart" class="underline">See this cell's recent days and forecast</a>
    <!-- TODO(track 3): "Open this site" through routes.site() once the site pages land -->
  </p>
</section>
