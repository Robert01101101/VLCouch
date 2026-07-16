import { test, expect } from '@playwright/test'

test.describe('Home page', () => {
  test('loads browse rows from API', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    await expect(page.getByTestId('nav-settings')).toBeVisible()
    const rows = page.locator('[data-testid^="browse-row-"]')
    await expect(rows.first()).toBeVisible({ timeout: 10000 })
  })

  test('rescan button shows scanning state', async ({ page }) => {
    await page.goto('/settings')
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

  test('hero play triggers episode playback', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })

    const showLink = page.locator('[data-testid^="poster-card-"]').filter({ hasText: 'Breaking Bad' }).first()
    await expect(showLink).toBeVisible({ timeout: 10000 })
    await showLink.click()
    await expect(page.getByTestId('show-detail')).toBeVisible()

    const seasonHeading = page.getByRole('heading', { name: 'Season 1' })
    const markSeasonUnwatched = page.getByTestId('mark-season-1-unwatched')
    if (!(await markSeasonUnwatched.isVisible())) {
      await seasonHeading.click()
    }
    if (await markSeasonUnwatched.isVisible()) {
      await Promise.all([
        page.waitForResponse((r) => r.url().includes('/seasons/1/watch-status') && r.ok()),
        page.waitForResponse((r) => r.url().includes('/shows/') && r.request().method() === 'GET'),
        markSeasonUnwatched.click(),
      ])
      if (!(await page.locator('[data-testid^="watched-episode-"]').first().isVisible())) {
        await seasonHeading.click()
      }
    }

    const firstCheckbox = page.locator('[data-testid^="watched-episode-"]').first()
    if (!(await firstCheckbox.isChecked())) {
      await Promise.all([
        page.waitForResponse((r) => r.url().includes('/watch-status') && r.ok()),
        page.waitForResponse((r) => r.url().includes('/shows/') && r.request().method() === 'GET'),
        page.getByLabel('Mark as watched').first().click(),
      ])
    }

    await page.getByTestId('nav-home').click()
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    await expect(page.getByTestId('hero-banner')).toBeVisible({ timeout: 10000 })

    await expect(page.getByTestId('hero-play')).toBeVisible()
    page.on('dialog', (dialog) => dialog.accept())
    const playResponse = page.waitForResponse(
      (r) => r.url().includes('/api/play/episode/') && r.request().method() === 'POST' && r.ok()
    )
    await page.getByTestId('hero-play').click()
    await playResponse
  })
})
