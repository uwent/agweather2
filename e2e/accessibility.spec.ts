// Ported from WISP 3 (adapted): e2e/accessibility.spec.ts
import AxeBuilder from '@axe-core/playwright'
import { type Page } from '@playwright/test'

import { SAVED, stubSiteData } from './sites'
import { stubSiteApi } from './siteApi'
import { expect, test } from './test'

// WCAG 2.1 A and AA checks (axe) on every page, in light (desktop) and dark (phone), and on desktop
// each page's reflow (320 px wide, 200% text). Every page is scanned before the test fails. Add new
// pages here.

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

const PAGES = ['/', '/sites', '/changelog', '/api-use', '/map']

async function scan(page: Page, path: string, { reflow = true }: { reflow?: boolean } = {}) {
  await page.goto(path)
  await expect(page.locator('main h1').first()).toBeVisible()
  // Open the collapsed sections (CollapsibleSection) so what's in them is checked too
  const closed = page.locator('[data-section-toggle][aria-expanded="false"]')
  while ((await closed.count()) > 0) await closed.first().click()
  // Nothing hovered where the last click left the pointer
  await page.mouse.move(0, 0)
  // Transitions finished: axe blends a fading element's text into its background; a spinner's
  // endless one aside
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .every((animation) => animation.playState !== 'running' || animation.effect?.getTiming().iterations === Infinity),
  )
  // Charts draw after ECharts loads
  for (const chart of await page.locator('[data-chart]').all()) await expect(chart.locator('canvas')).toBeAttached()
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  expect
    .soft(
      violations.map(
        (violation) =>
          `${violation.id} (${violation.nodes.length}): ${violation.help} at ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}${violation.nodes[0]?.failureSummary ? ` (${violation.nodes[0].failureSummary.replace(/\s+/g, ' ')})` : ''}`,
      ),
      `${path} has accessibility violations`,
    )
    .toEqual([])

  if (reflow && test.info().project.name === 'desktop') await reflows(page, path)
}

// WCAG 1.4.10: 320 CSS px wide with no sideways page scroll (grids and tables scroll inside
// themselves); WCAG 1.4.4: text at 200%. Checked on the page as scanned, its sections open.
async function reflows(page: Page, path: string) {
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  const size = page.viewportSize()!
  await page.setViewportSize({ width: 320, height: 640 })
  await page.waitForFunction(() => window.innerWidth === 320)
  expect.soft(await overflow(), `${path} scrolls sideways at 320 px`).toBeLessThanOrEqual(0)
  await page.setViewportSize(size)
  await page.waitForFunction((width) => window.innerWidth === width, size.width)
  const larger = await page.addStyleTag({ content: 'html { font-size: 200% !important }' })
  expect.soft(await overflow(), `${path} scrolls sideways with 200% text`).toBeLessThanOrEqual(0)
  await larger.evaluate((element) => (element as HTMLElement).remove())
}

test('public pages', async ({ page }) => {
  for (const path of PAGES) await scan(page, path)
})

test('public pages in the other theme', async ({ page }) => {
  // The desktop project is light and the phone dark: each also checks the other through the toggle
  await page.goto('/')
  await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
  for (const path of PAGES) await scan(page, path, { reflow: false })
})

test('your sites with saved sites, and the add-site dialog', async ({ page }) => {
  await stubSiteData(page)
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
  await scan(page, '/sites')
  await expect(page.getByText('Late blight').first()).toBeVisible()
  await scan(page, '/')
  await page.goto('/sites')
  await page.getByRole('button', { name: 'Add a site' }).click()
  await expect(page.getByRole('dialog', { name: 'Add a site' })).toBeVisible()
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  expect(violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([])
})

// Groups and preferences: /sites with a group's preferences and a card's groups open, and a saved site's page with
// its preferences open, in both themes
async function axeOnly(page: Page, what: string) {
  await page.mouse.move(0, 0)
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  expect
    .soft(
      violations.map((v) => `${v.id}: ${v.help} at ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`),
      `${what} has accessibility violations`,
    )
    .toEqual([])
}

test('groups and preferences panels', async ({ page }) => {
  await stubSiteData(page)
  await stubSiteApi(page)
  await page.goto('/')
  const saved = {
    ...SAVED,
    sites: [...SAVED.sites, { ...SAVED.sites[0], key: '44.12,-89.52', lat: 44.12, lng: -89.52, name: 'Plover' }],
    prefs: { all: { crops: ['potato'] }, groups: { g1: { hiddenModels: ['tar-spot'] } }, sites: {} },
  }
  saved.groups = [{ ...SAVED.groups[0], siteKeys: ['44.1336,-89.5168', '44.12,-89.52'] }]
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), saved)
  for (const theme of ['first', 'other']) {
    if (theme === 'other') {
      await page.goto('/')
      await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
    }
    await page.goto('/sites')
    await expect(page.locator('main h1').first()).toBeVisible()
    const closed = page.locator('[data-section-toggle][aria-expanded="false"]')
    while ((await closed.count()) > 0) await closed.first().click()
    await page.getByRole('button', { name: 'Preferences for Research stations' }).click()
    await page.getByRole('button', { name: 'Groups for Madison' }).click()
    await page.getByTestId('prefs-group').getByLabel('Change a model’s settings').selectOption('late-blight-dsv')
    await axeOnly(page, `/sites (${theme} theme)`)

    await page.goto('/sites/44.12,-89.52#preferences')
    await expect(page.getByRole('heading', { name: 'Preferences for this site' })).toBeVisible()
    await expect(page.getByText('This site follows its group: Research stations.')).toBeVisible()
    await axeOnly(page, `a site's preferences (${theme} theme)`)
    await page.getByRole('button', { name: /^Groups/ }).click()
    await axeOnly(page, `a site's groups (${theme} theme)`)
  }
})

// A site page, its API answers stubbed: the Overview, the Weather tab's charts, the Models tab, and a model at the site
const SITE_PAGES = [
  '/sites/44.12,-89.52',
  '/sites/44.12,-89.52?tab=weather',
  '/sites/44.12,-89.52?tab=models',
  '/sites/44.12,-89.52/models/late-blight-dsv',
]

test('site pages', async ({ page }) => {
  await stubSiteApi(page)
  for (const path of SITE_PAGES) await scan(page, path)
})

test('site pages in the other theme', async ({ page }) => {
  await stubSiteApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
  for (const path of SITE_PAGES) await scan(page, path, { reflow: false })
})

// The model catalog and two model pages: a disease with risk levels, and a fitted insect with its training area
const MODEL_PAGES = ['/models', '/models/tar-spot', '/models/colorado-potato-beetle']

test('model pages', async ({ page }) => {
  for (const path of MODEL_PAGES) await scan(page, path)
})

test('model pages in the other theme', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
  for (const path of MODEL_PAGES) await scan(page, path, { reflow: false })
})

test('the settings dialog', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible()
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  expect(violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([])
})
