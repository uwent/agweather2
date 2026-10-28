import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

// WCAG 2.1 A and AA checks (axe) on every page, in light (desktop) and dark (phone). Add new pages here.
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

async function scan(page: Page, path: string) {
  await page.goto(path)
  await expect(page.locator('main h1').first()).toBeVisible()
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  expect
    .soft(
      violations.map((violation) => `${violation.id} (${violation.nodes.length}): ${violation.help}`),
      `${path} has accessibility violations`,
    )
    .toEqual([])
}

test('public pages', async ({ page }) => {
  for (const path of ['/']) await scan(page, path)
})
