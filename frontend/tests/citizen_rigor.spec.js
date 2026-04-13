import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test.describe('Citizen Rigorous Flow', () => {
  test('submits repeated unsupported reports that remain archived and never create issues', async ({ page, context }) => {
    resetDatabase()
    const testImage = ensureTestImage('test_rigor.jpg')

    await context.grantPermissions(['geolocation'])
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 })

    await loginAs(page, 'citizen@example.com', '/citizen')

    const submitReport = async () => {
      await page.goto('/citizen/report', { waitUntil: 'domcontentloaded' })
      // Step 1: Capture Evidence
      await page.locator('input[type="file"]').setInputFiles(testImage)
      await page.click('button:has-text("Continue to Location")')

      // Step 2: Submit and expect rejection from intake screening
      await page.click('button:has-text("Broadcast Report")')
      await expect(
        page.getByText('Image did not match any supported issue type.')
      ).toBeVisible({ timeout: 15000 })
    }

    await submitReport()
    await submitReport()

    const issueCount = runSql(
      'SELECT COUNT(*)::text FROM issue;'
    )
    expect(issueCount).toBe('0')

    const rejectionCount = runSql(
      "SELECT COUNT(*)::text FROM reportintakesubmission WHERE status='REJECTED' AND reporter_id=(SELECT id FROM \"user\" WHERE email='citizen@example.com' LIMIT 1);"
    )
    expect(rejectionCount).toBe('2')
  })
})
