<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { apiUrl, ApiError, get, isAbort, latestRequests } from '@/lib/api'
  import DataTable from '@/lib/components/DataTable.svelte'
  import type { DataInfo } from '@/lib/map/DataMap.svelte'
  import { currentUnits } from '@/lib/units'

  import { COVERAGE_STATES, countyColumns, countyRows, type SummaryColumns, summaryParams } from './counties'
  import type { TileRequest } from './view'

  // The map's values by county (Phase 7 track 2 step 7), below the fold: each county of a state, summarized from
  // the same map as the tiles (the same day, range and settings), sortable and searchable, with a CSV download.
  // It's the map's accessible equivalent (frontend.md), so it asks for nothing until it's scrolled into view.
  let {
    tiles,
    info,
    title,
    region,
    onregion,
  }: {
    /** The map's request as its tiles have it */
    tiles: TileRequest | null
    /** What the tiles' TileJSON said: the stored unit and any levels' names */
    info: DataInfo | null
    title: string
    /** The state shown, a postal code */
    region: string
    /** The reader chose another state */
    onregion: (code: string) => void
  } = $props()

  const units = $derived(currentUnits())

  let section: HTMLElement | undefined = $state()
  let seen = $state(false)
  $effect(() => {
    if (!section || seen) return
    if (typeof IntersectionObserver === 'undefined') {
      seen = true
      return
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        seen = true
        observer.disconnect()
      }
    })
    observer.observe(section)
    return () => observer.disconnect()
  })

  const params = $derived(tiles ? summaryParams(tiles, region) : null)
  let data = $state<{ columns: SummaryColumns; warnings: string[]; key: string } | null>(null)
  let error = $state<string | null>(null)
  let loading = $state(false)
  const requests = latestRequests()
  onDestroy(() => requests.cancel())

  $effect(() => {
    const [asked, layer, visible] = [params, tiles?.layer, seen]
    if (!asked || !layer || !visible) return
    untrack(() => load(layer, asked))
  })

  async function load(layer: string, asked: Record<string, string | number>) {
    loading = true
    error = null
    try {
      const body = await requests.run('summary', (signal) =>
        get<{ data: SummaryColumns; meta: { warnings?: string[] } }>(`/summaries/${layer}`, asked, { signal }),
      )
      data = { columns: body.data, warnings: body.meta.warnings ?? [], key: `${layer}?${JSON.stringify(asked)}` }
      loading = false
    } catch (failure) {
      if (isAbort(failure)) return
      data = null
      error = failure instanceof ApiError ? failure.message : String(failure)
      loading = false
    }
  }

  const unit = $derived(info?.unit ?? '')
  const rows = $derived(data && unit ? countyRows(data.columns, unit) : [])
  const levelled = $derived(rows.some((r) => Object.keys(r.levels).length > 0))
  const columns = $derived(countyColumns(rows, { unit, units, categories: info?.categories ?? null }))
  const stateName = $derived(COVERAGE_STATES.find((s) => s.code === region)?.name ?? region)
  const csv = $derived(tiles && params ? apiUrl(`/summaries/${tiles.layer}`, { ...params, format: 'csv' }) : null)
  let sort = $state<{ key: string; direction: 'asc' | 'desc' } | null>({ key: 'name', direction: 'asc' })
</script>

<section bind:this={section} class="space-y-3" aria-labelledby="counties-heading" id="counties">
  <div class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h2 id="counties-heading" class="text-lg font-semibold">This map by county</h2>
      <p class="max-w-prose text-sm text-ink-muted">
        {levelled
          ? `${title} in each county of ${stateName}: the highest level on the county's land, and how much of it is at each level.`
          : `${title} in each county of ${stateName}: the average, lowest and highest over the county's land.`}
      </p>
    </div>
    <div class="flex flex-wrap items-end gap-3 text-sm">
      <div class="space-y-1">
        <label for="counties-state" class="block font-medium">State</label>
        <select
          id="counties-state"
          class="rounded-md sm:text-sm"
          value={region}
          onchange={(event) => onregion(event.currentTarget.value)}
        >
          {#each COVERAGE_STATES as s (s.code)}<option value={s.code}>{s.name}</option>{/each}
        </select>
      </div>
      {#if csv}
        <a href={csv} class="py-2 text-brand-600 underline hover:text-brand-700" download>
          Download as CSV{units.system === 'metric' ? ' (US units)' : ''}
        </a>
      {/if}
    </div>
  </div>

  {#if error}
    <p class="text-sm text-danger-ink" role="alert">{error}</p>
  {:else if !data}
    <p class="text-sm text-ink-muted" role="status">
      {loading || !seen ? `Summarizing the map by county in ${stateName}…` : ''}
    </p>
  {:else}
    {#if loading}<p class="text-sm text-ink-muted" role="status">Updating the table…</p>{/if}
    {#each data.warnings as warning (warning)}<p class="max-w-prose text-sm text-ink-muted">{warning}</p>{/each}
    <DataTable
      {rows}
      {columns}
      rowKey={(row) => row.fips}
      label="{title} by county in {stateName}"
      searchPlaceholder="Find a county"
      bind:sort
      nowrap
      maxHeight="28rem"
    />
  {/if}
</section>
