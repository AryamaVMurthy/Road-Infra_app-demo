import fs from 'node:fs';
import { test, expect } from '@playwright/test';
import { resetDatabase, runSql } from './helpers/db';
import { ensureTestImage, loginAs } from './helpers/e2e';

const ADMIN_EMAIL = 'admin@authority.gov.in';
const WORKER_EMAIL = 'worker@authority.gov.in';

let WORKER_ID;
let CATEGORY_ID;

test.describe('Golden Thread: Full Issue Lifecycle', () => {
  test.setTimeout(180000);

  test.beforeAll(() => {
    resetDatabase();
    WORKER_ID = runSql(
      `SELECT id FROM "user" WHERE email='${WORKER_EMAIL}' LIMIT 1;`
    ).trim();
    CATEGORY_ID = runSql(
      `SELECT id FROM category WHERE name='Pothole' LIMIT 1;`
    ).trim();
    expect(WORKER_ID).toBeTruthy();
    expect(CATEGORY_ID).toBeTruthy();
  });

  test('manual issue → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED', async ({ page, context }) => {
    page.on('console', msg => {
      const text = msg.text();
      if (!text.includes('ERR_INSUFFICIENT_RESOURCES') && !text.includes('Failed to load resource')) {
        console.log('BROWSER:', text);
      }
    });

    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 });

    const testImage = ensureTestImage();

    // PHASE 1: Sysadmin creates a routed issue explicitly so the workflow test is
    // deterministic even with VLM intake screening enabled.
    await loginAs(page, 'sysadmin@marg.gov.in', '/admin');
    const createResponse = await page.request.post('/api/v1/admin/manual-issues', {
      data: {
        category_id: CATEGORY_ID,
        lat: 17.4447,
        lng: 78.3483,
        address: 'Golden Thread Road',
      },
    });
    expect(createResponse.ok()).toBe(true);
    const createBody = await createResponse.json();
    const issueId = createBody.issue_id;
    expect(issueId).toBeTruthy();
    console.log(`PHASE 1 DONE: Issue ${issueId} created as REPORTED`);

    // PHASE 2: Admin assigns
    await loginAs(page, ADMIN_EMAIL, '/authority');
    await page.locator('text=Kanban Triage').click();
    await page.waitForTimeout(2000);

    // Fallback to API for speed in this long test
    const assignResp = await page.request.post(`/api/v1/admin/assign?issue_id=${issueId}&worker_id=${WORKER_ID}`);
    expect(assignResp.ok()).toBe(true);
    console.log('PHASE 2 DONE: Issue is ASSIGNED');

    // PHASE 3: Worker
    await loginAs(page, WORKER_EMAIL, '/worker');
    // Accept
    const etaDate = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const acceptResp = await page.request.post(
      `/api/v1/worker/tasks/${issueId}/accept?eta_date=${encodeURIComponent(etaDate)}`
    );
    expect(acceptResp.ok()).toBe(true);
    // Start
    const startResp = await page.request.post(`/api/v1/worker/tasks/${issueId}/start`);
    expect(startResp.ok()).toBe(true);
    // Resolve
    const resolveResp = await page.request.post(`/api/v1/worker/tasks/${issueId}/resolve`, {
      multipart: {
        photo: {
          name: 'resolve.jpg',
          mimeType: 'image/jpeg',
          buffer: fs.readFileSync(testImage),
        },
      },
    });
    expect(resolveResp.ok()).toBe(true);
    console.log('PHASE 3 DONE: Issue is RESOLVED');

    // PHASE 4: Admin approves
    await loginAs(page, ADMIN_EMAIL, '/authority');
    const approveResp = await page.request.post(`/api/v1/admin/approve?issue_id=${issueId}`);
    expect(approveResp.ok()).toBe(true);
    console.log(`PHASE 4 DONE: Issue ${issueId} is CLOSED`);
  });
});
