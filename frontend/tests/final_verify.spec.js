import { test, expect } from '@playwright/test';
import { resetDatabase } from './helpers/db';

const personas = [
  { name: 'Citizen', email: 'citizen@test.com', url: '/citizen', trigger: 'text=City Analytics' },
  { name: 'Authority', email: 'admin@authority.gov.in', url: '/authority', trigger: 'text=City Analytics' },
  { name: 'Worker', email: 'worker@authority.gov.in', url: '/worker', trigger: 'text=City Health' },
  { name: 'Admin', email: 'sysadmin@test.com', url: '/admin', trigger: 'text=Full Analytics' }
];

test.describe('Final Purposeful UI Verification', () => {
  for (const p of personas) {
    test(`${p.name} dashboard and analytics load correctly`, async ({ page }) => {
      resetDatabase();
      // 1. Mock Login
      await page.goto('http://localhost:3001/login');
      const role = p.name.toUpperCase() === 'AUTHORITY' ? 'ADMIN' : (p.name.toUpperCase() === 'ADMIN' ? 'SYSADMIN' : p.name.toUpperCase());
      
      await page.evaluate(({role, email}) => {
        localStorage.setItem('user', JSON.stringify({
          access_token: 'dummy.payload.dummy',
          role: role,
          sub: email,
          id: '00000000-0000-0000-0000-000000000001'
        }));
      }, {role, email: p.email});

      // 2. Load Dashboard
      await page.goto(`http://localhost:3001${p.url}`);
      await page.waitForTimeout(2000);
      
      // Check for common error text
      const hasError = await page.evaluate(() => document.body.innerText.includes('Internal Server Error') || document.body.innerText.includes('redeclaration'));
      expect(hasError).toBe(false);

      // 3. Navigate to Analytics
      await page.goto('http://localhost:3001/analytics');
      await page.waitForURL('**/analytics');
      
      // 4. Verify Analytics Elements
      await expect(page.locator('h1')).toContainText('City Health Intelligence');
      await expect(page.locator('.leaflet-container')).toBeVisible();
      
      console.log(`${p.name} verification successful!`);
    });
  }
});
