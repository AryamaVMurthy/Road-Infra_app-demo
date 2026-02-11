import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'
import fs from 'fs'
import path from 'path'

test.describe('Bulk Worker Onboarding', () => {
  test('Admin can onboard workers via CSV', async ({ page }) => {
    await loginAs(page, 'admin@authority.gov.in', '/authority')
    
    await page.click('button:has-text("Field Force")')
    
    await page.click('button:has-text("Onboard Workers")')
    
    await page.click('button:has-text("Bulk Onboard")')
    
    const csvContent = 'worker_test1@example.com\nworker_test2@example.com, worker_test3@example.com'
    const csvPath = path.join(process.cwd(), 'workers_test.csv')
    fs.writeFileSync(csvPath, csvContent)
    
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.click('button:has-text("Import CSV")')
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(csvPath)
    
    const textarea = page.locator('textarea[placeholder*="worker1@ex.com"]')
    await expect(textarea).toHaveValue(/worker_test1@example.com/)
    await expect(textarea).toHaveValue(/worker_test2@example.com/)
    await expect(textarea).toHaveValue(/worker_test3@example.com/)
    
    await page.click('button:has-text("Send Invites")')
    
    await expect(page.locator('h3:has-text("Onboard Workers")')).not.toBeVisible()
    
    fs.unlinkSync(csvPath)
  })
})
