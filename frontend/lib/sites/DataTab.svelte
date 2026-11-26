<script lang="ts">
  import type { SiteModel } from '@/types'

  import PointsBuilder from '../data/PointsBuilder.svelte'
  import type { DataKind } from './dataRequest'

  export type DataView = { get: DataKind }

  // A site's Data tab (track 3 step 10): the download builder (lib/data/PointsBuilder.svelte) for this point. What to
  // download is the page's view.
  let {
    lat,
    lng,
    today,
    models,
    view,
    onchange,
  }: {
    lat: number
    lng: number
    today: string
    models: SiteModel[]
    view: DataView
    onchange: (changes: Partial<DataView>) => void
  } = $props()

  const points = $derived([{ lat, lng }])
</script>

<PointsBuilder {points} {today} {models} kind={view.get} onkind={(get) => onchange({ get })}>
  {#snippet intro()}
    <p class="max-w-prose text-sm text-ink-muted">
      Download this location’s weather, degree days or a model’s results as a CSV file for a spreadsheet, or as JSON.
      The address of each download is shown below, so you can use it in a script or fetch it again later.
    </p>
  {/snippet}
</PointsBuilder>
