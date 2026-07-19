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
    await expect(page.getByRole('heading', { name: 'Breaking Bad' })).toBeVisible()
    await expect(page.getByTestId('open-show-folder')).toBeVisible()

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

  test('mark season watched updates all episode checkboxes', async ({ page }) => {
    const showLink = page.locator('[data-testid^="poster-card-"]').filter({ hasText: 'Breaking Bad' }).first()
    await expect(showLink).toBeVisible({ timeout: 10000 })
    await showLink.click()
    await expect(page.getByTestId('show-detail')).toBeVisible()

    const seasonHeading = page.getByRole('heading', { name: 'Season 1' })
    const markSeasonWatched = page.getByTestId('mark-season-1-watched')

    if (!(await markSeasonWatched.isVisible())) {
      await seasonHeading.click()
    }
    await expect(markSeasonWatched).toBeVisible({ timeout: 10000 })

    const episodeCheckboxes = page.locator('[data-testid^="watched-episode-"]')
    await expect(episodeCheckboxes).toHaveCount(2)

    await Promise.all([
      page.waitForResponse((r) => r.url().includes('/seasons/1/watch-status') && r.ok()),
      page.waitForResponse((r) => r.url().includes('/shows/') && r.request().method() === 'GET'),
      markSeasonWatched.click(),
    ])

    if (!(await episodeCheckboxes.first().isVisible())) {
      await seasonHeading.click()
    }
    await expect(episodeCheckboxes.first()).toBeVisible({ timeout: 5000 })

    await expect(episodeCheckboxes.nth(0)).toBeChecked()
    await expect(episodeCheckboxes.nth(1)).toBeChecked()
  })
})
