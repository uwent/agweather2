import { readFileSync } from 'node:fs'

import type { Page } from '@playwright/test'

// The API answers /data asks for, from the responses recorded from the dev server for the frontend's tests, since
// the end-to-end server's archive is empty (so the states and counties are none, and no yearly files are built)

const fixture = (path: string) =>
  JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/${path}.json`, import.meta.url), 'utf8'))

const ANSWERS: Record<string, string> = {
  '/api/v2/variables': 'site/variables',
  '/api/v2/layers': 'layers',
  '/api/v2/downloads': 'downloads',
  '/api/v2/weather/daily': 'site/daily',
}

export async function stubDataApi(page: Page) {
  await page.route('**/api/v2/**', (route) => {
    const name = ANSWERS[new URL(route.request().url()).pathname]
    return name ? route.fulfill({ json: fixture(name) }) : route.fallback()
  })
}
