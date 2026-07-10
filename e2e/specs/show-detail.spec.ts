import { test, expect } from '@playwright/test'

test.describe('Show detail', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
  })

  test('navigate to show and toggle watched', async ({ page }) => {
    const showLink = page.locator('[data-testid^="poster-card-"]').filter({ hasText: 'Breaking Bad' }).first()
    await expect(showLink).toBeVisible({ timeout: 10000 })
    await showLink.click()
    await expect(page.getByTestId('show-detail')).toBeVisible()
    await expect(page.getByTestId('nav-home')).toBeVisible()
    await expect(page.getByTestId('rescan-library')).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Breaking Bad' })).toBeVisible()

    const watched = page.locator('[data-testid^="watched-episode-"]').first()
    await expect(watched).toBeAttached()

    const markUnwatched = page.getByLabel('Mark as unwatched').first()
    const markWatched = page.getByLabel('Mark as watched').first()

    if (await watched.isChecked()) {
      await Promise.all([
        page.waitForResponse((r) => r.url().includes('/watch-status') && r.ok()),
        page.waitForResponse((r) => r.url().includes('/shows/') && r.request().method() === 'GET'),
        markUnwatched.click(),
      ])
      await expect(watched).not.toBeChecked()
    }

    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/watch-status') && r.ok()),
      page.waitForResponse((r) => r.url().includes('/shows/') && r.request().method() === 'GET'),
      markWatched.click(),
    ])
    await expect(watched).toBeChecked()
  })
})
