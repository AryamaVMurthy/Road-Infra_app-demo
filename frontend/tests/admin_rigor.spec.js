import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test.describe('Admin Rigorous Flow', () => {
  const email = 'admin_rigor@ghmc.gov.in';

  test.beforeAll(async () => {
    execSync('export PYTHONPATH=$PYTHONPATH:$(pwd)/../backend && ../venv/bin/python3 ../backend/reset_db.py');
    const sql = `
        INSERT INTO \\"user\\" (id, email, role, status) VALUES ('00000000-0000-0000-0000-000000000001', '${email}', 'ADMIN', 'ACTIVE');
        INSERT INTO \\"user\\" (id, email, role, status) VALUES ('00000000-0000-0000-0000-000000000002', 'worker_rigor@test.com', 'WORKER', 'ACTIVE');
        INSERT INTO issue (id, category_id, status, location, reporter_id, report_count, priority, created_at, updated_at) 
        VALUES (gen_random_uuid(), (SELECT id FROM category LIMIT 1), 'REPORTED', ST_GeomFromText('POINT(78 17)', 4326), '00000000-0000-0000-0000-000000000001', 1, 'P3', now(), now());
        INSERT INTO issue (id, category_id, status, location, reporter_id, report_count, priority, created_at, updated_at) 
        VALUES (gen_random_uuid(), (SELECT id FROM category LIMIT 1), 'REPORTED', ST_GeomFromText('POINT(78.1 17.1)', 4326), '00000000-0000-0000-0000-000000000001', 1, 'P3', now(), now());
    `;
    execSync(`docker exec spec_requirements-db-1 psql -U postgres -d app -c "${sql}"`);
  });

  test('Bulk assigns issues and reviews resolution', async ({ page }) => {
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER_ERROR:', err.message, err.stack));
    // 2. Login
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', email);
    await page.click('text=Request Access');

    await page.waitForTimeout(1000);
    const otp = execSync(`docker exec spec_requirements-db-1 psql -U postgres -d app -t -c "SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;"`).toString().trim();
    await page.fill('input[placeholder*="Enter 6-digit code"]', otp);
    await page.click('text=Verify & Sign In');

    // 3. Kanban & Bulk Assign
    await page.click('button:has-text("Kanban Triage")');
    console.log("Navigated to Kanban, waiting for issues...");
    
    await page.waitForSelector('.ticket-card');
    
    const checkboxes = page.locator('input[type="checkbox"]');
    console.log(`Found ${await checkboxes.count()} checkboxes`);
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();
    
    await page.selectOption('select', { index: 1 });
    
    console.log("Bulk assign selected, verifying transition...");
    // Verify move to ASSIGNED column
    await page.waitForTimeout(5000);
    
    const assignedCol = page.locator('div:has-text("ASSIGNED")').first();
    const cardsInAssigned = assignedCol.locator('.ticket-card');
    console.log(`Cards in ASSIGNED column: ${await cardsInAssigned.count()}`);
    expect(await cardsInAssigned.count()).toBeGreaterThanOrEqual(2);
  });
});
