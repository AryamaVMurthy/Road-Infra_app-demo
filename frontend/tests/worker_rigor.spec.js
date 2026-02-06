import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { loginAs } from './helpers/e2e'

test.describe('Worker Rigorous Flow', () => {
  test('accepts an assigned task with ETA', async ({ page }) => {
    resetDatabase()

    runSql(
      "INSERT INTO issue (id, category_id, status, location, reporter_id, worker_id, report_count, priority, created_at, updated_at) VALUES (gen_random_uuid(), (SELECT id FROM category LIMIT 1), 'ASSIGNED', ST_GeomFromText('POINT(78.35 17.44)', 4326), (SELECT id FROM \"user\" WHERE email='citizen@example.com' LIMIT 1), (SELECT id FROM \"user\" WHERE email='worker@authority.gov.in' LIMIT 1), 1, 'P3', now(), now()) RETURNING id;"
    )

    await loginAs(page, 'worker@authority.gov.in', '/worker')
    await expect(page.locator('text=Assigned Tasks')).toBeVisible()

    const acceptButton = page.locator('button:has-text("Accept Task")').first()
    await expect(acceptButton).toBeVisible()
    await acceptButton.click()
    await page.locator('button:has-text("Tomorrow")').click()
    await page.locator('button:has-text("Confirm & Accept")').click()

    const acceptedCount = runSql(
      "SELECT COUNT(*) FROM issue WHERE worker_id=(SELECT id FROM \"user\" WHERE email='worker@authority.gov.in' LIMIT 1) AND status='ACCEPTED';"
    )
    expect(Number(acceptedCount)).toBeGreaterThan(0)
  })
})
