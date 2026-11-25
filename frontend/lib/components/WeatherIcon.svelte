<!-- WISP 3: app/frontend/lib/components/WeatherIcon.svelte (adapted: our skies, and the chart tokens' colors) -->
<script lang="ts">
  import type { Sky } from '../forecast'

  // A day's sky as a small line icon (ForecastStrip). Decorative: the strip words the sky beside it.
  let { sky, class: className = 'size-8' }: { sky: Sky; class?: string } = $props()

  // The cloud, raised when something falls from it
  const CLOUD = 'M7 17.5h10.5a3.5 3.5 0 0 0 .3-7 5.5 5.5 0 0 0-10.6 1.2A2.9 2.9 0 0 0 7 17.5z'
  const falls = $derived(['rain', 'showers', 'snow'].includes(sky))
</script>

<svg
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.6"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  class="{className} shrink-0 text-ink-muted"
>
  {#if sky === 'clear'}
    <g class="text-chart-et">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
    </g>
  {:else if sky === 'partly' || sky === 'showers'}
    <g class="text-chart-et">
      <circle cx="8" cy="8" r="3" />
      <path d="M8 2.5v1M2.5 8h1M4.1 4.1l.7.7M11.9 4.1l-.7.7" />
    </g>
    <path d={CLOUD} transform="translate(1 {sky === 'showers' ? -1.5 : 1})" class="fill-surface-raised" />
  {:else}
    <path d={CLOUD} transform={falls ? 'translate(0 -3.5)' : undefined} />
  {/if}

  {#if sky === 'rain' || sky === 'showers'}
    <path d="M9 17l-1 3M13 17l-1 3M17 17l-1 3" class="text-chart-precipitation" />
  {:else if sky === 'snow'}
    <path d="M8 17.5v3M6.7 18.25l2.6 1.5M6.7 19.75l2.6-1.5M16 17.5v3M14.7 18.25l2.6 1.5M14.7 19.75l2.6-1.5" />
  {/if}
</svg>
