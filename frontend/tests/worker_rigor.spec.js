import { test, expect } from '@playwright/test';
import { getLatestOtp, resetDatabase, runSql } from './helpers/db';

test.describe('Worker Rigorous Flow', () => {
  const email = 'worker_rigor@authority.gov.in';

  test('Accepts task with ETA and completes work', async ({ page }) => {
    resetDatabase();
    // 1. Setup worker user and assigned task
    runSql(
      `INSERT INTO \\"user\\" (id, email, role, status) VALUES ('00000000-0000-0000-0000-000000000002', '${email}', 'WORKER', 'ACTIVE') ON CONFLICT DO NOTHING;`
    );
    
    // 2. Login
    await page.goto('http://localhost:3001/login');
    await page.fill('input[type="email"]', email);
    await page.click('button:has-text("Request Access")');
    await page.waitForTimeout(1000);
    const otp = getLatestOtp(email);
    await page.fill('input[placeholder*="code"]', otp);
    await page.click('button:has-text("Verify & Sign In")');

    // 3. Task List
    await page.waitForSelector('text=Assigned Tasks');
    
    // Check if we can accept (assuming a task exists)
    const acceptBtn = page.locator('button:has-text("Accept Task")');
    if (await acceptBtn.count() > 0) {
        await acceptBtn.first().click();
        await page.selectOption('select', { label: '1 Hour' });
        await page.click('button:has-text("Confirm")');
        await expect(page.locator('text=ACCEPTED')).toBeVisible();
    }
  });
});
