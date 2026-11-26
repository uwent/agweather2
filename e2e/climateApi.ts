import { readFileSync } from 'node:fs'

import type { Page } from '@playwright/test'

// The climate answers a site's Climate tab asks for, from the responses recorded at Madison for the frontend's tests
// (frontend/test/fixtures/climate), since the end-to-end server's archive is empty. `/climate/normals` and
// `/climate/compare` answer by what's asked: counts, months, a span of days or the whole year.

const fixture = (name: string) =>
  JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/climate/${name}.json`, import.meta.url), 'utf8'))

function answer(path: string, query: URLSearchParams): string | null {
  switch (path) {
    case '/api/v2/climate/compare':
      return query.has('count') ? 'counts' : 'compare'
    case '/api/v2/climate/normals':
      if (query.has('count')) return 'counts-months'
      if (query.get('interval') === 'month') return 'months'
      return query.has('start') ? 'normal-span' : 'normal-year'
    case '/api/v2/climate/frost':
      return 'frost'
    case '/api/v2/climate/frost/chances':
      return 'chances'
    case '/api/v2/freeze':
      return 'freeze'
    default:
      return null
  }
}

/** Climate's answers; the weather a section asks for (`/weather/daily` from 60 days back) too */
export async function stubClimateApi(page: Page) {
  await page.route('**/api/v2/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v2/weather/daily' && url.searchParams.get('units') === 'us')
      return route.fulfill({ json: fixture('recent') })
    const name = answer(url.pathname, url.searchParams)
    return name ? route.fulfill({ json: fixture(name) }) : route.fallback()
  })
}
