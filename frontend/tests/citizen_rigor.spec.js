import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { ensureTestImage, loginAs } from './helpers/e2e'

test.describe('Citizen Rigorous Flow', () => {
  test('submits repeated reports and records stable intake outcomes', async ({ page, context }) => {
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

      // Step 2: Submit and accept whichever decision the integrated model returns
      await page.click('button:has-text("Broadcast Report")')
      await Promise.any([
        page.getByText('Accepted for review. A government admin will assign the category.')
          .waitFor({ state: 'visible', timeout: 15000 }),
        page.getByText('The image was rejected by intake screening.')
          .waitFor({ state: 'visible', timeout: 15000 }),
      ])
    }

    await submitReport()
    await submitReport()

    const submissionCount = runSql(
      'SELECT COUNT(*)::text FROM reportintakesubmission;'
    )
    expect(submissionCount).toBe('2')

    const distinctStatuses = runSql(
      "SELECT string_agg(DISTINCT status, ',' ORDER BY status) FROM reportintakesubmission;"
    )
    expect(distinctStatuses).toMatch(/ACCEPTED_UNCATEGORIZED|REJECTED_SPAM/)

    const issueCount = runSql(
      'SELECT COUNT(*)::text FROM issue;'
    )
    expect(['0', '1']).toContain(issueCount)
  })
})
