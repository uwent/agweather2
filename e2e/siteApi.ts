import { readFileSync } from 'node:fs'

import type { Page } from '@playwright/test'

// The API answers a site page asks for, from the responses recorded from the dev server for the frontend's tests
// (frontend/test/fixtures/site), since the end-to-end server's archive is empty

const fixture = (name: string) =>
  JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/site/${name}.json`, import.meta.url), 'utf8'))

const ANSWERS: Record<string, string> = {
  '/api/v2/locate': 'locate',
  '/api/v2/weather/daily': 'daily',
  '/api/v2/weather/hourly': 'hourly',
  '/api/v2/weather/totals': 'totals',
  '/api/v2/risk': 'risk',
  // A model at a site (late blight's page)
  '/api/v2/models/late-blight-dsv/run': 'model-late-blight',
  // The Degree days and Data tabs
  '/api/v2/degree-days': 'degree-days',
  '/api/v2/degree-days/presets': 'presets',
  '/api/v2/variables': 'variables',
}

/** Late blight at three saved sites (e2e/sites.ts's SAVED), for its feed: a run over several points */
export async function stubFeedApi(page: Page) {
  await page.route('**/api/v2/models/late-blight-dsv/run?*', (route) =>
    route.fulfill({ json: fixture('feed-late-blight') }),
  )
}

export async function stubSiteApi(page: Page) {
  await page.route('**/api/v2/**', (route) => {
    const name = ANSWERS[new URL(route.request().url()).pathname]
    return name ? route.fulfill({ json: fixture(name) }) : route.fallback()
  })
}
