import type { Page } from '@playwright/test'

import { SAVED } from './sites'
import { stubCropGddApi, stubFreezeApi, stubPotatoApi, stubSiteApi } from './siteApi'
import { expect, test } from './test'

// Keyboard use of the tools and the day-of-year calendar (WCAG 2.1.1, 2.4.3, 2.4.7), as keyboard.spec.ts does for
// the map explorer: every control reached by Tab from the main content to the footer, each with a visible focus,
// the page's controls in reading order, and the place picker (search and saved sites) and each tool's own controls
// worked by keys alone

/** The focused element's name as a reader hears it (near enough), and whether its focus shows */
async function focused(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null
    if (!el || el === document.body) return { name: '', shows: false, footer: false }
    const field = el as HTMLInputElement
    const label = field.labels?.[0]
    const name = (el.getAttribute('aria-label') ?? label?.innerText ?? el.innerText ?? '').trim().replace(/\s+/g, ' ')
    const ring = (node: Element) => {
      const s = getComputedStyle(node)
      const outline =
        s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 && s.outlineColor !== 'rgba(0, 0, 0, 0)'
      return outline || s.boxShadow !== 'none'
    }
    // A visually hidden radio (SegmentedChoice) shows its focus on its label
    const hidden = el.getBoundingClientRect().width <= 1
    // A date field's last stop is its calendar button, which Chromium rings itself (the field's own style doesn't
    // show it)
    const picker = field.type === 'date' && !el.matches(':focus-visible')
    const shows = picker || (hidden ? !!label && ring(label) : ring(el))
    return { name, shows, footer: !!el.closest('footer') }
  })
}

/** Tab from the main content to the footer: every stop shows its focus, and `expected` come in this order */
async function tabsInOrder(page: Page, expected: (string | RegExp)[]) {
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused()
  await page.keyboard.press('Enter')
  const names: string[] = []
  for (let n = 0; n < 80; n++) {
    await page.keyboard.press('Tab')
    const stop = await focused(page)
    if (stop.footer) break
    expect(stop.shows, `focus shows on "${stop.name}" (stop ${n + 1})`).toBe(true)
    names.push(stop.name)
  }
  let at = 0
  for (const want of expected) {
    const found = names.findIndex((name, i) => i >= at && (typeof want === 'string' ? name === want : want.test(name)))
    expect(
      found,
      `"${want}" after "${names[at - 1] ?? 'the start'}" in ${JSON.stringify(names)}`,
    ).toBeGreaterThanOrEqual(at)
    at = found + 1
  }
}

async function withSites(page: Page) {
  await page.goto('/')
  await page.evaluate((doc) => localStorage.setItem('agweather.sites', JSON.stringify(doc)), SAVED)
}

const place = (page: Page) => page.getByRole('region', { name: 'Place' })

// Tab order is the same on a phone; the desktop run checks it
test.skip(({ isMobile }) => isMobile)

test('the place picker by keys: a search, Change place, and a saved site', async ({ page }) => {
  await stubSiteApi(page)
  await withSites(page)
  await page.goto('/tools/degree-days')
  await tabsInOrder(page, [
    'About degree days and how we calculate them',
    'Choose a place',
    'Go',
    'Madison',
    'Hancock',
    'Rhinelander',
  ])

  // Coordinates typed and Enter: the place is shown, and focus moves to its name rather than being lost
  const search = page.getByRole('searchbox', { name: 'Choose a place' })
  await search.focus()
  await page.keyboard.type('44.5, -90.1')
  await page.keyboard.press('Enter')
  await expect(place(page)).toContainText('44.5')
  await expect(place(page).locator(':focus')).toHaveCount(1)
  await expect(search).toBeHidden()

  // Change place opens the search with focus in it; a name found by Enter takes focus back to the place
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Save this site' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Open the site page' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Change place' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(search).toBeFocused()
  await page.keyboard.type('Hancock WI')
  await page.keyboard.press('Enter')
  await expect(place(page).locator(':focus')).toContainText('Hancock')

  // A saved site by Tab and Space
  const rhinelander = page.getByRole('button', { name: 'Rhinelander' })
  for (let n = 0; n < 6 && !(await rhinelander.evaluate((el) => el === document.activeElement)); n++)
    await page.keyboard.press('Tab')
  await expect(rhinelander).toBeFocused()
  await page.keyboard.press('Space')
  await expect(rhinelander).toHaveAttribute('aria-pressed', 'true')
  await expect(place(page).locator('p').first()).toContainText('Rhinelander')
})

test('the degree-day calculator: settings, season and count-from in order, by keys', async ({ page }) => {
  await stubSiteApi(page)
  await withSites(page)
  await page.goto('/tools/degree-days?at=43.07,-89.4')
  await tabsInOrder(page, [
    'Share',
    'Change place',
    'Madison',
    'Setting 1',
    'Add a setting to compare',
    /^Season/,
    'January 1',
    /^Through/,
    'See on the map',
  ])
  // Count from is one tab stop; the arrows choose within it
  const jan1 = page.getByRole('radio', { name: 'January 1' })
  await jan1.focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('radio', { name: 'Planting date' })).toBeChecked()
  await expect(page.getByLabel('Planting date', { exact: true }).and(page.locator('input[type=date]'))).toBeVisible()
})

test('freeze dates and odds: temperatures, year and period by keys', async ({ page }) => {
  await stubFreezeApi(page)
  await withSites(page)
  await page.goto('/tools/freeze?at=43.07,-89.4')
  await tabsInOrder(page, ['Share', 'Change place', 'Madison', /^Frost, hard freeze/, /^Year/, 'Summary and data'])
  await page.getByRole('radio', { name: /^Frost, hard freeze/ }).focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('radio', { name: 'A crop’s killing freeze' })).toBeChecked()
  await expect(page.getByRole('combobox', { name: 'Crop' })).toBeVisible()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('radio', { name: 'Your own' })).toBeChecked()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('textbox', { name: 'Temperature' })).toBeFocused()
})

test('oak wilt: the place, the dates and the season by keys', async ({ page }) => {
  await stubSiteApi(page)
  await withSites(page)
  await page.goto('/tools/oak-wilt?at=43.07,-89.4')
  await tabsInOrder(page, [
    'Share',
    'Change place',
    'Madison',
    'How the model sets its levels',
    'Zoom in',
    'Summary and data',
  ])
})

test('crop GDD outlook: crop, maturity, planting, freeze and past years by keys', async ({ page }) => {
  await stubCropGddApi(page)
  await withSites(page)
  await page.goto('/tools/crop-gdd?at=43.07,-89.4&hybrid=2700&planting=2026-05-08&years=2012')
  await tabsInOrder(page, [
    'Share',
    'Change place',
    'Madison',
    /^Crop/,
    /^Hybrid maturity/,
    'Planting date',
    'Fall freeze',
    'Remove 2012',
    'Summary and data',
  ])
  // A past year removed by Enter
  await page.getByRole('button', { name: 'Remove 2012' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Remove 2012' })).toBeHidden()
})

test('potato volunteer: winter and the map’s measure by keys', async ({ page }) => {
  await stubPotatoApi(page)
  await withSites(page)
  await page.goto('/tools/potato-volunteer?at=44.12,-89.53&name=Hancock&winter=2025-26')
  await tabsInOrder(page, ['Share', 'Save this site', 'Change place', 'Hancock', 'Zoom in', 'Summary and data'])
})

test('the tools index and the day-of-year calendar by keys', async ({ page }) => {
  await page.goto('/tools')
  await tabsInOrder(page, [
    'Degree-day calculator',
    'Freeze dates and odds',
    'Crop GDD outlook',
    'Oak wilt',
    'Potato volunteer survival',
    'Day-of-year calendar',
  ])

  await page.goto('/calendar?year=2028')
  await tabsInOrder(page, [
    'Date to day of year',
    /^Day of year to date/,
    'Previous year',
    /^Year/,
    'Next year',
    /^Back to/,
  ])
  // A day typed into the number field, and the year changed by its buttons
  const day = page.getByRole('spinbutton', { name: /^Day of year to date/ })
  await day.focus()
  await page.keyboard.type('61')
  await expect(page.getByText(/^Day 61 of 2028 is/)).toBeVisible()
  await page.getByRole('button', { name: 'Previous year' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'The days of 2027' })).toBeVisible()
  await page.keyboard.press('Space')
  await expect(page.getByRole('heading', { name: 'The days of 2026' })).toBeVisible()
})
