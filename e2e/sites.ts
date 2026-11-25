import type { Page } from '@playwright/test'

// Saved sites and the API answers their cards read, for the tests of /sites and the home page (the tests' archive
// is empty, so /risk and /weather/daily are answered here)

const at = '2026-11-01T00:00:00Z'
const site = (lat: number, lng: number, name: string) => ({
  key: `${lat},${lng}`,
  lat,
  lng,
  name,
  addedAt: at,
  updatedAt: at,
})

export const SAVED = {
  version: 1,
  sites: [site(43.07, -89.4, 'Madison'), site(44.1336, -89.5168, 'Hancock'), site(45.65, -89.38, 'Rhinelander')],
  groups: [{ id: 'g1', name: 'Research stations', siteKeys: ['44.1336,-89.5168'] }],
  prefs: { all: {}, groups: {}, sites: {} },
  updatedAt: at,
  syncedAt: null,
}

const meta = { warnings: [] }

export async function stubSiteData(page: Page) {
  await page.route('**/api/v2/risk?*', (route) =>
    route.fulfill({
      json: {
        meta,
        data: {
          model: ['late-blight-dsv', 'early-blight-pdays', 'tar-spot', 'white-mold'],
          name: ['Late blight', 'Early blight P-days', 'Tar spot risk', 'White mold apothecia probability'],
          risk_level: [3, 1, 0, 2],
          risk_label: ['High', 'Low', 'Very low', 'High'],
        },
      },
    }),
  )
  await page.route('**/api/v2/weather/daily?*', (route) => {
    const url = new URL(route.request().url())
    const points = (url.searchParams.get('points') ?? '').split(';').length
    const start = url.searchParams.get('start')!
    const end = url.searchParams.get('end')!
    const data: Record<string, unknown[]> = {
      point: [],
      date: [],
      kind: [],
      air_temperature_max: [],
      air_temperature_min: [],
      precipitation_sum: [],
    }
    for (let p = 0; p < points; p++) {
      for (const [date, kind] of [
        [start, 'partial'],
        [end, 'forecast'],
      ]) {
        data.point.push(p)
        data.date.push(date)
        data.kind.push(kind)
        data.air_temperature_max.push(8.5)
        data.air_temperature_min.push(-2)
        data.precipitation_sum.push(kind === 'partial' ? null : 3.1)
      }
    }
    return route.fulfill({ json: { meta, data } })
  })
}
