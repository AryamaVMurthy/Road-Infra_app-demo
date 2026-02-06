import { test, expect } from '@playwright/test'
import { resetDatabase } from './helpers/db'
import { loginAs } from './helpers/e2e'

test.describe('City Analytics End-to-End', () => {
  test('sysadmin can access analytics and load map/charts', async ({ page, context }) => {
    resetDatabase()

    await context.grantPermissions(['geolocation'])
    await context.setGeolocation({ latitude: 17.4, longitude: 78.4 })

    await loginAs(page, 'sysadmin@marg.gov.in', '/admin')
    await page.goto('/analytics', { waitUntil: 'domcontentloaded' })

    await expect(page.locator('h1')).toContainText('City Health Intelligence')
    await expect(page.locator('.leaflet-container')).toBeVisible()
    await expect(page.locator('.recharts-surface').first()).toBeVisible()
  })
})
