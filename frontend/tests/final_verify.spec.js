import { test, expect } from '@playwright/test'
import { resetDatabase } from './helpers/db'
import { loginAs } from './helpers/e2e'

const personas = [
  { name: 'Citizen', email: 'citizen@example.com', path: '/citizen', anchor: 'Report New Issue' },
  { name: 'Authority', email: 'admin@authority.gov.in', path: '/authority', anchor: 'Kanban Triage' },
  { name: 'Worker', email: 'worker@authority.gov.in', path: '/worker', anchor: 'Assigned Tasks' },
  { name: 'Sysadmin', email: 'sysadmin@marg.gov.in', path: '/admin', anchor: 'Full Analytics' },
]

test.describe('Final Purposeful UI Verification', () => {
  for (const persona of personas) {
    test(`${persona.name} dashboard loads without hard errors`, async ({ page }) => {
      resetDatabase()
      await loginAs(page, persona.email, persona.path)

      await expect(page.locator(`text=${persona.anchor}`)).toBeVisible({ timeout: 15000 })

      const hasCrashText = await page.locator('body').innerText()
      expect(hasCrashText.includes('Internal Server Error')).toBe(false)
      expect(hasCrashText.includes('Cannot read properties')).toBe(false)
    })
  }
})
