
import { chromium } from 'playwright';

void (async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const email = 'worker@authority.gov.in';
  
  console.log('Logging in as worker...');
  await page.goto('http://localhost:3001/login');
  await page.fill('input[type="email"]', email);
  await page.click('button:has-text("Request Access")');
  await page.waitForTimeout(1000);
})();
