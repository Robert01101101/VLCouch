import { test, expect } from '@playwright/test'

test.describe('Home page', () => {
  test('loads browse rows from API', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    await expect(page.getByTestId('rescan-library')).toBeVisible()
    const rows = page.locator('[data-testid^="browse-row-"]')
    await expect(rows.first()).toBeVisible({ timeout: 10000 })
  })

  test('rescan button shows scanning state', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    const rescan = page.getByTestId('rescan-library')
    await rescan.click()
    await expect(rescan).toHaveText('Scanning...')
    await expect(rescan).toHaveText('Rescan Library', { timeout: 10000 })
  })

  test('search finds library items', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    await page.getByTestId('library-search').fill('Breaking')
    await expect(page.getByTestId('search-results')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('search-result-show-1')).toBeVisible()
  })
})
