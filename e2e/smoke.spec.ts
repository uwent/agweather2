import { expect, test } from './test'

// Every page loads with no console errors (a CSP violation shows as one) and no failed requests
let problems: string[] = []

test.beforeEach(({ page }) => {
  problems = []
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(message.text())
  })
  page.on('pageerror', (error) => problems.push(String(error)))
  page.on('requestfailed', (request) => problems.push(`${request.url()}: ${request.failure()?.errorText}`))
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
  // Stepping a day moves the date
  await page.getByRole('button', { name: 'Forward 1 day' }).click()
  await expect(page.locator('#time-day')).toHaveValue('2026-11-21')
  // Tiles cancelled as the map moved on, or as the page was left, aren't failures
  problems = problems.filter((problem) => !problem.endsWith('net::ERR_ABORTED'))
})

test('health check', async ({ request }) => {
  const response = await request.get('/up')
  expect(await response.json()).toMatchObject({ status: 'ok', database: 'ok' })
})
