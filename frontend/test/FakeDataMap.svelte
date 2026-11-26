<script lang="ts">
  // A stand-in for lib/map/DataMap.svelte in component tests (jsdom has no WebGL): the tiles' request as data
  // attributes, a button that picks a cell as a click on the map would, and `valueAt` answering a fixed value.
  import type { Snippet } from 'svelte'

  type Pick = { lat: number; lng: number; value: number | 'none' | null; unit: string; text: string }

  let {
    layer,
    time,
    stat = null,
    params = {},
    label,
    onpick,
    header,
  }: {
    layer: string
    time: string
    stat?: string | null
    params?: Record<string, unknown>
    label: string
    onpick?: (pick: Pick) => void
    header?: Snippet
    [key: string]: unknown
  } = $props()

  /** The value every cell has */
  const VALUE: Pick = { lat: 0, lng: 0, value: 120.5, unit: 'degF_day', text: '+121 °F·d' }

  export async function valueAt(lat: number, lng: number): Promise<Pick> {
    return { ...VALUE, lat, lng }
  }
</script>

<div
  role="region"
  aria-label={label}
  data-testid="data-map"
  data-layer={layer}
  data-time={time}
  data-stat={stat ?? ''}
  data-params={JSON.stringify(params)}
>
  {@render header?.()}
  <button type="button" onclick={() => onpick?.({ ...VALUE, lat: 44.12, lng: -89.52 })}>Click the map</button>
</div>
