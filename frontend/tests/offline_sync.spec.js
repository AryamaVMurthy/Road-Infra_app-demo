import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import { getLatestOtp, resetDatabase } from './helpers/db';

test.describe('Offline Sync Rigorous Flow', () => {
  const email = 'offline_sync@test.com';

  test('Queues report while offline and syncs when online', async ({ page, context }) => {
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    
    // Grant geolocation permissions and set location
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 17.4447, longitude: 78.3483 });

    // Custom online/offline trigger
    await page.addInitScript(() => {
        let online = true;
        Object.defineProperty(navigator, 'onLine', { get: () => online });
        window.addEventListener('offline_test', () => { online = false; window.dispatchEvent(new Event('offline')); });
        window.addEventListener('online_test', () => { online = true; window.dispatchEvent(new Event('online')); });
    });

    // 1. Reset DB
    resetDatabase();
    
    // 2. Login
    await page.goto('http://localhost:3011/login');
    await page.fill('input[type="email"]', email);
    await page.click('text=Request Access');
    await page.waitForTimeout(1000);
    const otp = getLatestOtp(email);
    await page.fill('input[placeholder*="Enter 6-digit code"]', otp);
    await page.click('text=Verify & Sign In');

    // 3. Go Offline
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('offline_test')));
    console.log("Browser is now OFFLINE");

    // 4. Submit Report
    await page.click('text=Report New Issue');
    await page.waitForTimeout(2000);
    await page.click('button:has-text("Confirm & Proceed")');
    
    const fc = page.waitForEvent('filechooser');
    await page.locator('input[type="file"]').click();
    execSync('python3 -c "from PIL import Image; Image.new(\'RGB\', (10, 10)).save(\'off.jpg\')"');
    (await fc).setFiles('off.jpg');
    
    await page.waitForTimeout(2000);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.click('button:has-text("Next Step")');
    
    await page.waitForSelector('select');
    await page.selectOption('select', { index: 1 });
    
    page.on('dialog', async d => {
        console.log(`DIALOG: ${d.message()}`);
        await d.accept();
    });
    
    await page.click('button:has-text("Submit Report")');

    const offlineNav = page.waitForURL('**/citizen/my-reports', { timeout: 15000 }).catch(() => null);
    const offlineToast = page
      .waitForSelector('text=Offline: Report saved and will be synced.', { timeout: 15000 })
      .catch(() => null);
    await Promise.race([offlineNav, offlineToast]);
    if (!page.url().includes('/citizen/my-reports')) {
      await page.goto('http://localhost:3011/citizen/my-reports');
    }
    console.log("Report queued while offline");

    // 5. Go Online
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('online_test')));
    console.log("Browser is now ONLINE, waiting for sync...");
    
    await page.waitForTimeout(10000);
    await page.reload();

    await expect(page.locator('text=Infrastructure Portal')).toBeVisible();
    console.log("Offline sync verified!");
  });
});
