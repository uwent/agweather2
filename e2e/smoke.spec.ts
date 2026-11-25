import { expect, test } from '@playwright/test'

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

test('health check', async ({ request }) => {
  const response = await request.get('/up')
  expect(await response.json()).toMatchObject({ status: 'ok', database: 'ok' })
})
