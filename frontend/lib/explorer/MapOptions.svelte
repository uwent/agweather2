<script lang="ts">
  import { untrack } from 'svelte'

  import type { DataInfo } from '@/lib/map/DataMap.svelte'
  import { currentUnits, parseNumber } from '@/lib/units'
  import type { LayerInfo, PaletteInfo } from '@/types/api'

  import { type ExplorerView, rollable, ROLLS, spanFor } from './view'

  // Map options (Phase 7 track 2 step 4), behind a disclosure: smoothing over 7, 14 or 28 days, and the colors'
  // palette and range. Colors change in the browser without a new request (D119).
  let {
    view,
    layer,
    info,
    palettes,
    onchange,
  }: {
    view: ExplorerView
    layer: LayerInfo
    info: DataInfo | null
    palettes: PaletteInfo[]
    onchange: (changes: Partial<ExplorerView>) => void
  } = $props()

  const units = $derived(currentUnits())
  const smoothing = $derived(rollable(layer, spanFor(view, layer)))
  const categorical = $derived(info?.kind === 'categorical')

  // A categorical map takes only a categorical palette with as many levels; a continuous one no categorical one
  const choices = $derived.by(() => {
    if (!info) return []
    const levels = palettes.find((p) => p.id === info.defaultPalette.replace(/_r$/, ''))?.colors.length
    return palettes.filter((p) =>
      categorical ? p.kind === 'categorical' && p.colors.length === levels : p.kind !== 'categorical',
    )
  })

  const scaleMode = $derived(view.scale === null ? 'auto' : view.scale === 'default' ? 'default' : 'custom')
  let low = $state('')
  let high = $state('')
  $effect(() => {
    const [a, b] = (view.scale ?? '').split(',')
    untrack(() => {
      if (scaleMode === 'custom') [low, high] = [a ?? '', b ?? '']
    })
  })
  function setScale(mode: string) {
    if (mode === 'custom') {
      low ||= info ? String(Math.round(info.low)) : ''
      high ||= info ? String(Math.round(info.high)) : ''
      onchange({ scale: `${low},${high}` })
    } else onchange({ scale: mode === 'auto' ? null : mode })
  }
  function setRange() {
    const [a, b] = [parseNumber(low), parseNumber(high)]
    if (a.ok && b.ok) onchange({ scale: `${a.value ?? ''},${b.value ?? ''}` })
  }
  const unitLabel = $derived(
    info && info.unit !== 'date' && info.unit !== 'index' ? ` (${units.label(info.unit)})` : '',
  )
</script>

<details class="group rounded-md border border-line">
  <summary class="cursor-pointer px-3 py-2 text-sm font-semibold">Map options</summary>
  <div class="space-y-3 border-t border-line p-3 text-sm">
    {#if smoothing}
      <div class="flex flex-wrap items-end gap-2">
        <div class="space-y-1">
          <label for="map-roll" class="block font-medium">Smoothing</label>
          <select
            id="map-roll"
            class="rounded-md sm:text-sm"
            value={view.roll ?? ''}
            onchange={(event) =>
              onchange({ roll: event.currentTarget.value ? Number(event.currentTarget.value) : null })}
          >
            <option value="">None: each day</option>
            {#each ROLLS as days (days)}<option value={days}>{days}-day window</option>{/each}
          </select>
        </div>
        {#if view.roll}
          <div class="space-y-1">
            <label for="map-align" class="block font-medium">Window</label>
            <select
              id="map-align"
              class="rounded-md sm:text-sm"
              value={view.align}
              onchange={(event) => onchange({ align: event.currentTarget.value as ExplorerView['align'] })}
            >
              <option value="trailing">Ending on the date</option>
              <option value="centered">Centered on the date</option>
            </select>
          </div>
        {/if}
      </div>
      {#if view.roll}
        <p class="text-xs text-ink-muted">
          Values that add up over days, such as rain, are totaled over the window; others are averaged.
        </p>
      {/if}
    {/if}

    {#if info}
      <div class="space-y-1">
        <label for="map-palette" class="block font-medium">Colors</label>
        <select
          id="map-palette"
          class="block w-full rounded-md sm:text-sm"
          value={view.palette ?? ''}
          onchange={(event) => onchange({ palette: event.currentTarget.value || null })}
        >
          <option value="">The map's own ({info.defaultPalette})</option>
          {#each choices as p (p.id)}
            <option value={p.id}>{p.id}{p.colorblind_safe ? '' : ' (not color-blind safe)'}</option>
            <option value="{p.id}_r">{p.id}, reversed{p.colorblind_safe ? '' : ' (not color-blind safe)'}</option>
          {/each}
        </select>
      </div>
      {#if !categorical}
        <div class="space-y-1">
          <label for="map-scale" class="block font-medium">Color range</label>
          <select
            id="map-scale"
            class="block w-full rounded-md sm:text-sm"
            value={scaleMode}
            onchange={(event) => setScale(event.currentTarget.value)}
          >
            <option value="auto">Fit to this map</option>
            <option value="default">Fixed, to compare days</option>
            <option value="custom">Your own low and high</option>
          </select>
        </div>
        {#if scaleMode === 'custom'}
          <div class="flex gap-2">
            <div class="space-y-1">
              <label for="map-low" class="block font-medium">Low{unitLabel}</label>
              <input
                id="map-low"
                class="w-24 rounded-md sm:text-sm"
                inputmode="decimal"
                bind:value={low}
                onchange={setRange}
              />
            </div>
            <div class="space-y-1">
              <label for="map-high" class="block font-medium">High{unitLabel}</label>
              <input
                id="map-high"
                class="w-24 rounded-md sm:text-sm"
                inputmode="decimal"
                bind:value={high}
                onchange={setRange}
              />
            </div>
          </div>
        {/if}
      {/if}
    {/if}
  </div>
</details>
