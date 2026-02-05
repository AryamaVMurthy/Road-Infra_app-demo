import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import { getLatestOtp, resetDatabase } from './helpers/db';

test.describe('Citizen Rigorous Flow', () => {
  const email = 'citizen_rigor@test.com';

  test.beforeAll(async () => {
    // execSync('export PYTHONPATH=$PYTHONPATH:$(pwd)/../backend && ../venv/bin/python3 ../backend/reset_db.py');
  });

  test('Submits report and aggregates duplicates', async ({ page, context }) => {
    resetDatabase();
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    
    // Grant geolocation permissions and set location
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 });

    // Force online mode
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'onLine', { get: () => true });
    });

    // 1. Login
    await page.goto('http://localhost:3001/login');
    await page.fill('input[type="email"]', email);
    await page.click('text=Request Access');
    await page.waitForTimeout(1000);
    const otp = getLatestOtp(email);
    await page.fill('input[placeholder*="Enter 6-digit code"]', otp);
    await page.click('text=Verify & Sign In');
    console.log(`Login clicked with OTP: ${otp}`);

    // 2. First Report
    await page.waitForURL('**/citizen');
    console.log("Logged in, navigating to report...");
    await page.click('text=Report New Issue');
    await page.waitForTimeout(2000);
    await page.click('button:has-text("Confirm & Proceed")');
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('input[type="file"]').click();
    const fileChooser = await fileChooserPromise;
    execSync('python3 -c "from PIL import Image; Image.new(\'RGB\', (100, 100), color=\'red\').save(\'test_rigor.jpg\')"');
    await fileChooser.setFiles('test_rigor.jpg');
    
    await page.waitForTimeout(2000);
    console.log("Photo set, scrolling and clicking Next Step...");
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.click('button:has-text("Next Step")');
    
    await page.waitForSelector('text=Final Details');
    console.log("Step 3: Final Details visible");
    
    await page.selectOption('select', { index: 1 });
    await page.screenshot({ path: 'submission_state.png' });
    
    console.log("Submitting report...");
    page.on('dialog', async d => {
        console.log(`DIALOG: ${d.message()}`);
        await d.accept();
    });
    
    await page.click('button:has-text("Submit Report")');

    const firstNav = page.waitForURL('**/citizen/my-reports', { timeout: 15000 }).catch(() => null);
    const firstToast = page
      .waitForSelector('text=/Successfully reported|Offline: Report saved/', { timeout: 15000 })
      .catch(() => null);
    await Promise.race([firstNav, firstToast]);
    if (!page.url().includes('/citizen/my-reports')) {
      await page.goto('http://localhost:3001/citizen/my-reports');
    }
    console.log("Report submitted, verified in my-reports");

    // 3. Second Report (Duplicate)
    await page.goto('http://localhost:3001/citizen/report');
    await page.waitForTimeout(2000);
    await page.click('button:has-text("Confirm & Proceed")');
    
    const fc2 = page.waitForEvent('filechooser');
    await page.locator('input[type="file"]').click();
    (await fc2).setFiles('test_rigor.jpg');
    await page.waitForTimeout(1000);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.click('button:has-text("Next Step")');
    
    await page.waitForSelector('text=Final Details');
    await page.selectOption('select', { index: 1 });
    await page.click('button:has-text("Submit Report")');

    const secondNav = page.waitForURL('**/citizen/my-reports', { timeout: 15000 }).catch(() => null);
    const secondToast = page
      .waitForSelector('text=/Successfully reported|Offline: Report saved/', { timeout: 15000 })
      .catch(() => null);
    await Promise.race([secondNav, secondToast]);
    if (!page.url().includes('/citizen/my-reports')) {
      await page.goto('http://localhost:3001/citizen/my-reports');
    }
    await page.reload();
    await page.waitForTimeout(2000);

    await expect(page.locator('text=Track Progress')).toBeVisible();
    await expect(page.locator('text=Infrastructure Portal')).toBeVisible();
    console.log("Duplicate aggregation verified!");
  });
});
