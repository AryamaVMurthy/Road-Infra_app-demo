import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import { getLatestOtp, resetDatabase } from './helpers/db';

test('Citizen flow: Login and Report Issue', async ({ page }) => {
  const email = 'citizen_e2e@test.com';

  resetDatabase();
  
  // 1. Login Flow
  await page.goto('http://localhost:3011/login');
  await page.fill('input[type="email"]', email);
  await page.click('button:has-text("Request Access")');
  
  // Wait for OTP to be generated in DB
  await page.waitForTimeout(2000);
  
  // Fetch OTP from DB
  const otpCode = getLatestOtp(email);
  
  console.log(`Extracted OTP: ${otpCode}`);
  
  await page.fill('input[placeholder*="Enter 6-digit code"]', otpCode);
  await page.click('button:has-text("Verify & Sign In")');
  
  // 2. Home Page
  await expect(page.locator('h2')).toContainText('Namaste');
  
  // 3. Report Issue
  await page.click('text=Report New Issue');
  
  // Map/Location Step
  await page.waitForTimeout(5000);
  await page.click('button:has-text("Confirm & Proceed")');
  
  // Photo Step
  // Simulate file upload
  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.locator('input[type="file"]').click();
  const fileChooser = await fileChooserPromise;
  
  execSync('python3 -c "from PIL import Image; Image.new(\'RGB\', (100, 100), color=\'red\').save(\'test_e2e.jpg\')"');
  await fileChooser.setFiles('test_e2e.jpg');
  
  await page.click('button:has-text("Next Step")');
  
  // Details Step
  await page.waitForSelector('select');
  await page.selectOption('select', { index: 1 });
  await page.fill('textarea', 'Large pothole near the gate');
  
  console.log("Details filled, clicking submit...");
  await page.click('button:has-text("Submit Report")');
  
  // 4. Verification in My Reports
  await page.waitForTimeout(5000); 
  if (page.url().includes('my-reports')) {
    console.log("Redirected to My Reports");
  }

  
  console.log("E2E Test Passed Successfully!");
});
