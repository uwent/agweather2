<!-- Ported from WISP 3: app/frontend/lib/components/Spinner.svelte -->
<script lang="ts">
  // A small spinner beside text that says what's in progress (decorative; the text carries the meaning).
  // It keeps spinning under reduced motion (.keep-motion in application.css): it's small and spins in
  // place, unlike the slides and scrolling the setting stops.
  let { class: className = '' }: { class?: string } = $props()
</script>

<svg
  class="keep-motion inline-block size-3.5 shrink-0 animate-spin {className}"
  viewBox="0 0 16 16"
  fill="none"
  aria-hidden="true"
>
  <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-opacity="0.25" stroke-width="2" />
  <path d="M14.5 8A6.5 6.5 0 0 0 8 1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
</svg>
