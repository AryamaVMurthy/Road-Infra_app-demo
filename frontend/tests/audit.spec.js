import { test, expect } from '@playwright/test';
import { getLatestOtp } from './helpers/db.js';

const USERS = [
  { email: 'citizen@example.com', role: 'CITIZEN', dashboard: '/citizen', extraRoutes: ['/citizen/report', '/citizen/my-reports'] },
  { email: 'admin@authority.gov.in', role: 'ADMIN', dashboard: '/authority', extraRoutes: [] },
  { email: 'worker@authority.gov.in', role: 'WORKER', dashboard: '/worker', extraRoutes: [] },
  { email: 'sysadmin@marg.gov.in', role: 'SYSADMIN', dashboard: '/admin', extraRoutes: [] }
];

const COMMON_ROUTES = ['/login', '/analytics'];

test.describe('Audit Application Routes', () => {
  test.use({ 
    baseURL: 'http://localhost:3011',
    permissions: ['geolocation'],
    geolocation: { latitude: 12.9716, longitude: 77.5946 }
  });
  let consoleErrors = [];

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
      if (msg.type() === 'error') {
        const errorMsg = `[${page.url()}] ${msg.text()}`;
        consoleErrors.push(errorMsg);
      }
    });
    page.on('pageerror', err => {
      const errorMsg = `[${page.url()}] PAGE ERROR: ${err.message}`;
      consoleErrors.push(errorMsg);
      console.log('PAGE ERROR:', errorMsg);
    });
  });

  test('Public Routes Audit', async ({ page }) => {
    for (const route of COMMON_ROUTES) {
      console.log(`Auditing ${route}...`);
      await page.goto(route);
      await expect(page).toHaveURL(new RegExp(route));
      
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(1000);
      
      await expect(page.locator('body')).toBeVisible();
      
      const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = await page.viewportSize().width;
      
      if (scrollWidth > viewportWidth + 5) {
         console.log(`[Responsiveness Warning] ${route} has horizontal scroll: ${scrollWidth} > ${viewportWidth}`);
      }
    }
  });

  for (const user of USERS) {
    test(`Audit ${user.role} Routes`, async ({ page }) => {
        console.log(`Logging in as ${user.role} (${user.email})...`);
        await page.goto('/login');
        await page.fill('input[type="email"]', user.email);
        await page.click('button[type="submit"]');
        
        await page.waitForTimeout(2000); 
        const otp = getLatestOtp(user.email);
        expect(otp).toBeTruthy();
        console.log(`OTP for ${user.email}: ${otp}`);
        
        await page.fill('input[placeholder="Enter 6-digit code"]', otp);
        await page.click('button:has-text("Verify & Sign In")');
        
        await expect(page).toHaveURL(new RegExp(user.dashboard), { timeout: 10000 });

        const routes = [user.dashboard, ...user.extraRoutes];
        
        for (const route of routes) {
            console.log(`Auditing ${route}...`);
            await page.goto(route);
            
            await page.setViewportSize({ width: 375, height: 667 });
            await page.waitForTimeout(1000);
            
            await expect(page.locator('body')).toBeVisible();
            const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
            const viewportWidth = await page.viewportSize().width;
            if (scrollWidth > viewportWidth + 5) {
                console.log(`[Responsiveness Warning] ${route} has horizontal scroll: ${scrollWidth} > ${viewportWidth}`);
            }

            if (route === '/authority' && user.role === 'ADMIN') {
                await page.setViewportSize({ width: 1280, height: 720 });
                await page.click('button:has-text("Field Force")');
                const onboardBtn = page.locator('button:has-text("Onboard Workers")');
                if (await onboardBtn.isVisible()) {
                    await onboardBtn.click();
                    await expect(page.locator('div[role="dialog"], div.fixed.inset-0')).toBeVisible(); 
                    await page.locator('div.fixed.inset-0 button:has(svg.lucide-x)').first().click();
                } else {
                    console.log('Worker onboarding button not found on /authority');
                }
            }
            
            if (route === '/admin' && user.role === 'SYSADMIN') {
                 await page.setViewportSize({ width: 1280, height: 720 });
                 await expect(page.locator('h1:has-text("MARG IT Admin")')).toBeVisible({ timeout: 15000 });
                 await page.click('#btn-authorities');
                 await expect(page.locator('h3:has-text("Government Authorities")')).toBeVisible();
            }

            if (route === '/analytics' || route === '/citizen/report' || route === '/authority') {
                await page.waitForTimeout(2000);
            }
        }
    });
  }
});