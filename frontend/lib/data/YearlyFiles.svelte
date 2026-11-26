<!-- /data's yearly files (track 7 step 7.1): every file `/downloads` lists, a row per variable and a column per
     year with each file's size, the grid file, and how to read them in R and Python (D71's notes: terra reads the
     projection from the file; xarray plots on latitude and longitude with grid.nc's). -->
<script lang="ts">
  import { onDestroy } from 'svelte'

  import type { DownloadsResponse, VariablesResponse } from '@/types/api'

  import { get } from '../api'
  import { formatDate } from '../dates'
  import Failed from '../components/Failed.svelte'
  import { formatBytes } from '../sites/dataRequest'
  import { request } from '../request.svelte'
  import { shortSize, yearlyTable } from './yearlyFiles'

  const listing = request<[DownloadsResponse, VariablesResponse]>()
  const load = () =>
    listing.load((signal) =>
      Promise.all([
        get<DownloadsResponse>('/downloads', undefined, { signal }),
        get<VariablesResponse>('/variables', undefined, { signal }),
      ]),
    )
  load()
  onDestroy(() => listing.cancel())

  const table = $derived(
    listing.value.data ? yearlyTable(listing.value.data[0].data.files, listing.value.data[1].data) : null,
  )
  const gridUrl = $derived(listing.value.data?.[0].data.grid ?? null)

  const R = `library(terra)
tmax <- rast("air_temperature_max_2025.nc")  # 365 layers in °C
july15 <- tmax[[196]]
plot(project(july15, "EPSG:4326"))           # on latitude and longitude`
  const PYTHON = `import xarray as xr

tmax = xr.open_dataset("air_temperature_max_2025.nc")
grid = xr.open_dataset("grid.nc")
tmax = tmax.assign_coords(lat=grid.lat, lon=grid.lon)
tmax.air_temperature_max.sel(time="2025-07-15").plot(x="lon", y="lat")`
</script>

<div class="space-y-4">
  <p class="max-w-prose">
    Each daily variable is one NetCDF file per year over everything we cover, on the 2.5 km grid in its own projection.
    Values are in metric units (°C, mm and so on), packed as whole numbers with a scale factor that GIS software, R and
    Python apply when they read the file. Missing values are left missing, never set to zero.
  </p>

  {#if listing.value.status === 'failed'}
    <Failed {...listing.value} retry={load} />
  {:else if !table}
    <div class="h-48 animate-pulse rounded-md bg-surface-raised" aria-hidden="true"></div>
  {:else if !table.files}
    <p class="text-sm text-ink-muted">The yearly files haven’t been made yet. Check back after the next weekly build.</p>
  {:else}
    <p class="max-w-prose text-sm">
      {`${table.files.toLocaleString('en-US')} files, ${formatBytes(table.bytes)} in all. Past years are whole years. `}
      {#if table.through}
        {`The ${table.years.at(-1)} files run through ${formatDate(table.through, { year: true })} and are rebuilt weekly. `}
      {/if}
      {'A file is rebuilt whenever the data behind it are revised.'}
    </p>
    <div class="max-h-128 overflow-auto rounded-md border border-line" role="region" aria-label="Yearly files">
      <table class="min-w-full border-collapse text-sm">
        <caption class="sr-only">Yearly files by variable and year, with each file’s size</caption>
        <thead class="sticky top-0 z-10 bg-surface-raised">
          <tr>
            <th scope="col" class="sticky left-0 z-20 bg-surface-raised px-3 py-2 text-left font-medium">Variable</th>
            {#each table.years as year (year)}
              <th scope="col" class="p-2 text-right font-medium whitespace-nowrap">
                {year}{#if table.through && year === table.years.at(-1)}<span class="block text-xs font-normal text-ink-muted"
                    >{`to ${formatDate(table.through)}`}</span
                  >{/if}
              </th>
            {/each}
          </tr>
        </thead>
        {#each table.groups as group (group.label)}
          <tbody>
            <tr>
              <th
                scope="colgroup"
                colspan={table.years.length + 1}
                class="sticky left-0 bg-surface px-3 pt-3 pb-1 text-left text-xs font-semibold tracking-wide text-ink-muted uppercase"
              >
                {group.label}
              </th>
            </tr>
            {#each group.rows as row (row.name)}
              <tr class="border-t border-line">
                <th scope="row" class="sticky left-0 bg-surface px-3 py-1.5 text-left font-normal">
                  {row.longName}
                  <code class="block text-xs text-ink-muted">{row.name}</code>
                </th>
                {#each row.files as file, k (k)}
                  <td class="px-2 py-1.5 text-right whitespace-nowrap">
                    {#if file}
                      <a
                        href={file.url}
                        download
                        class="underline hover:text-ink-muted"
                        aria-label={`${row.longName}, ${file.year}: ${shortSize(file.bytes)} NetCDF`}
                      >
                        {shortSize(file.bytes)}
                      </a>
                    {:else}
                      <span class="text-ink-muted" aria-label="No file">–</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        {/each}
      </table>
    </div>
  {/if}

  <section class="space-y-2" aria-labelledby="grid-file-title">
    <h3 id="grid-file-title" class="text-lg font-semibold">The grid file</h3>
    <p class="max-w-prose">
      {'One small file, '}{#if gridUrl}<a href={gridUrl} download class="underline hover:text-ink">grid.nc</a
        >{:else}grid.nc{/if}{', goes with every yearly file. It gives each cell’s latitude and longitude (its center) and its local time zone. You need it only to plot the data on latitude and longitude without a projection library, or to show a cell’s hours on its own clock. Every day in the files runs from midnight to midnight Central Standard Time all year (06:00 to 06:00 UTC), in every cell.'}
    </p>
  </section>

  <section class="space-y-2" aria-labelledby="reading-title">
    <h3 id="reading-title" class="text-lg font-semibold">Reading the files</h3>
    <p class="max-w-prose">In R, the terra package reads the projection and the scale from the yearly file itself:</p>
    <!-- Scroll sideways on a phone; focusable so a keyboard can scroll them -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <pre
      class="overflow-x-auto rounded-md border border-line bg-surface-raised p-3 text-xs focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Reading a yearly file in R"
      tabindex="0"><code>{R}</code></pre>
    <p class="max-w-prose">
      In Python, xarray unpacks the values; add the grid file’s latitude and longitude to plot without a projection
      library:
    </p>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <pre
      class="overflow-x-auto rounded-md border border-line bg-surface-raised p-3 text-xs focus-visible:outline-2 focus-visible:outline-brand-600"
      role="region"
      aria-label="Reading a yearly file in Python"
      tabindex="0"><code>{PYTHON}</code></pre>
    <p class="max-w-prose text-sm text-ink-muted">
      {'GIS software such as QGIS and ArcGIS opens a yearly file as a raster with one band a day. The list of files is also available from the API, for a script that keeps a copy up to date: '}
      <a href="/api/v2/docs" class="underline hover:text-ink">read the API documentation</a>{' for '}<code>/downloads</code>{'.'}
    </p>
  </section>
</div>
