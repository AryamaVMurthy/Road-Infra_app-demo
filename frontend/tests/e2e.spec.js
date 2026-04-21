import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test('Citizen flow: intake screening persists a backend decision and submission record', async ({ page, context }) => {
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

  const acceptedText = page.getByText('Accepted for review. A government admin will assign the category.')
  const rejectedText = page.getByText('The image was rejected by intake screening.')
  await Promise.any([
    acceptedText.waitFor({ state: 'visible', timeout: 15000 }),
    rejectedText.waitFor({ state: 'visible', timeout: 15000 }),
  ])

  const submissionCount = runSql(
    'SELECT COUNT(*)::text FROM reportintakesubmission;'
  )
  expect(submissionCount).toBe('1')

  const submissionStatus = runSql(
    'SELECT status FROM reportintakesubmission ORDER BY created_at DESC LIMIT 1;'
  )
  expect(['ACCEPTED_UNCATEGORIZED', 'REJECTED_SPAM']).toContain(submissionStatus)

  const issueCount = runSql(
    'SELECT COUNT(*)::text FROM issue;'
  )
  if (submissionStatus === 'ACCEPTED_UNCATEGORIZED') {
    expect(issueCount).toBe('1')
  } else {
    expect(issueCount).toBe('0')
  }
})
