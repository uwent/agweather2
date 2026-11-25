import { stubSiteApi } from './siteApi'
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

test('a site outside latitude and longitude is not found', async ({ request }) => {
  expect((await request.get('/sites/91,-89')).status()).toBe(404)
})

test('changelog page', async ({ page }) => {
  await page.goto('/changelog')
  await expect(page.getByRole('heading', { level: 1, name: 'Changes and announcements' })).toBeVisible()
})

test('health check', async ({ request }) => {
  const response = await request.get('/up')
  expect(await response.json()).toMatchObject({ status: 'ok', database: 'ok' })
})
