import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'

test.describe('Security & RBAC Rigor', () => {
  test('Citizen should be blocked from administrative routes', async ({ page }) => {
    await loginAs(page, 'citizen@example.com', '/citizen')
    
    await page.goto('/authority')
    await expect(page).not.toHaveURL('/authority')
    
    await page.goto('/admin')
    await expect(page).not.toHaveURL('/admin')
  })

  test('Worker should be blocked from administrative routes', async ({ page }) => {
    await loginAs(page, 'worker@authority.gov.in', '/worker')
    
    await page.goto('/authority')
    await expect(page).not.toHaveURL('/authority')
    
    await page.goto('/admin')
    await expect(page).not.toHaveURL('/admin')
  })

  test('Authority Admin should be blocked from SysAdmin route', async ({ page }) => {
    await loginAs(page, 'admin@authority.gov.in', '/authority')
    
    await page.goto('/admin')
    await expect(page).not.toHaveURL('/admin')
  })

  test('Unauthenticated user should be redirected to login', async ({ page }) => {
    await page.goto('/authority')
    await expect(page).toHaveURL(/\/login/)
    
    await page.goto('/worker')
    await expect(page).toHaveURL(/\/login/)
    
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/login/)
  })
})
