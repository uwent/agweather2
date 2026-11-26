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
  // The oak wilt tool (Madison, January 1 to August 31, 2026)
  '/api/v2/models/oak-wilt-vectors/run': 'model-oak-wilt',
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

/** The freeze tool's answers (Madison, recorded for frontend/test/fixtures/climate), with the site's */
export async function stubFreezeApi(page: Page) {
  await stubSiteApi(page)
  const climate = (name: string) =>
    JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/climate/${name}.json`, import.meta.url), 'utf8'))
  const answers: Record<string, string> = {
    '/api/v2/freeze': 'freeze',
    '/api/v2/climate/frost': 'frost',
    '/api/v2/climate/frost/chances': 'chances',
  }
  await page.route('**/api/v2/**', (route) => {
    const name = answers[new URL(route.request().url()).pathname]
    return name ? route.fulfill({ json: climate(name) }) : route.fallback()
  })
}

/** The crop GDD outlook's answers (Madison, corn planted May 8, recorded for frontend/test/fixtures/tools), with the
 * site's and the freeze tool's */
export async function stubCropGddApi(page: Page) {
  await stubFreezeApi(page)
  const tools = (name: string) =>
    JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/tools/${name}.json`, import.meta.url), 'utf8'))
  await page.route('**/api/v2/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v2/models/corn-stages/run') return route.fulfill({ json: tools('corn-run') })
    if (url.pathname === '/api/v2/climate/compare') return route.fulfill({ json: tools('compare-corn') })
    if (url.pathname === '/api/v2/degree-days')
      return route.fulfill({
        json: tools(url.searchParams.get('biofix')?.startsWith('2012') ? 'year-2012' : 'degree-days-soybean'),
      })
    return route.fallback()
  })
}

/** The potato volunteer tool's answers (Hancock, winter 2025–26, recorded for frontend/test/fixtures/tools), with
 * the site's */
export async function stubPotatoApi(page: Page) {
  await stubSiteApi(page)
  const tools = (name: string) =>
    JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/tools/${name}.json`, import.meta.url), 'utf8'))
  const answers: Record<string, string> = {
    '/api/v2/models/potato-volunteer/run': 'potato-volunteer',
    '/api/v2/weather/daily': 'potato-volunteer-air',
  }
  await page.route('**/api/v2/**', (route) => {
    const name = answers[new URL(route.request().url()).pathname]
    return name ? route.fulfill({ json: tools(name) }) : route.fallback()
  })
}

/** The alfalfa planner's answers (Madison, November 26, 2026, recorded for frontend/test/fixtures/alfalfa), with
 * the site's */
export async function stubAlfalfaApi(page: Page) {
  await stubSiteApi(page)
  const alfalfa = (name: string) =>
    JSON.parse(readFileSync(new URL(`../frontend/test/fixtures/alfalfa/${name}.json`, import.meta.url), 'utf8'))
  await page.route('**/api/v2/models/alfalfa-growth/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/run')) return route.fulfill({ json: alfalfa('run-cut') })
    return route.fulfill({ json: alfalfa(url.searchParams.has('cuts') ? 'plan-cuts' : 'plan') })
  })
}
