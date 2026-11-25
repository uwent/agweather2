<!-- WISP 3: app/frontend/lib/map/OverviewLayers.svelte (adapted: its data overlays only, without WISP's systems, zones and example farm) -->
<script lang="ts">
  import type { Units } from '@/lib/units'

  import type { MapOverlays } from './mapOverlays.svelte'
  import OverlayLegend from './OverlayLegend.svelte'
  import { type Overlay, type OverlayId, OVERLAYS } from './overlays'
  import type { MapPrefs } from './prefs'

  // A map's data overlays, in its Layers panel (MapLayersButton) above the basemap's: one at a time
  // (radar, recent rain, forecast rain or the Drought Monitor), the one shown with its legend, time,
  // opacity and source
  let { prefs = $bindable(), overlays, units }: { prefs: MapPrefs; overlays: MapOverlays; units: Units } = $props()

  const shown = $derived(OVERLAYS.find((overlay) => overlay.id === prefs.overlay) ?? null)

  const STATUS_TEXT = { loading: 'Loading…', ready: '', unavailable: 'Unavailable' }
</script>

{#snippet details(overlay: Overlay)}
  {@const status = overlays.status[overlay.id]}
  <div class="border-line mt-2 space-y-2 border-l-2 pl-3">
    {#if status === 'unavailable'}
      <p class="text-danger text-xs">
        This layer isn't loading right now. Switch it off and on to try again, or check back later.
      </p>
    {/if}
    {#if overlays.times[overlay.id]}<p class="text-xs font-medium">{overlays.times[overlay.id]}</p>{/if}
    <OverlayLegend legend={overlay.legend} {units} />
    <p class="text-ink-muted text-xs">{overlay.description}</p>
    <label class="flex items-center gap-2 text-xs">
      <span class="text-ink-muted">Opacity</span>
      <input
        type="range"
        min="0.1"
        max="1"
        step="0.05"
        class="flex-1"
        value={prefs.opacity[overlay.id] ?? overlay.opacity}
        oninput={(event) => (prefs.opacity = { ...prefs.opacity, [overlay.id]: Number(event.currentTarget.value) })}
      />
    </label>
    <p class="text-xs">
      Source: <a href={overlay.credit.url} target="_blank" rel="noopener" class="text-brand-600 underline">
        {overlay.credit.name}
      </a>
    </p>
  </div>
{/snippet}

{#snippet mark(id: OverlayId)}
  {@const status = overlays.status[id]}
  {#if status && STATUS_TEXT[status]}
    <span class="ml-auto text-xs {status === 'unavailable' ? 'text-danger' : 'text-ink-muted'}">
      {STATUS_TEXT[status]}
    </span>
  {/if}
{/snippet}

<fieldset class="space-y-1">
  <legend class="text-ink-muted mb-1 text-xs font-medium tracking-wide uppercase">Data overlays</legend>
  <p class="text-ink-muted mb-1.5 text-xs">
    Point at the map, or tap it, to see the overlay's value there. Overlays come straight from public services, not from
    AgWeather, and can be slow or unavailable at times.
  </p>
  <label class="flex items-center gap-2">
    <input type="radio" name="map-overlay" checked={prefs.overlay === null} onchange={() => (prefs.overlay = null)} />
    None
  </label>
  {#each OVERLAYS as overlay (overlay.id)}
    <label class="flex items-center gap-2">
      <input
        type="radio"
        name="map-overlay"
        checked={prefs.overlay === overlay.id}
        onchange={() => (prefs.overlay = overlay.id)}
      />
      {overlay.name}
      {@render mark(overlay.id)}
    </label>
  {/each}
  {#if shown}{@render details(shown)}{/if}
</fieldset>
