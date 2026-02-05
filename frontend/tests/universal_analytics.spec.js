import { test, expect } from '@playwright/test';
import { getLatestOtp, resetDatabase } from './helpers/db';

test.describe('Universal Analytics Rigor', () => {
  const emails = ['citizen_ana@test.com', 'worker_ana@authority.gov.in', 'admin_ana@authority.gov.in', 'sysadmin_ana@test.com'];

  for (const email of emails) {
    test(`Persona ${email} can access and view Big Analytics`, async ({ page }) => {
      // 1. Reset DB for each run to be safe
      resetDatabase();

      // 2. Login
      await page.goto('http://localhost:3001/login');
      await page.fill('input[type="email"]', email);
      await page.click('text=Request Access');
      await page.waitForTimeout(1000);
      const otp = getLatestOtp(email);
      await page.fill('input[placeholder*="Enter 6-digit code"]', otp);
      await page.click('text=Verify & Sign In');

      // 3. Navigate to Analytics
      if (email.includes('citizen')) {
          await page.click('text=City Analytics');
      } else if (email.includes('worker')) {
          await page.click('text=City Health');
      } else if (email.includes('admin')) {
          await page.goto('http://localhost:3001/analytics');
      } else {
          await page.goto('http://localhost:3001/analytics');
      }

      // 4. Verify Analytics Dashboard Elements
      await page.waitForURL('**/analytics');
      await expect(page.locator('h1')).toContainText('City Health Intelligence');
      
      // Verify Map is visible
      await expect(page.locator('.leaflet-container')).toBeVisible();
      
      // Verify Heatmap is active (view mode button)
      await expect(page.locator('button:has-text("Heatmap")')).toHaveClass(/bg-primary/);

      // Verify Charts
      await expect(page.locator('text=Category Distribution')).toBeVisible();
      await expect(page.locator('text=Incident Trends')).toBeVisible();

      console.log(`Persona ${email} analytics access verified!`);
    });
  }
});
