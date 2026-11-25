<!-- WISP 3: app/frontend/lib/map/MapPanel.svelte (copied) -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  // The shell of the Map tab's panels (a system's, a farm or group's, a weather zone's): a header
  // (header, holding the title with id titleId) with a close button, over a scrolling body. A
  // floating panel on wide screens, a sheet along the bottom on phones. The page focuses it
  // (data-map-panel) when it's opened from the keyboard.
  let {
    titleId,
    header,
    children,
    onclose,
  }: { titleId: string; header: Snippet; children: Snippet; onclose: () => void } = $props()
</script>

<section
  class="border-line bg-surface focus-visible:outline-brand-500 pointer-events-auto flex max-h-full flex-col overflow-hidden rounded-lg border
    shadow-xl focus-visible:outline-2"
  aria-labelledby={titleId}
  tabindex="-1"
  data-map-panel
>
  <header class="border-line bg-surface-raised flex items-start justify-between gap-2 border-b px-3 py-2">
    <div class="min-w-0">{@render header()}</div>
    <button
      type="button"
      class="text-ink-muted hover:bg-surface hover:text-ink -mr-1 rounded-md px-2 py-1 text-lg leading-none"
      aria-label="Close"
      onclick={onclose}
    >
      ×
    </button>
  </header>
  <div class="space-y-3 overflow-y-auto p-3">{@render children()}</div>
</section>
