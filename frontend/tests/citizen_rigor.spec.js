import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test.describe('Citizen Rigorous Flow', () => {
  test('submits duplicate reports that aggregate report_count', async ({ page, context }) => {
    resetDatabase()
    const testImage = ensureTestImage('test_rigor.jpg')

    await context.grantPermissions(['geolocation'])
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 })

    await loginAs(page, 'citizen@example.com', '/citizen')

    const submitReport = async () => {
      await page.goto('/citizen/report', { waitUntil: 'domcontentloaded' })
      // Step 1: Capture Evidence
      await page.locator('input[type="file"]').setInputFiles(testImage)
      // Wait for categories to load and select one
      await page.locator('button:has-text("Pothole")').first().click()
      await page.click('button:has-text("Continue to Location")')

      // Step 2: Pin Location
      await page.click('button:has-text("Broadcast Report")')

      // Step 3: Success
      await Promise.race([
        page.waitForURL('**/citizen/my-reports', { timeout: 15000 }),
        page.waitForSelector('text=/Successfully Logged/i', { timeout: 15000 }),
      ])
    }

    await submitReport()
    await submitReport()

    const count = runSql(
      "SELECT report_count::text FROM issue WHERE reporter_id=(SELECT id FROM \"user\" WHERE email='citizen@example.com' LIMIT 1) ORDER BY created_at DESC LIMIT 1;"
    )
    expect(count).toBe('2')
  })
})
