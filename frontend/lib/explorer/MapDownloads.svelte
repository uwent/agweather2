<script lang="ts">
  import type { DownloadLinks } from './downloads'

  // The map's data files and its tiles for GIS (frontend.md: "GeoTIFF or NetCDF of the view; TileJSON for GIS"),
  // behind a disclosure under Map options. The links follow the map: its layer, date, settings and the area in view.
  let { links }: { links: DownloadLinks } = $props()

  const uid = $props.id()
  const origin = typeof location === 'undefined' ? '' : location.origin
  const tilejson = $derived(`${origin}${links.tilejson}`)
  const unitsWords = $derived(links.system === 'us' ? 'US units (°F, inches)' : 'metric units (°C, millimeters)')
</script>

<details class="rounded-md border border-line" data-testid="map-downloads">
  <summary class="cursor-pointer px-3 py-2 text-sm font-semibold">Download</summary>
  <div class="space-y-3 border-t border-line p-3 text-sm">
    <p>
      {links.inView
        ? 'Download the values of this map for the area in view, '
        : 'Download the values of this map for the whole area we cover, '}
      {`with each 2.5 km cell's value in ${unitsWords}. Move or zoom the map to change the area.`}
    </p>
    <ul class="space-y-1">
      <li>
        <a href={links.geotiff} download class="text-brand-600 underline hover:text-brand-700">GeoTIFF</a>
        <span class="text-ink-muted">{' for ArcGIS, QGIS and other GIS software'}</span>
      </li>
      <li>
        <a href={links.netcdf} download class="text-brand-600 underline hover:text-brand-700">NetCDF</a>
        <span class="text-ink-muted">{' for R, Python and Panoply'}</span>
      </li>
    </ul>
    <div class="space-y-1">
      <label for="tilejson-{uid}" class="block font-medium">Map tiles for web maps and GIS (TileJSON)</label>
      <p class="text-xs text-ink-muted">
        Add this address to MapLibre, Leaflet or other software that reads TileJSON to show this map, in these colors,
        under your own layers.
      </p>
      <input
        id="tilejson-{uid}"
        type="text"
        readonly
        value={tilejson}
        class="block w-full rounded-md border border-line bg-surface px-2 py-1 text-xs text-ink"
        onfocus={(event) => event.currentTarget.select()}
      />
    </div>
    <p class="text-xs text-ink-muted">
      The files and tiles come from the AgWeather API. See the
      <a href="/api/v2/docs" class="underline">API documentation</a> for the other settings and formats.
    </p>
  </div>
</details>
