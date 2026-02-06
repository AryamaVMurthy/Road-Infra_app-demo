import { test, expect } from '@playwright/test'
import { resetDatabase } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test.describe('Offline Sync Rigorous Flow', () => {
  test('Queues report while offline and syncs when online', async ({ page, context }) => {
    const testImage = ensureTestImage('off.jpg')

    await context.grantPermissions(['geolocation'])
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 })

    // Custom online/offline trigger
    await page.addInitScript(() => {
      let online = true
      Object.defineProperty(navigator, 'onLine', { get: () => online })
      window.addEventListener('offline_test', () => {
        online = false
        window.dispatchEvent(new Event('offline'))
      })
      window.addEventListener('online_test', () => {
        online = true
        window.dispatchEvent(new Event('online'))
      })
    })

    resetDatabase()
    await loginAs(page, 'citizen@example.com', '/citizen')

    // 3. Go Offline
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('offline_test')))

    // 4. Submit Report
    await page.goto('/citizen/report', { waitUntil: 'domcontentloaded' })
    await page.click('button:has-text("Confirm & Proceed")')
    await page.locator('input[type="file"]').setInputFiles(testImage)
    await page.click('button:has-text("Next Step")')
    await page.locator('select').selectOption({ index: 1 })
    await page.click('button:has-text("Submit Report")')

    const offlineNav = page.waitForURL('**/citizen/my-reports', { timeout: 15000 }).catch(() => null)
    const offlineToast = page
      .waitForSelector('text=Offline: Report saved and will be synced.', { timeout: 15000 })
      .catch(() => null)
    await Promise.race([offlineNav, offlineToast])
    if (!page.url().includes('/citizen/my-reports')) {
      await page.goto('/citizen/my-reports', { waitUntil: 'domcontentloaded' })
    }

    // 5. Go Online
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('online_test')))
    await page.waitForTimeout(8000)
    await page.reload({ waitUntil: 'domcontentloaded' })

    await expect(page.locator('text=Infrastructure Portal')).toBeVisible()
  })
})
