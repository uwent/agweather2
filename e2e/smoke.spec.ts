import { readFileSync } from 'node:fs'

import { SAVED, stubSiteData } from './sites'
import { stubDataApi } from './dataApi'
import { stubClimateApi } from './climateApi'
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
  // Every tab is on the screen, a phone's too (they wrap rather than scroll out of sight)
  await expect(page.getByRole('tab', { name: 'Data' })).toBeInViewport()
  await page.getByRole('tab', { name: 'Data' }).click()
  await expect(page.getByRole('link', { name: 'Download CSV' })).toHaveAttribute('href', /^\/api\/v2\/weather\/daily\?/)
  await page.getByRole('radio', { name: /A model run/ }).check()
  await expect(page.getByRole('textbox', { name: 'The request’s address, for a script' })).toHaveValue(
    /\/api\/v2\/models\/late-blight-dsv\/run\?format=csv&lat=44\.12&lng=-89\.52/,
  )
})

test('a date to count degree days from is kept with a saved site', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
  await page.goto('/sites/44.1336,-89.5168?tab=degree-days&from=planting')
  await page.getByRole('textbox', { name: 'Planting date' }).fill('2026-05-12')
  await expect(page.getByText('Saved as this site’s planting date.')).toBeVisible()
  const kept = await page.evaluate(() => JSON.parse(localStorage.getItem('agweather.sites') ?? '{}'))
  expect(kept.prefs.sites['44.1336,-89.5168'].planting).toBe('2026-05-12')
  // Opened again without the date in the link, the site's own date is the one counted from
  await page.goto('/sites/44.1336,-89.5168?tab=degree-days&from=planting')
  await expect(page.getByText(/Counting from this site’s planting date, May 12/)).toBeVisible()
  await page.getByRole('button', { name: 'Forget this date' }).click()
  await expect(page.getByText(/Counting from this site’s planting date/)).toBeHidden()
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
  // The title says what the map is; how far the data reaches is the date control's
  await expect(page.getByTestId('title-chip')).not.toContainText('Observed through')
  // The map's values by county, below the fold
  await page.getByRole('heading', { name: 'This map by county' }).scrollIntoViewIfNeeded()
  await expect(page.getByRole('table', { name: /by county in Wisconsin/ })).toContainText('Dane County')
})

test('the map explorer saves the map as a PNG', async ({ page }) => {
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
  await page.goto('/map?layer=air_temperature_min&date=2026-11-20')
  await expect(page.getByTestId('data-legend')).toBeVisible()
  await page.getByRole('button', { name: 'Save image' }).first().click()
  await expect(page.getByLabel('Name my saved sites on the map')).toBeChecked()
  const download = page.waitForEvent('download')
  await page.getByTestId('save-image').click()
  const file = await download
  expect(file.suggestedFilename()).toMatch(/^agweather-air_temperature_min-[\d-]+\.png$/)
  const bytes = readFileSync(await file.path())
  // A PNG's signature, then its header's width: twice the map's at least
  expect(bytes.subarray(1, 4).toString('latin1')).toBe('PNG')
  expect(bytes.readUInt32BE(16)).toBeGreaterThan(400)
  await expect(page.getByText('Saved. Look for the image in your downloads.')).toBeVisible()
})

test('a fitted model’s map outlines its training area and says when the cell is outside it', async ({ page }) => {
  // The recorded /models predates `trained`: the beetle's, as /models gives it now
  const models = JSON.parse(readFileSync(new URL('../frontend/test/fixtures/models.json', import.meta.url), 'utf8'))
  const beetle = models.data.find((m: { id: string }) => m.id === 'colorado-potato-beetle')
  beetle.trained = {
    description: 'scouting counts in commercial potato fields in central Wisconsin, mostly the Central Sands',
    years: [2014, 2025],
    states: [],
    counties: [
      '55001',
      '55137',
      '55097',
      '55077',
      '55135',
      '55111',
      '55049',
      '55057',
      '55141',
      '55021',
      '55073',
      '55103',
    ],
  }
  await page.route('**/api/v2/models', (route) => route.fulfill({ json: models }))
  await page.goto('/map?layer=colorado-potato-beetle&at=43.07,-89.4')
  await expect(page.getByTestId('training-area-note')).toContainText('The dashed line on the map outlines that area.')
  // The recorded cell is Madison's, in Dane County, outside the Central Sands
  await expect(page.getByTestId('outside-training')).toContainText('outside the area')
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

test('a group’s preferences hide a model from its sites, and reset', async ({ page }) => {
  await stubSiteData(page)
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), { ...SAVED, groups: [] })
  await page.goto('/sites')
  const madison = page.getByRole('listitem', { name: 'Madison' })
  const hancock = page.getByRole('listitem', { name: 'Hancock' })
  const rhinelander = page.getByRole('listitem', { name: 'Rhinelander' })
  await expect(madison.getByText('Late blight')).toBeVisible()
  await expect(hancock.getByText('Late blight')).toBeVisible()

  // A group with two of the sites
  await page.getByRole('button', { name: 'Groups', exact: true }).click()
  await page.getByLabel('New group').fill('North farm')
  await page.getByRole('button', { name: 'Add group' }).click()
  const members = page.getByRole('group', { name: 'Sites in North farm' })
  await members.getByRole('checkbox', { name: 'Madison' }).check()
  await members.getByRole('checkbox', { name: 'Hancock' }).check()

  // Late blight hidden for the group: gone from both its sites' cards, not from the third
  await page.getByRole('button', { name: 'Preferences for North farm' }).click()
  const panel = page.getByTestId('prefs-group')
  await panel.getByRole('checkbox', { name: 'Late blight disease severity values' }).uncheck()
  await expect(panel.getByText('Set for this group: Late blight disease severity values hidden.')).toBeVisible()
  await expect(madison.getByText('Late blight')).toBeHidden()
  await expect(hancock.getByText('Late blight')).toBeHidden()
  await expect(rhinelander.getByText('Late blight')).toBeVisible()

  // Kept after a reload; then reset
  await page.reload()
  await expect(madison.getByText('White mold')).toBeVisible()
  await expect(madison.getByText('Late blight')).toBeHidden()
  const group = page.getByTestId('group-North farm')
  if (!(await page.getByTestId('prefs-group').isVisible()))
    await group.getByRole('button', { name: 'Preferences for North farm' }).click()
  await page.getByTestId('prefs-group').getByRole('button', { name: 'Reset to my defaults' }).click()
  await expect(madison.getByText('Late blight')).toBeVisible()
  await expect(hancock.getByText('Late blight')).toBeVisible()

  // The group on the map: its sites named, the view shared with them
  await group.getByRole('link', { name: 'Show on the map' }).click()
  await expect(page.getByTestId('map-group')).toContainText('Showing the group North farm: 2 sites')
})

// The oak wilt tool (track 5 T1 d)
test('oak wilt: the restricted period at a location, its chart and DNR’s rules', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/tools/oak-wilt')
  await expect(page.getByRole('heading', { level: 1, name: /^Oak wilt/ })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Oak Harvesting Guidelines (PUB-FR-560, PDF)' })).toBeVisible()
  await page.goto('/tools/oak-wilt?at=43.07,-89.4')
  await expect(page.getByText(/The oak wilt vector model’s level/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'The season' })).toBeVisible()
  await expect(page.locator('[data-chart] canvas').first()).toBeAttached()
  await expect(page.getByRole('heading', { name: 'Managing oak wilt' })).toBeVisible()
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

test('the topics index opens a topic page, which links its model', async ({ page }) => {
  await page.goto('/models')
  await page.getByRole('link', { name: 'Pests and diseases' }).click()
  await expect(page).toHaveURL(/\/topics$/)
  await page.getByLabel('Crop', { exact: true }).selectOption('potato')
  await page
    .getByRole('link', { name: /^Late blight \(/ })
    .first()
    .click()
  await expect(page).toHaveURL(/\/topics\/late-blight$/)
  await expect(page.getByRole('heading', { level: 2, name: 'Identification' })).toBeVisible()
  await expect(page.getByRole('img', { name: 'Late blight spots on potato leaves' })).toHaveJSProperty('complete', true)
  await page.getByRole('link', { name: 'Late blight disease severity values' }).first().click()
  await expect(page).toHaveURL(/\/models\/late-blight-dsv$/)
})

test('an unknown topic has no page', async ({ request }) => {
  expect((await request.get('/topics/no-such-topic')).status()).toBe(404)
})

// --- /data (track 7 step 7.1) ---------------------------------------------------------------------------------------

test('the data page builds a download at saved sites and places, and lists the yearly files', async ({ page }) => {
  await stubDataApi(page)
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
  await page.goto('/data')
  await expect(page.getByRole('heading', { level: 1, name: 'Data and downloads' })).toBeVisible()
  await page.getByRole('button', { name: 'Choose all' }).click()
  await page.getByLabel('Add a place').fill('43.07, -89.40')
  await page.getByRole('button', { name: 'Add', exact: true }).click()
  await expect(page.getByText(/^\d+ locations chosen, of up to 50\./)).toBeVisible()
  const address = page.locator('#locations').getByRole('textbox', { name: 'The request’s address, for a script' })
  await expect(address).toHaveValue(/\/api\/v2\/weather\/daily\?format=csv&points=[^&]*43\.07%2C-89\.4/)
  await expect(page.locator('#locations').getByRole('link', { name: 'Download CSV' })).toBeVisible()
  // The test server's archive is empty, so there are no areas for a map file
  await expect(page.getByText('Map files aren’t available yet: the archive has no data.')).toBeVisible()
  await expect(page.getByRole('link', { name: /Air temperature at 2 m, daily max, 2025: \d+ MB NetCDF/ })).toBeVisible()
})

test('the methods page, linked from the footer and from a model’s inputs', async ({ page }) => {
  await page.goto('/models/tar-spot')
  await page.getByRole('link', { name: 'Minimum temperature' }).click()
  await expect(page).toHaveURL(/\/methods#variable-air_temperature_min$/)
  await expect(page.getByRole('heading', { level: 1, name: 'Methods' })).toBeVisible()
  await expect(page.locator('#variable-air_temperature_min')).toBeInViewport()
  await page.getByRole('contentinfo').getByRole('link', { name: 'Methods' }).click()
  await expect(page).toHaveURL(/\/methods$/)
})

test('the tools index opens the degree-day calculator, which answers for a place typed in', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/tools')
  await page.getByRole('link', { name: 'Degree-day calculator' }).click()
  await expect(page).toHaveURL(/\/tools\/degree-days$/)
  await page.getByLabel('Choose a place').fill('44.12, -89.52')
  await page.getByLabel('Choose a place').press('Enter')
  await expect(page.getByText('Waushara County, WI · 44.12° N, 89.52° W')).toBeVisible()
  await expect(page.locator('[data-chart] canvas').first()).toBeAttached()
  await expect(page.getByRole('link', { name: 'See on the map' })).toHaveAttribute(
    'href',
    '/map?layer=degree_days&span=season&dd=modified_50_86&at=44.12,-89.52',
  )
  await page.getByRole('link', { name: 'Open the site page' }).click()
  await expect(page).toHaveURL(/\/sites\/44\.12,-89\.52$/)
})

test('the day-of-year calendar converts a date and changes year', async ({ page }) => {
  await page.goto('/calendar?year=2028')
  await expect(page.getByRole('heading', { level: 1, name: 'Day-of-year calendar' })).toBeVisible()
  await expect(page.getByText(/2028 is a leap year/)).toBeVisible()
  await page.getByLabel('Date to day of year').fill('2028-03-01')
  await expect(page.getByText('March 1, 2028 is day 61 of 2028.')).toBeVisible()
  await page.getByRole('button', { name: 'Previous year' }).click()
  await expect(page.getByRole('heading', { name: 'The days of 2027' })).toBeVisible()
})

// --- The reference pages (track 7 step 7.4): about, accessibility, contact and the glossary

test('the about, accessibility and contact pages, from the footer', async ({ page }) => {
  await page.goto('/')
  for (const [link, title] of [
    ['About', 'About AgWeather'],
    ['Accessibility', 'Accessibility'],
    ['Contact', 'Contact us'],
  ]) {
    await page.getByRole('contentinfo').getByRole('link', { name: link, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  }
  await expect(page.getByRole('link', { name: 'agweather@cals.wisc.edu' }).first()).toHaveAttribute(
    'href',
    'mailto:agweather@cals.wisc.edu',
  )
})

test('the glossary filters its terms, and a term on another page links to its entry', async ({ page }) => {
  await page.goto('/glossary')
  await expect(page.getByRole('heading', { level: 1, name: 'Glossary' })).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search the glossary' }).fill('fruit trees')
  await expect(page.getByText('Chill hours', { exact: true })).toBeVisible()
  await expect(page.getByText('Biofix', { exact: true })).toBeHidden()

  await page.goto('/methods')
  await page.getByRole('button', { name: 'degree days' }).first().click()
  await page.getByRole('link', { name: 'See the glossary' }).click()
  await expect(page).toHaveURL(/\/glossary#growing_degree_days$/)
  await expect(page.locator('#growing_degree_days')).toBeInViewport()
})

// The site page's Climate tab (track 6.2): each section loads as it scrolls in
test("a site's Climate tab", async ({ page }) => {
  await stubSiteApi(page)
  await stubClimateApi(page)
  await page.goto('/sites/44.12,-89.52?name=Hancock&tab=climate&cperiod=last10')
  await expect(page.getByRole('tab', { name: 'Climate' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('radio', { name: /^10 years/ })).toBeChecked()
  await expect(page.getByText(/^Degree days from Jan 1 through Nov 24:/)).toBeVisible()
  for (const name of ['Temperature against normal', 'Frost and freeze', 'This month against normal', 'Normals']) {
    await page.getByRole('heading', { level: 2, name }).scrollIntoViewIfNeeded()
  }
  await expect(page.getByRole('table', { name: /^Days counted in / })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Normals by month' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Average high: normal through the year' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Freeze dates' })).toBeVisible()
  await expect(page.locator('[data-chart] canvas')).toHaveCount(5)
})
