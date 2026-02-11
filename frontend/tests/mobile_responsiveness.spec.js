import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'

test.describe('Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('Login page is responsive on mobile', async ({ page }) => {
    await page.goto('/login')
    const loginCard = page.locator('div.bg-white').first()
    await expect(loginCard).toBeVisible()
    
    const boundingBox = await loginCard.boundingBox()
    expect(boundingBox.width).toBeLessThanOrEqual(375)
  })

  test('Citizen Report Issue flow is responsive', async ({ page }) => {
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    const header = page.locator('h2:has-text("Capture Evidence")')
    await expect(header).toBeVisible()
    
    const main = page.locator('main')
    const mainBox = await main.boundingBox()
    expect(mainBox.width).toBeLessThanOrEqual(375)

    const navbar = page.locator('header')
    await expect(navbar).toBeVisible()
  })

  test('Worker Dashboard is responsive', async ({ page }) => {
    await loginAs(page, 'worker@authority.gov.in', '/worker')
    
    const taskCards = page.locator('.card, .bg-white').first()
    if (await taskCards.count() > 0) {
      const cardBox = await taskCards.boundingBox()
      expect(cardBox.width).toBeLessThanOrEqual(375)
    }
  })
})
