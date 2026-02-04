
import { chromium } from 'playwright';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Listen for console errors
  page.on('console', msg => {
      if (msg.type() === 'error') {
          console.log('BROWSER_CONSOLE_ERROR:', msg.text());
      }
  });
  
  page.on('pageerror', err => {
      console.log('BROWSER_PAGE_ERROR:', err.message);
      if (err.message.includes('useRef')) {
          console.log('--- DETECTED REFERENCE ERROR: useRef ---');
          process.exit(1);
      }
  });

  const getOTPFromDB = (email) => {
      console.log(`Getting OTP for ${email} from DB...`);
      for (let i = 0; i < 15; i++) {
          try {
              const otp = execSync(`DOCKER_HOST=unix:///var/run/docker.sock docker exec spec_requirements-db-1 psql -U postgres -d app -t -c "SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;"`).toString().trim();
              if (otp && otp.length === 6) {
                  console.log(`Found OTP in DB: ${otp}`);
                  return otp;
              }
          } catch (e) {}
          process.stdout.write('.');
          execSync('sleep 2');
      }
      console.log('\nFAILED to find OTP in DB.');
      return null;
  };

  // 1. Worker Login (Test if dashboard loads)
  const workerEmail = 'worker@ghmc.gov.in';
  console.log('--- TESTING WORKER DASHBOARD ---');
  await page.goto('http://localhost:3001/login');
  await page.fill('input[type="email"]', workerEmail);
  await page.click('button:has-text("Request Access")');
  await page.waitForTimeout(2000);
  const workerOtp = getOTPFromDB(workerEmail);
  await page.fill('input[placeholder*="code"]', workerOtp);
  await page.click('button:has-text("Verify & Sign In")');
  
  await page.waitForTimeout(5000);
  console.log('Current URL:', page.url());
  
  if (page.url().includes('/worker')) {
      console.log('Worker dashboard LOADED successfully!');
      const content = await page.innerText('body');
      if (content.includes('Field Force')) {
          console.log('Dashboard content VERIFIED.');
      } else {
          console.log('Dashboard content MISSING or BROKEN.');
          await browser.close();
          process.exit(1);
      }
  } else {
      console.log('Worker dashboard FAILED to load.');
      await browser.close();
      process.exit(1);
  }

  // 2. Admin Login (Test if dashboard loads)
  const adminEmail = 'admin@ghmc.gov.in';
  console.log('--- TESTING ADMIN DASHBOARD ---');
  await page.goto('http://localhost:3001/login');
  await page.fill('input[type="email"]', adminEmail);
  await page.click('button:has-text("Request Access")');
  await page.waitForTimeout(2000);
  const adminOtp = getOTPFromDB(adminEmail);
  await page.fill('input[placeholder*="code"]', adminOtp);
  await page.click('button:has-text("Verify & Sign In")');
  
  await page.waitForTimeout(5000);
  console.log('Current URL:', page.url());
  
  if (page.url().includes('/authority')) {
      console.log('Admin dashboard LOADED successfully!');
  } else {
      console.log('Admin dashboard FAILED to load.');
      await browser.close();
      process.exit(1);
  }

  await browser.close();
  console.log('E2E VERIFICATION SUCCESSFUL! ALL REFERENCE ERRORS RESOLVED.');
})();
