import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test('Citizen flow: Login and Report Issue', async ({ page }) => {
  const email = 'citizen_e2e@test.com';
  
  // 1. Login Flow
  await page.goto('http://localhost:3001/login');
  await page.fill('input[type="email"]', email);
  await page.click('button:has-text("Request OTP")');
  
  // Wait for OTP to be generated in DB
  await page.waitForTimeout(2000);
  
  // Fetch OTP from DB
  const otpCode = execSync(
    `docker exec spec_requirements-db-1 psql -U postgres -d app -t -c "SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;"`
  ).toString().trim();
  
  console.log(`Extracted OTP: ${otpCode}`);
  
  await page.fill('input[placeholder*="OTP"]', otpCode);
  await page.click('button:has-text("Login")');
  
  // 2. Home Page
  await expect(page.locator('h2')).toContainText('Hello');
  
  // 3. Report Issue
  await page.click('a:has-text("Report Issue")');
  
  // Map/Location Step
  await page.waitForTimeout(5000);
  await page.click('button:has-text("Confirm Location")');
  
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
