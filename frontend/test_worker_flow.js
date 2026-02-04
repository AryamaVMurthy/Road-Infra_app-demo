
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const email = 'worker@authority.gov.in';
  const otp = '333406'; // Reuse previous OTP if still valid, or I'll request a new one
  
  console.log('Logging in as worker...');
  await page.goto('http://localhost:3001/login');
  await page.fill('input[type="email"]', email);
  await page.click('button:has-text("Request Access")');
  await page.waitForTimeout(1000);
  // Actually I should get the fresh OTP
  // But for now I'll just use the one I got earlier if it works, otherwise I'll fail and fix.
  // Wait, I'll request a new one to be safe.
})();
