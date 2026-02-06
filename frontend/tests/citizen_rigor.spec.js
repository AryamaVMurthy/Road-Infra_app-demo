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
      await page.click('button:has-text("Confirm & Proceed")')
      await page.locator('input[type="file"]').setInputFiles(testImage)
      await page.click('button:has-text("Next Step")')
      await page.locator('select').selectOption({ index: 1 })
      await page.click('button:has-text("Submit Report")')
      await Promise.race([
        page.waitForURL('**/citizen/my-reports', { timeout: 15000 }),
        page.waitForSelector('text=/Successfully reported/i', { timeout: 15000 }),
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
