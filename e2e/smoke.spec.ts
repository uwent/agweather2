import { readFileSync } from 'node:fs'

import { SAVED, stubSiteData } from './sites'
import { stubFeedApi, stubSiteApi } from './siteApi'
import { expect, test } from './test'

// Every page loads with no console errors (a CSP violation shows as one) and no failed requests
let problems: string[] = []

test.beforeEach(({ page }) => {
  problems = []
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(message.text())
  })
  page.on('pageerror', (error) => problems.push(String(error)))
  // A request cancelled on purpose (a superseded fetch, tiles as a map moves, anything left by a reload) isn't a failure
  page.on('requestfailed', (request) => {
    const error = request.failure()?.errorText
    if (error !== 'net::ERR_ABORTED') problems.push(`${request.url()}: ${error}`)
  })
})

test.afterEach(() => {
  expect(problems).toEqual([])
})

test('home page', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1, name: 'AgWeather' })).toBeVisible()
  await expect(page.getByText('Version dev · wisconsin')).toBeVisible()
})

test('theme toggle switches and is remembered', async ({ page }) => {
  await page.goto('/')
  const before = await page.evaluate(() => matchMedia('(prefers-color-scheme: dark)').matches)
  await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', before ? 'light' : 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', before ? 'light' : 'dark')
})

test('header has the sections, and settings choose the units', async ({ page }) => {
  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Main' })
  for (const section of ['Map', 'Sites', 'Models', 'Tools', 'Climate', 'Data'])
    await expect(nav.getByRole('link', { name: section, exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Settings' }).click()
  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog.getByRole('radio', { name: 'US (°F, inches)' })).toBeChecked()
  await dialog.getByText('Metric (°C, millimeters)').click()
  await expect(dialog.getByRole('radio', { name: 'Metric (°C, millimeters)' })).toBeChecked()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  await page.reload()
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByRole('radio', { name: 'Metric (°C, millimeters)' })).toBeChecked()
})

test('API docs', async ({ page }) => {
  await page.goto('/api/v2/docs')
  await expect(page.getByRole('heading', { level: 1, name: /^AgWeather API/ })).toBeVisible()
})

test('API use form sends a report', async ({ page }) => {
  await page.goto('/api-use')
  await page.getByLabel('Your name').fill('Pat Grower')
  await page.getByLabel('What do you use the API for?').fill('Degree days for our fields.')
  await page.getByLabel('Weather', { exact: true }).check()
  // A form sent within seconds of the page loading is taken for a program's (updates/forms.py)
  await page.waitForTimeout(3500)
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByRole('status')).toContainText('Thank you')
  await expect(page.getByLabel('Your name')).toHaveValue('')
})

test('API use form shows what to correct', async ({ page }) => {
  await page.goto('/api-use')
  await page.getByLabel('Your name').fill('Pat Grower')
  await page.waitForTimeout(3500)
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Tell us what you use the API for.')).toBeVisible()
  await expect(page.getByLabel('What do you use the API for?')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByLabel('Your name')).toHaveValue('Pat Grower')
})

test('site page', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/sites/44.12,-89.52?name=Hancock')
  await expect(page.getByRole('heading', { level: 1, name: 'Hancock' })).toBeVisible()
  await expect(page.getByText('Waushara County, WI · 44.12° N, 89.52° W')).toBeVisible()
  await expect(page.getByRole('list', { name: 'Risk today by model' })).toBeVisible()
  await page.getByRole('tab', { name: 'Weather' }).click()
  await expect(page.getByRole('heading', { name: 'Air temperature' })).toBeVisible()
  await expect(page.locator('[data-chart] canvas').first()).toBeAttached()
})

test('a model at a site', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/sites/44.12,-89.52/models/late-blight-dsv?name=Hancock')
  await expect(page.getByRole('heading', { level: 1, name: 'Late blight disease severity values' })).toBeVisible()
  await expect(page.getByText(/^Out of season /)).toBeVisible()
  await expect(page.locator('[data-chart] canvas').first()).toBeAttached()
  await expect(page.getByRole('table', { name: /the past 7 days and the forecast/ })).toBeVisible()
  await page.getByRole('link', { name: 'Hancock' }).click()
  await expect(page).toHaveURL(/\/sites\/44\.12,-89\.52\?name=Hancock$/)
})

test("a site's Degree days and Data tabs", async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/sites/44.12,-89.52?name=Hancock&tab=degree-days&dd=corn;sine_41_86&from=planting')
  await expect(page.getByRole('combobox', { name: 'Setting 1' })).toHaveValue('corn')
  await expect(page.locator('[data-chart] canvas').first()).toBeAttached()
  await expect(page.getByRole('rowheader', { name: 'Corn (field)' })).toBeVisible()
  await page.getByRole('tab', { name: 'Data' }).click()
  await expect(page.getByRole('link', { name: 'Download CSV' })).toHaveAttribute('href', /^\/api\/v2\/weather\/daily\?/)
  await page.getByRole('radio', { name: /A model run/ }).check()
  await expect(page.getByRole('textbox', { name: 'The request’s address, for a script' })).toHaveValue(
    /\/api\/v2\/models\/late-blight-dsv\/run\?format=csv&lat=44\.12&lng=-89\.52/,
  )
})

test('one model across your sites', async ({ page }) => {
  await stubSiteData(page)
  await stubFeedApi(page)
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
  await page.goto('/sites')
  await page.getByRole('combobox', { name: 'One model across your sites' }).selectOption('late-blight-dsv')
  await page.getByRole('button', { name: 'Show' }).click()
  await expect(page).toHaveURL(/\/sites\/models\/late-blight-dsv$/)
  const list = page.getByRole('list', { name: 'Your sites' })
  await expect(list.getByRole('listitem')).toHaveCount(3)
  await expect(list.getByRole('link', { name: 'Hancock' })).toHaveAttribute(
    'href',
    '/sites/44.1336,-89.5168/models/late-blight-dsv',
  )
})

test('the feed is not found for a model we don’t have', async ({ request }) => {
  expect((await request.get('/sites/models/no-such-model')).status()).toBe(404)
})

test('a model at a site is not found for a model we don’t have', async ({ request }) => {
  expect((await request.get('/sites/44.12,-89.52/models/no-such-model')).status()).toBe(404)
})

test('a site outside latitude and longitude is not found', async ({ request }) => {
  expect((await request.get('/sites/91,-89')).status()).toBe(404)
})

test('changelog page', async ({ page }) => {
  await page.goto('/changelog')
  await expect(page.getByRole('heading', { level: 1, name: 'Changes and announcements' })).toBeVisible()
})

test('the map explorer shows a layer and a clicked cell', async ({ page }) => {
  await page.goto('/map')
  await expect(page.getByRole('heading', { level: 1, name: 'Weather and pest maps' })).toBeVisible()
  await expect(page.getByTestId('data-legend')).toBeVisible()
  // The first visit's layer, by the month: degree days in the growing season, the daily low otherwise
  await expect(page.getByTestId('title-chip')).toContainText(/Growing degree days|Air temperature, daily minimum/)
  // A shared link opens its view, with its cell
  await page.goto('/map?layer=air_temperature_min&date=2026-11-20&at=43.07,-89.4')
  await expect(page.getByTestId('cell-panel')).toContainText('Dane County, WI')
  await expect(page.getByRole('heading', { name: "This cell's recent days" })).toBeVisible()
  // Stepping a day moves the date (the controls' stepper on a wide screen, the bar's under the map on a phone)
  await page.getByRole('button', { name: 'Forward 1 day' }).click()
  await expect(page.getByText('Nov 21, 2026', { exact: true })).toBeVisible()
  // The map's values by county, below the fold
  await page.getByRole('heading', { name: 'This map by county' }).scrollIntoViewIfNeeded()
  await expect(page.getByRole('table', { name: /by county in Wisconsin/ })).toContainText('Dane County')
})

test('a site added is kept after a reload, and exported', async ({ page }) => {
  await stubSiteData(page)
  await page.goto('/sites')
  await expect(page.getByRole('heading', { name: 'No sites yet' })).toBeVisible()
  await page.getByRole('button', { name: 'Add a site' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add a site' })
  await dialog.getByLabel('Name').fill('North field')
  await dialog.getByLabel('Latitude').fill('44.1336')
  await dialog.getByLabel('Longitude').fill('-89.5168')
  await dialog.getByRole('button', { name: 'Save site' }).click()
  await expect(dialog).toBeHidden()
  const card = page.getByRole('listitem', { name: 'North field' })
  await expect(card.getByText('Late blight')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('listitem', { name: 'North field' })).toBeVisible()
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'North field' })).toHaveAttribute('href', '/sites/44.1336,-89.5168')

  await page.goto('/sites')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export CSV' }).click()
  const file = await download
  expect(file.suggestedFilename()).toBe('agweather-sites.csv')
  const text = readFileSync(await file.path(), 'utf8')
  expect(text).toBe('﻿name,lat,lng,groups\r\nNorth field,44.1336,-89.5168,\r\n')
})

test('health check', async ({ request }) => {
  const response = await request.get('/up')
  expect(await response.json()).toMatchObject({ status: 'ok', database: 'ok' })
})

test('the model catalog filters by crop and opens a model page', async ({ page }) => {
  await page.goto('/models')
  await expect(page.getByRole('heading', { level: 1, name: 'Crop disease and insect models' })).toBeVisible()
  await page.getByLabel('Crop', { exact: true }).selectOption('corn')
  await expect(page.getByRole('heading', { level: 2, name: 'Apple' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Tar spot risk' }).first().click()
  await expect(page).toHaveURL(/\/models\/tar-spot$/)
  await expect(page.getByRole('heading', { level: 2, name: 'How to read it' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'See the map' })).toHaveAttribute('href', '/map?layer=tar-spot')
})

test('a retired or unknown model has no page', async ({ request }) => {
  expect((await request.get('/models/no-such-model')).status()).toBe(404)
})
