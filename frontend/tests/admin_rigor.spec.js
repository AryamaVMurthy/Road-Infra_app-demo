import { test, expect } from '@playwright/test'
import { resetDatabase, runSql } from './helpers/db'
import { loginAs } from './helpers/e2e'

test.describe('Admin Rigorous Flow', () => {
  test('assigns a reported issue to worker from kanban', async ({ page }) => {
    resetDatabase()

    const orgId = runSql(
      "SELECT org_id FROM \"user\" WHERE email='admin@authority.gov.in' LIMIT 1;"
    ).trim()

    const createdIssueId = runSql(
      `INSERT INTO issue (id, category_id, status, location, reporter_id, org_id, report_count, priority, created_at, updated_at) VALUES (gen_random_uuid(), (SELECT id FROM category LIMIT 1), 'REPORTED', ST_GeomFromText('POINT(78 17)', 4326), (SELECT id FROM \"user\" WHERE email='citizen@example.com' LIMIT 1), '${orgId}', 1, 'P3', now(), now()) RETURNING id;`
    ).trim()
    expect(createdIssueId).toBeTruthy()

    const workerId = runSql(
      "SELECT id FROM \"user\" WHERE email='worker@authority.gov.in' LIMIT 1;"
    ).trim()

    await loginAs(page, 'admin@authority.gov.in', '/authority')
    await page.click('text=Kanban Triage')
    await page.waitForSelector('.ticket-card', { timeout: 15000 })
    await expect(page.locator('.ticket-card').first()).toBeVisible()

    const assignResponse = await page.request.post(
      `/api/v1/admin/assign?issue_id=${createdIssueId}&worker_id=${workerId}`
    )
    expect(assignResponse.ok()).toBe(true)

    const status = runSql(`SELECT status FROM issue WHERE id='${createdIssueId}';`)
    const workerEmail = runSql(
      `SELECT u.email FROM issue i JOIN \"user\" u ON i.worker_id=u.id WHERE i.id='${createdIssueId}';`
    )

    expect(status).toBe('ASSIGNED')
    expect(workerEmail).toBe('worker@authority.gov.in')
  })
})
