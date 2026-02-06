import { test, expect } from '@playwright/test'
import { resetDatabase } from './helpers/db'
import { loginAs } from './helpers/e2e'

test.describe('Universal Analytics Rigor', () => {
  const personas = [
    { email: 'citizen@example.com', path: '/citizen' },
    { email: 'worker@authority.gov.in', path: '/worker' },
    { email: 'admin@authority.gov.in', path: '/authority' },
    { email: 'sysadmin@marg.gov.in', path: '/admin' },
  ]

  for (const persona of personas) {
    test(`persona ${persona.email} can open analytics page`, async ({ page }) => {
      resetDatabase()
      await loginAs(page, persona.email, persona.path)

      await page.goto('/analytics', { waitUntil: 'domcontentloaded' })

      await expect(page).toHaveURL(/\/analytics/)
      await expect(page.locator('h1')).toContainText('City Health Intelligence')
      await expect(page.locator('.leaflet-container')).toBeVisible()
      await expect(page.locator('.recharts-surface').first()).toBeVisible()
    })
  }
})
