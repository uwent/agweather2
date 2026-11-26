// Ported from WISP 3 (adapted): e2e/test.ts
import { readFileSync } from 'node:fs'

import { test as base } from '@playwright/test'

// Playwright's test, with the outside services a page may call answered here, so an OpenFreeMap,
// USGS or Nominatim outage (or a slow day) can't fail the suite. A test's own page.route() takes
// precedence over these. E2E_LIVE=1 bin/e2e reaches the real services instead.

export { expect } from '@playwright/test'

// A plain green 256 px tile for the satellite basemap
const imageryTile = readFileSync(new URL('./fixtures/imagery-tile.png', import.meta.url))
// A data tile of the daily minimum temperature over Wisconsin (the map explorer)
const dataTile = readFileSync(new URL('./fixtures/data-tile.png', import.meta.url))

const cors = { 'Access-Control-Allow-Origin': '*' }

export const test = base.extend({
  context: async ({ context }, use) => {
    if (!process.env.E2E_LIVE) {
      // OpenFreeMap's vector tiles (the street map, the roads over the imagery): empty, so maps load
      // at once. Its fonts and street style stay live.
      await context.route('**/tiles.openfreemap.org/planet', (route) =>
        route.fulfill({
          json: { tilejson: '3.0.0', tiles: ['https://tiles.openfreemap.org/planet/e2e/{z}/{x}/{y}.pbf'], maxzoom: 14 },
          headers: cors,
        }),
      )
      await context.route('**/tiles.openfreemap.org/planet/**', (route) =>
        route.fulfill({ body: Buffer.alloc(0), contentType: 'application/x-protobuf', headers: cors }),
      )
      // The USGS imagery basemap's tiles (lib/map/basemaps.ts)
      await context.route('**/basemap.nationalmap.gov/**', (route) =>
        route.fulfill({ body: imageryTile, contentType: 'image/png', headers: cors }),
      )
      // The API's static maps (the home page's headline maps): the tests' archive is empty, so a plain image
      await context.route('**/api/v2/maps/*.png*', (route) =>
        route.fulfill({ body: imageryTile, contentType: 'image/png' }),
      )
      // Place search (lib/geocode.ts): one place, Hancock, Wisconsin
      await context.route('**/nominatim.openstreetmap.org/**', (route) =>
        route.fulfill({
          json: [
            {
              lat: '44.1336',
              lon: '-89.5168',
              boundingbox: ['44.1236', '44.1436', '-89.5268', '-89.5068'],
              display_name: 'Hancock, Waushara County, Wisconsin, United States',
              name: 'Hancock',
              type: 'village',
              address: { village: 'Hancock', county: 'Waushara County', state: 'Wisconsin', country_code: 'us' },
            },
          ],
          headers: cors,
        }),
      )
    }
    // The map explorer's API calls, answered from recorded responses (the test server has no archive). Only the
    // endpoints the map uses: the rest of the API answers for real.
    const api = (name: string) => JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'))
    const recorded: [string, () => unknown][] = [
      ['**/api/v2/layers', () => api('../frontend/test/fixtures/layers.json')],
      ['**/api/v2/models', () => api('../frontend/test/fixtures/models.json')],
      ['**/api/v2/crops', () => api('../frontend/test/fixtures/crops.json')],
      ['**/api/v2/degree-days/presets', () => api('../frontend/test/fixtures/presets.json')],
      ['**/api/v2/palettes', () => api('./fixtures/palettes.json')],
      ['**/api/v2/tiles/*.json?*', () => api('./fixtures/tilejson.json')],
      ['**/api/v2/locate?*', () => api('./fixtures/locate.json')],
      ['**/api/v2/weather/daily?*', () => api('./fixtures/daily.json')],
      ['**/api/v2/degree-days?*', () => api('./fixtures/daily.json')],
      ['**/api/v2/summaries/*?*', () => api('./fixtures/summaries.json')],
    ]
    for (const [pattern, body] of recorded) await context.route(pattern, (route) => route.fulfill({ json: body() }))
    await context.route('**/api/v2/tiles/*/*/*/*/*.png*', (route) =>
      route.fulfill({ body: dataTile, contentType: 'image/png' }),
    )
    await use(context)
  },
})
