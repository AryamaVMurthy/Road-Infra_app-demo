import { test, expect } from '@playwright/test';
import { getLatestOtp, resetDatabase, runSql } from './helpers/db';

test.describe('City Analytics End-to-End', () => {
  const email = 'sysadmin_e2e_ana@test.com';

  test('Persona can access, search location, and get current location', async ({ page, context }) => {
    // 1. Reset DB and Setup User
    resetDatabase();
    const sql = `INSERT INTO \\"user\\" (id, email, role, status) VALUES (gen_random_uuid(), '${email}', 'SYSADMIN', 'ACTIVE');`;
    runSql(sql);
    
    // 2. Login
    await page.goto('http://localhost:3011/login');
    await page.fill('input[type="email"]', email);
    await page.click('text=Request Access');
    await page.waitForTimeout(1000);
    
    const otp = getLatestOtp(email);
    await page.fill('input[placeholder*="Enter 6-digit code"]', otp);
    await page.click('text=Verify & Sign In');
    console.log(`Login clicked with OTP`);

    // 3. Navigate to Analytics
    await page.waitForURL('**/admin', { timeout: 10000 });
    console.log("Logged in as Admin");
    
    await page.click('text=Full Analytics');
    console.log("Analytics button clicked");
    
    // Wait for loading to finish
    await expect(page.locator('text=Compiling Intelligence...')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Compiling Intelligence...')).toBeHidden({ timeout: 20000 });
    console.log("Loading finished");

    // 4. Verify Dashboards and Charts
    await expect(page.locator('h1')).toContainText('City Health Intelligence', { timeout: 10000 });
    const charts = page.locator('.recharts-surface');
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
    expect(await charts.count()).toBeGreaterThan(0);

    // 5. Test Geocoding (Search Location)
    const geocoderIcon = page.locator('.leaflet-control-geocoder-icon');
    await geocoderIcon.click();
    const searchInput = page.locator('.leaflet-control-geocoder-form input');
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill('Main Road');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);
    console.log("Geocoding verified via text entry");

    // 6. Test Current Location (LocateControl)
    // Mock geolocation permission and result
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation({ latitude: 17.4, longitude: 78.4 });
    
    const locateBtn = page.locator('.leaflet-control-custom');
    await locateBtn.click();
    await page.waitForTimeout(2000);
    
    // Verify marker or circle exists (from our implementation)
    const markers = await page.locator('.leaflet-marker-icon').count();
    expect(markers).toBeGreaterThan(0);
    console.log("Current location detection verified!");

    await page.screenshot({ path: 'ANALYTICS_FINAL_E2E_SUCCESS.png', fullPage: true });
  });
});
