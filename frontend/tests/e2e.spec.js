import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test('Citizen flow: login and report issue successfully', async ({ page, context }) => {
  resetDatabase()
  const testImage = ensureTestImage('test_e2e.jpg')

  await context.grantPermissions(['geolocation'])
  await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 })

  await loginAs(page, 'citizen@example.com', '/citizen')
  await expect(page.locator('text=Report New Issue')).toBeVisible()

  await page.click('text=Report New Issue')
  await page.waitForURL('**/citizen/report')

  await page.click('button:has-text("Confirm & Proceed")')
  await page.locator('input[type="file"]').setInputFiles(testImage)
  await page.click('button:has-text("Next Step")')
  await page.locator('select').selectOption({ index: 1 })
  await page.click('button:has-text("Submit Report")')

  await Promise.race([
    page.waitForURL('**/citizen/my-reports', { timeout: 15000 }),
    page.waitForSelector('text=/Successfully reported/i', { timeout: 15000 }),
  ])

  const issueState = runSql(
    "SELECT status || ':' || report_count::text FROM issue ORDER BY created_at DESC LIMIT 1;"
  )
  expect(issueState).toBe('REPORTED:1')
})
