import { test, expect } from '@playwright/test'

test.describe('Settings page', () => {
  test('loads settings and shows controls', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    await expect(page.getByTestId('settings-page')).toBeVisible()
    await expect(page.getByTestId('settings-media-folders')).toBeVisible()
    await expect(page.getByTestId('rescan-library')).toBeVisible()
    await expect(page.getByTestId('settings-wikipedia-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-scan-on-startup-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-browse-row-random-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-auto-thumbnails-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-vlc-options')).toBeVisible()
    await expect(page.getByTestId('settings-vlc-subtitles-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-vlc-resume-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-vlc-tv-playlist-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-vlc-playlist-advance-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-simple-vlc-toggle')).toBeVisible()
    await expect(page.getByTestId('settings-version')).toHaveText(/0\.1\.0/)
    await expect(page.getByTestId('settings-github-link')).toBeVisible()
  })

  test('rescan button shows scanning state', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByTestId('page-loading')).toBeHidden({ timeout: 15000 })
    const rescan = page.getByTestId('rescan-library')
    await rescan.click()
    await expect(rescan).toHaveText('Scanning...')
    await expect(rescan).toHaveText('Rescan Library', { timeout: 10000 })
  })
})
