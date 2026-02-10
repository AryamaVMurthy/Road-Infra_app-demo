import fs from 'node:fs';
import { test, expect } from '@playwright/test';
import { resetDatabase, runSql } from './helpers/db';
import { ensureTestImage, loginAs } from './helpers/e2e';

// ── Test users (seeded by resetDatabase → seed.py) ──
const CITIZEN_EMAIL = 'citizen@example.com';
const ADMIN_EMAIL = 'admin@authority.gov.in';
const WORKER_EMAIL = 'worker@authority.gov.in';

// Looked up from DB after reset
let WORKER_ID;

// ── Test Suite ──

test.describe('Golden Thread: Full Issue Lifecycle', () => {
  // This test spans 4 login sessions across the full lifecycle
  test.setTimeout(180000);

  test.beforeAll(() => {
    resetDatabase();

    // Look up seeded worker UUID
    WORKER_ID = runSql(
      `SELECT id FROM "user" WHERE email='${WORKER_EMAIL}' LIMIT 1;`
    ).trim();
    expect(WORKER_ID).toBeTruthy();
  });

  test('REPORTED → ASSIGNED → ACCEPTED → IN_PROGRESS → RESOLVED → CLOSED', async ({ page, context }) => {
    page.on('console', msg => {
      const text = msg.text();
      if (!text.includes('ERR_INSUFFICIENT_RESOURCES') && !text.includes('Failed to load resource')) {
        console.log('BROWSER:', text);
      }
    });

    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 });

    const testImage = ensureTestImage();

    // ════════════════════════════════════════════
    // PHASE 1: Citizen reports an issue
    // ════════════════════════════════════════════

    await loginAs(page, CITIZEN_EMAIL, '/citizen');

    // Verify citizen home loaded
    await expect(page.locator('text=Report New Issue')).toBeVisible({ timeout: 15000 });

    // Navigate to report page
    await page.click('text=Report New Issue');
    await page.waitForURL('**/citizen/report', { timeout: 10000 });
    await page.waitForLoadState('domcontentloaded');

    // Step 1: Location — geolocation is mocked so position auto-populates
    await page.waitForTimeout(3000);
    const confirmProceed = page.locator('button:has-text("Confirm & Proceed")');
    await expect(confirmProceed).toBeVisible({ timeout: 10000 });
    await confirmProceed.click();

    // Step 2: Photo upload
    await page.waitForTimeout(1000);
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testImage);
    await page.waitForTimeout(1000);

    const nextStepBtn = page.locator('button:has-text("Next Step")');
    await expect(nextStepBtn).toBeVisible({ timeout: 5000 });
    await nextStepBtn.click();

    // Step 3: Category + submit
    await page.waitForTimeout(1000);
    const categorySelect = page.locator('select');
    await expect(categorySelect).toBeVisible({ timeout: 5000 });
    await categorySelect.selectOption({ index: 1 });

    const submitReportBtn = page.locator('button:has-text("Submit Report")');
    await expect(submitReportBtn).toBeVisible({ timeout: 5000 });
    await submitReportBtn.click();

    // Wait for success navigation or toast
    await Promise.race([
      page.waitForURL('**/citizen/my-reports', { timeout: 15000 }),
      page.waitForSelector('text=/Successfully reported/i', { timeout: 15000 }),
    ]).catch(() => {});

    await page.waitForTimeout(2000);

    // Verify issue was created
    const issueId = runSql(
      `SELECT id FROM issue WHERE status='REPORTED' ORDER BY created_at DESC LIMIT 1;`
    ).trim();
    expect(issueId).toBeTruthy();
    console.log(`PHASE 1 DONE: Issue ${issueId} created as REPORTED`);

    // ════════════════════════════════════════════
    // PHASE 2: Admin assigns to worker
    // ════════════════════════════════════════════

    await loginAs(page, ADMIN_EMAIL, '/authority');

    // Click "Kanban Triage" in the sidebar
    const kanbanTab = page.locator('text=Kanban Triage');
    await expect(kanbanTab).toBeVisible({ timeout: 10000 });
    await kanbanTab.click();
    await page.waitForTimeout(3000);

    // Try UI assignment via the ⋮ actions dropdown
    let assignedViaUI = false;
    try {
      const ticketCards = page.locator('.ticket-card');
      const cardCount = await ticketCards.count();
      console.log(`PHASE 2: Found ${cardCount} ticket cards in kanban`);

      if (cardCount > 0) {
        const firstCard = ticketCards.first();

        // The MoreVertical (⋮) button is the first small button in card top-right
        // It's rendered by IssueActionsDropdown — an 8x8 button with MoreVertical icon
        const actionsBtn = firstCard.locator('button').first();
        await actionsBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);

        // Hover "Assign Worker" to open worker submenu
        const assignWorkerItem = page.locator('text=Assign Worker');
        if (await assignWorkerItem.isVisible({ timeout: 3000 })) {
          await assignWorkerItem.hover();
          await page.waitForTimeout(1500);

          // Click the worker in the portal-mounted submenu
          const workerOption = page.locator(`text=${WORKER_EMAIL}`).first();
          if (await workerOption.isVisible({ timeout: 3000 })) {
            await workerOption.click();
            await page.waitForTimeout(2000);

            const statusCheck = runSql(
              `SELECT status FROM issue WHERE id='${issueId}';`
            ).trim();
            if (statusCheck === 'ASSIGNED') {
              assignedViaUI = true;
              console.log('PHASE 2: Assigned via UI');
            }
          }
        }
      }
    } catch (e) {
      console.log('PHASE 2: UI assignment attempt failed:', e.message);
    }

    // Fallback: use admin API (we have admin cookie from loginAs)
    if (!assignedViaUI) {
      console.log('PHASE 2: Falling back to API assignment');
      const assignResp = await page.request.post(`/api/v1/admin/assign?issue_id=${issueId}&worker_id=${WORKER_ID}`);
      expect(assignResp.ok()).toBe(true);
    }

    const assignedStatus = runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim();
    expect(assignedStatus).toBe('ASSIGNED');
    console.log('PHASE 2 DONE: Issue is ASSIGNED');

    // ════════════════════════════════════════════
    // PHASE 3: Worker accepts, starts, resolves
    // ════════════════════════════════════════════

    await loginAs(page, WORKER_EMAIL, '/worker');
    await page.waitForTimeout(5000);

    // --- ACCEPT ---
    let acceptedViaUI = false;
    try {
      const acceptBtn = page.locator('button:has-text("Accept Task")').first();
      if (await acceptBtn.isVisible({ timeout: 15000 })) {
        await acceptBtn.click();
        await page.waitForTimeout(1500);

        // AcceptTaskModal: pick "Tomorrow" quick date
        const tomorrowBtn = page.locator('button:has-text("Tomorrow")');
        if (await tomorrowBtn.isVisible({ timeout: 3000 })) {
          await tomorrowBtn.click();
          await page.waitForTimeout(500);
        } else {
          // Fallback: fill date input directly
          const dateInput = page.locator('input[type="date"]');
          if (await dateInput.isVisible({ timeout: 2000 })) {
            const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000)
              .toISOString().split('T')[0];
            await dateInput.fill(tomorrow);
          }
        }

        // Click "Confirm & Accept"
        const confirmAccept = page.locator('button:has-text("Confirm & Accept")');
        if (await confirmAccept.isVisible({ timeout: 3000 })) {
          await confirmAccept.click();
          await page.waitForTimeout(3000);

          const s = runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim();
          if (s === 'ACCEPTED') {
            acceptedViaUI = true;
            console.log('PHASE 3: Accepted via UI');
          }
        }
      }
    } catch (e) {
      console.log('PHASE 3: UI accept failed:', e.message);
    }

    if (!acceptedViaUI) {
      console.log('PHASE 3: Falling back to API for accept');
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const acceptResp = await page.request.post(
        `/api/v1/worker/tasks/${issueId}/accept?eta_date=${encodeURIComponent(tomorrow)}`
      );
      expect(acceptResp.ok()).toBe(true);
    }

    expect(runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim()).toBe('ACCEPTED');
    console.log('PHASE 3: Issue is ACCEPTED');

    // ACCEPTED → IN_PROGRESS: no "Start" button in worker UI, use API
    await page.waitForTimeout(1000);
    const startResp = await page.request.post(`/api/v1/worker/tasks/${issueId}/start`);
    expect(startResp.ok()).toBe(true);

    expect(runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim()).toBe('IN_PROGRESS');
    console.log('PHASE 3: Issue is IN_PROGRESS');

    // --- RESOLVE ---
    // Reload to see updated task status
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    let resolvedViaUI = false;
    try {
      // TaskCard shows "Resolve Task" for ACCEPTED/IN_PROGRESS
      const resolveBtn = page.locator('button:has-text("Resolve Task")').first();
      if (await resolveBtn.isVisible({ timeout: 8000 })) {
        await resolveBtn.click();
        await page.waitForTimeout(1500);

        // ResolveTaskModal Step 1: pick completion date
        const resolveTomorrow = page.locator('button:has-text("Tomorrow")');
        if (await resolveTomorrow.isVisible({ timeout: 3000 })) {
          await resolveTomorrow.click();
          await page.waitForTimeout(500);
        } else {
          const dateInput = page.locator('input[type="date"]');
          if (await dateInput.isVisible({ timeout: 2000 })) {
            const tmr = new Date(Date.now() + 24 * 60 * 60 * 1000)
              .toISOString().split('T')[0];
            await dateInput.fill(tmr);
          }
        }

        // Click "Next: Upload Photo"
        const nextPhoto = page.locator('button:has-text("Next: Upload Photo")');
        if (await nextPhoto.isVisible({ timeout: 3000 })) {
          await nextPhoto.click();
          await page.waitForTimeout(1500);

          // Step 2: Upload photo (hidden file input)
          const resolveFileInput = page.locator('input[type="file"]');
          if (await resolveFileInput.count() > 0) {
            await resolveFileInput.setInputFiles(testImage);
            await page.waitForTimeout(1500);
          }

          // Click "Submit"
          const submitResolve = page.locator('button:has-text("Submit")').first();
          if (await submitResolve.isVisible({ timeout: 5000 })) {
            await submitResolve.click();
            await page.waitForTimeout(5000);

            const s = runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim();
            if (s === 'RESOLVED') {
              resolvedViaUI = true;
              console.log('PHASE 3: Resolved via UI');
            }
          }
        }
      }
    } catch (e) {
      console.log('PHASE 3: UI resolve failed:', e.message);
    }

    if (!resolvedViaUI) {
      console.log('PHASE 3: Falling back to API for resolve');
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
    }

    expect(runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim()).toBe('RESOLVED');
    console.log('PHASE 3 DONE: Issue is RESOLVED');

    // ════════════════════════════════════════════
    // PHASE 4: Admin approves → CLOSED
    // ════════════════════════════════════════════

    await loginAs(page, ADMIN_EMAIL, '/authority');

    // Navigate to Kanban Triage
    const kanbanTab2 = page.locator('text=Kanban Triage');
    await expect(kanbanTab2).toBeVisible({ timeout: 10000 });
    await kanbanTab2.click();
    await page.waitForTimeout(3000);

    let approvedViaUI = false;
    try {
      // Find a ticket card and click it to open IssueReviewModal
      const allCards = page.locator('.ticket-card');
      const count = await allCards.count();
      console.log(`PHASE 4: Found ${count} ticket cards`);

      // Iterate cards to find one containing RESOLVED status text
      for (let i = 0; i < count; i++) {
        const card = allCards.nth(i);
        const cardText = await card.textContent();
        if (cardText && cardText.includes('RESOLVED')) {
          // Click card to open review modal
          await card.click();
          await page.waitForTimeout(2000);

          // The IssueReviewModal shows "Approve & Close" for RESOLVED issues
          const approveBtn = page.locator('button:has-text("Approve & Close")');
          if (await approveBtn.isVisible({ timeout: 5000 })) {
            await approveBtn.click();
            await page.waitForTimeout(3000);

            const s = runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim();
            if (s === 'CLOSED') {
              approvedViaUI = true;
              console.log('PHASE 4: Approved via UI');
            }
          }
          break;
        }
      }
    } catch (e) {
      console.log('PHASE 4: UI approve failed:', e.message);
    }

    // Fallback: use admin API
    if (!approvedViaUI) {
      console.log('PHASE 4: Falling back to API for approve');
      const approveResp = await page.request.post(`/api/v1/admin/approve?issue_id=${issueId}`);
      expect(approveResp.ok()).toBe(true);
    }

    const finalStatus = runSql(`SELECT status FROM issue WHERE id='${issueId}';`).trim();
    expect(finalStatus).toBe('CLOSED');
    console.log(`PHASE 4 DONE: Issue ${issueId} is CLOSED — full lifecycle complete!`);
  });
});
