// Ported from WISP 3 (adapted): e2e/test.ts
import { readFileSync } from 'node:fs'

import { test as base } from '@playwright/test'

// Playwright's test, with the outside services a page may call answered here, so an OpenFreeMap,
// USGS or Nominatim outage (or a slow day) can't fail the suite. A test's own page.route() takes
// precedence over these. E2E_LIVE=1 bin/e2e reaches the real services instead.

export { expect } from '@playwright/test'

// A plain green 256 px tile for the satellite basemap
const imageryTile = readFileSync(new URL('./fixtures/imagery-tile.png', import.meta.url))

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
      // Place search (lib/geocode.ts): one place, Hancock, Wisconsin
      await context.route('**/nominatim.openstreetmap.org/**', (route) =>
        route.fulfill({
          json: [
            {
              lat: '44.1336',
              lon: '-89.5168',
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
    await use(context)
  },
})
