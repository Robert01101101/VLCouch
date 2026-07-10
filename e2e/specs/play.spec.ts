import { test, expect } from '@playwright/test'

test.describe('Play actions', () => {
  test('play movie from home row', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })

    const movieRow = page.locator('[data-testid^="browse-row-movies-"]').first()
    await expect(movieRow).toBeVisible({ timeout: 10000 })
    const movieCard = movieRow.locator('[data-testid^="poster-card-"]').first()
    await expect(movieCard).toBeVisible()

    page.on('dialog', (dialog) => dialog.accept())
    const playResponse = page.waitForResponse(
      (r) => r.url().includes('/api/play/movie/') && r.request().method() === 'POST'
    )
    await movieCard.click()
    await playResponse
  })
})
