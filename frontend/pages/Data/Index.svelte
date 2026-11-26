<!-- Data and downloads (/data, Phase 7 track 7 step 7.1): weather at the reader's locations (the site page's Data
     tab for up to 50 at once), maps as data files (a layer over an area, sized before it's asked for), and the
     yearly files of every daily variable. The page's data come from the API; the props carry the API's limits,
     the grid's projection and (deferred) the states and counties a map file can cover (web.datapage). -->
<script lang="ts">
  import { onDestroy } from 'svelte'

  import CollapsibleSection from '@/lib/components/CollapsibleSection.svelte'
  import GridBuilder from '@/lib/data/GridBuilder.svelte'
  import LocationPicker from '@/lib/data/LocationPicker.svelte'
  import type { Chosen } from '@/lib/data/locations'
  import PointsBuilder from '@/lib/data/PointsBuilder.svelte'
  import YearlyFiles from '@/lib/data/YearlyFiles.svelte'
  import { today as gridToday } from '@/lib/dates'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { DataPageProps } from '@/types'

  let props: DataPageProps = $props()

  const today = gridToday()
  const view = viewState({
    get: field(codecs.oneOf(['daily', 'hourly', 'totals', 'degree-days', 'model'] as const), 'daily'),
  })
  onDestroy(() => view.destroy())

  let chosen = $state<Chosen[]>([])
  const points = $derived(chosen.map((c) => ({ lat: c.lat, lng: c.lng })))

  const contents = [
    { id: 'locations', title: 'Weather at your locations' },
    { id: 'maps', title: 'Maps as data files' },
    { id: 'yearly', title: 'Yearly files' },
  ]
</script>

<svelte:head>
  <title>Data and downloads · AgWeather</title>
  <meta
    name="description"
    content="Download AgWeather's weather, degree days and model results for your locations, maps as NetCDF, GeoTIFF or CSV files, and yearly files of every daily variable."
  />
</svelte:head>

<article class="space-y-8">
  <header class="max-w-prose space-y-3">
    <h1 class="text-3xl font-semibold">Data and downloads</h1>
    <p class="text-lg">
      Download the weather, degree days and model results at your locations, a map’s values as a data file, or the
      archive’s daily weather a year at a time.
    </p>
    <nav aria-label="On this page">
      <ul class="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {#each contents as section (section.id)}
          <li><a href="#{section.id}" class="underline hover:text-ink-muted">{section.title}</a></li>
        {/each}
      </ul>
    </nav>
    <p class="text-sm text-ink-muted">
      {'Each download shows its address, so you can fetch it again from a script. The data come from our public API, which you can use directly; '}
      <a href="/api/v2/docs" class="underline hover:text-ink">read its documentation</a
      >{'. The weather is on a grid of cells about 2.5 km (1.5 miles) on a side, so a location’s values describe its cell as a whole. '}
      <a href="/methods" class="underline hover:text-ink">Read how the data are made</a>{'.'}
    </p>
  </header>

  <CollapsibleSection id="locations" title="Weather at your locations">
    <div class="space-y-6">
      <p class="max-w-prose">
        Choose up to 50 locations, then what to download: daily or hourly weather, totals over a period, degree days or
        a model’s results. Each location gets its own rows in one CSV or JSON file.
      </p>
      <LocationPicker bind:chosen />
      {#if points.length}
        <PointsBuilder
          {points}
          {today}
          models={props.models}
          kind={$view.get}
          onkind={(get) => view.patch({ get })}
          headingLevel={3}
        />
      {/if}
    </div>
  </CollapsibleSection>

  <CollapsibleSection id="maps" title="Maps as data files">
    <div class="space-y-4">
      <p class="max-w-prose">
        Download a map’s values for a day or a range of days, over everything we cover, a state, a county or a box you
        choose. NetCDF and GeoTIFF files open in GIS software, R and Python; CSV and JSON give a row for each grid cell.
        The size of the file is shown before you download it.
      </p>
      <GridBuilder {today} limits={props.limits} projection={props.projection} areas={props.areas} />
    </div>
  </CollapsibleSection>

  <CollapsibleSection id="yearly" title="Yearly files">
    <YearlyFiles />
  </CollapsibleSection>
</article>
