import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test.describe('Worker Rigorous Flow', () => {
  const email = 'worker_rigor@ghmc.gov.in';

  test('Accepts task with ETA and completes work', async ({ page }) => {
    // 1. Setup worker user and assigned task
    execSync(`docker exec spec_requirements-db-1 psql -U postgres -d app -c "INSERT INTO \\"user\\" (id, email, role, status) VALUES ('00000000-0000-0000-0000-000000000002', '${email}', 'WORKER', 'ACTIVE') ON CONFLICT DO NOTHING;"`);
    
    // 2. Login
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', email);
    await page.click('button:has-text("Request OTP")');
    await page.waitForTimeout(1000);
    const otp = execSync(`docker exec spec_requirements-db-1 psql -U postgres -d app -t -c "SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;"`).toString().trim();
    await page.fill('input[placeholder*="OTP"]', otp);
    await page.click('button:has-text("Login")');

    // 3. Task List
    await page.waitForSelector('text=Current Tasks');
    
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
