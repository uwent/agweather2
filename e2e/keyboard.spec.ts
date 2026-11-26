import { expect, test } from './test'

// Keyboard use of the map explorer (WCAG 2.1.1, 2.4.3), modelled on WISP 3's keyboard spec: the controls in a
// sensible tab order, the day's stepper by Enter and Space, the phone's controls sheet opened and closed with focus
// returned, and a place found by search taking focus to the cell's answer, which a screen reader can't get from
// the map itself

const MAP = '/map?layer=air_temperature_min&date=2026-11-20'

test('the controls run in order: find a map, kind of map, daily or hourly, the measure, the time', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop', 'a phone holds the controls in a sheet (the next test)')
  await page.goto(MAP)
  const find = page.getByRole('searchbox', { name: 'Find a map' })
  await find.focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('radio', { name: 'Weather' })).toBeFocused()
  // A radio group is one tab stop: arrows move inside it
  await page.keyboard.press('Tab')
  await expect(page.getByRole('radio', { name: 'Daily' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('combobox', { name: 'Weather' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('radio', { name: 'Day', exact: true })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Date', { exact: true })).toBeFocused()
})

test('the stepper moves the day by Enter and Space, and stops at the archive’s ends', async ({ page }) => {
  await page.goto(MAP)
  const back = page.getByRole('button', { name: 'Back 7 days' })
  await back.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Nov 13, 2026', { exact: true })).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Back 1 day' })).toBeFocused()
  await page.keyboard.press('Tab')
  await page.keyboard.press('Space')
  await expect(page.getByText('Nov 14, 2026', { exact: true })).toBeVisible()
})

test('on a phone, Layer and date opens the controls as a sheet, and closing it returns focus', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'wide screens show the controls beside the map')
  await page.goto(MAP)
  const open = page.getByRole('button', { name: /Layer and date/ })
  await open.focus()
  await page.keyboard.press('Enter')
  const sheet = page.getByRole('dialog', { name: 'Layer and date' })
  await expect(sheet).toBeVisible()
  // Focus moves into the sheet, and Tab stays in it
  await expect(sheet.locator(':focus')).toHaveCount(1)
  await sheet.getByRole('searchbox', { name: 'Find a map' }).focus()
  await page.keyboard.press('Tab')
  await expect(sheet.getByRole('radio', { name: 'Weather' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(sheet).toBeHidden()
  await expect(open).toBeFocused()
  // And its own button closes it too
  await page.keyboard.press('Enter')
  await sheet.getByRole('button', { name: 'Show the map' }).press('Enter')
  await expect(sheet).toBeHidden()
  await expect(open).toBeFocused()
})

test('a place found by search takes focus to the cell’s answer and its links', async ({ page }) => {
  await page.goto(MAP)
  const search = page.getByRole('searchbox', { name: 'Find a place on the map' })
  await search.fill('Hancock WI')
  await search.press('Enter')
  const panel = page.getByTestId('cell-panel')
  await expect(panel).toBeFocused()
  await expect(panel).toContainText('Hancock')
  await page.keyboard.press('Tab')
  await expect(panel.getByRole('button', { name: 'Clear the cell you chose' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(panel.getByRole('link', { name: "See this cell's recent days and forecast" })).toBeFocused()
  await page.keyboard.press('Tab')
  const site = panel.getByRole('link', { name: 'Open this site' })
  await expect(site).toBeFocused()
  await expect(site).toHaveAttribute('href', /\/sites\/44\.1336,-89\.5168\?name=Hancock$/)
})

test('the date slider moves the day by its keys, and says where the forecast begins', async ({ page }, testInfo) => {
  await page.goto(MAP)
  if (testInfo.project.name === 'phone') await page.getByRole('button', { name: /Layer and date/ }).click()
  const slider = page.getByRole('slider', { name: 'Day on the timeline' })
  await expect(slider).toHaveAttribute('aria-valuetext', 'Nov 20, 2026')
  await slider.focus()
  await page.keyboard.press('ArrowRight')
  await expect(slider).toHaveAttribute('aria-valuetext', 'Nov 21, 2026')
  await page.keyboard.press('PageUp')
  await expect(slider).toHaveAttribute('aria-valuetext', 'Nov 28, 2026, forecast')
  // What the layer reaches is the date control's to say, not the map's title
  await expect(page.getByTestId('date-reach')).toContainText('Days through Nov 24, 2026 are observed')
  await expect(page.getByTestId('forecast-boundary')).toContainText('Observed through Nov 24')
  if (testInfo.project.name === 'phone') await page.getByRole('button', { name: 'Show the map' }).click()
  await expect(page.getByTestId('title-chip')).not.toContainText('Observed')
})
