import { test, expect } from '@playwright/test'
import { resetDatabase, getLatestOtp, runSql } from './helpers/db'
import { loginAs } from './helpers/e2e'

test.describe('Sysadmin and Worker Onboarding Flows', () => {
  test.beforeEach(async () => {
    resetDatabase()
  })

  test('Sysadmin can register a new authority with jurisdiction and onboard a worker', async ({ page }) => {
    // 1. Login as Sysadmin
    await loginAs(page, 'sysadmin@marg.gov.in', '/admin')
    
    // 2. Register New Authority
    await page.getByRole('button', { name: 'Authorities' }).click()
    
    await page.getByRole('button', { name: 'Register New Authority' }).click()
    
    const nameInput = page.getByTestId('input-authority-name')
    await nameInput.waitFor({ state: 'visible' })
    await nameInput.fill('Test Authority')
    
    await page.evaluate(() => {
        document.getElementById('btn-simulate-draw')?.click();
    });
    
    await page.getByRole('button', { name: 'Confirm Jurisdiction Area' }).click()
    await expect(page.getByText('Jurisdiction Defined')).toBeVisible()
    
    await page.getByRole('button', { name: 'Register Authority' }).click()
    await expect(page.getByRole('cell', { name: 'Test Authority', exact: true })).toBeVisible()

    // 3. Login as the newly registered Authority's Admin
    // (Note: In a real flow we'd need to create an admin for this org, 
    // but for the sake of UI test we can verify the onboarding UI on the existing admin)
    
    await page.goto('/login')
    await loginAs(page, 'admin@authority.gov.in', '/authority')
    await page.getByRole('button', { name: 'Field Force' }).click()
    
    // Onboard a worker
    await page.getByRole('button', { name: 'Onboard Workers' }).click()
    await page.getByPlaceholder('worker1@ex.com, worker2@ex.com...').fill('newworker@test.com')
    await page.getByRole('button', { name: 'Send Invites' }).click()
    
    await expect(page.getByRole('heading', { name: 'Onboard Workers' })).not.toBeVisible()
    
    const inviteCount = runSql("SELECT count(*) FROM invite WHERE email='newworker@test.com';")
    console.log('Invite count for newworker@test.com:', inviteCount)
    if (inviteCount !== '1') throw new Error('Invite was not created in DB')

    // 4. Verify worker can login and is assigned to org
    await page.goto('/login')
    await loginAs(page, 'newworker@test.com', '/worker')
    
    // Check if worker dashboard loads
    await expect(page.getByText('Assigned Tasks')).toBeVisible()
  })

  test('Sysadmin can manage issue types (CRUD)', async ({ page }) => {
    await loginAs(page, 'sysadmin@marg.gov.in', '/admin')
    await page.getByRole('button', { name: 'Issue Types' }).click()
    
    // Create
    await page.getByRole('button', { name: 'Create Category' }).first().click()
    await page.locator('input').filter({ hasText: '' }).nth(0).fill('Pothole V2')
    await page.locator('#btn-create-category-confirm').click()
    await expect(page.getByRole('cell', { name: 'Pothole V2' })).toBeVisible({ timeout: 10000 })
    
    // Edit
    await page.locator('tr').filter({ hasText: 'Pothole V2' }).getByRole('button').first().click()
    await page.locator('input[type="number"]').fill('10')
    await page.getByRole('button', { name: 'Update Category' }).click()
    await expect(page.getByText('10 Days')).toBeVisible()
  })
})
