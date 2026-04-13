import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test('Citizen flow: intake screening rejects unsupported images with an archive record', async ({ page, context }) => {
  resetDatabase()
  const testImage = ensureTestImage('test_e2e.jpg')

  await context.grantPermissions(['geolocation'])
  await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 })

  await loginAs(page, 'citizen@example.com', '/citizen')
  await expect(page.locator('text=Report New Issue')).toBeVisible()

  await page.click('text=Report New Issue')
  await page.waitForURL('**/citizen/report')

  // Step 1: Capture Evidence
  await page.locator('input[type="file"]').setInputFiles(testImage)
  await page.click('button:has-text("Continue to Location")')

  // Step 2: Pin Location
  await page.click('button:has-text("Broadcast Report")')

  // Step 3: Rejection from intake screening
  await expect(
    page.getByText('Image did not match any supported issue type.')
  ).toBeVisible({ timeout: 15000 })

  const issueCount = runSql(
    'SELECT COUNT(*)::text FROM issue;'
  )
  expect(issueCount).toBe('0')

  const rejectionCount = runSql(
    "SELECT COUNT(*)::text FROM reportintakesubmission WHERE status='REJECTED' AND reason_code='REJECTED';"
  )
  expect(rejectionCount).toBe('1')
})
