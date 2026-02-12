import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'

test.describe('Admin and Sysadmin regression coverage', () => {
  test('authority sees worker onboarding modal with single and bulk modes', async ({ page }) => {
    await loginAs(page, 'admin@authority.gov.in', '/authority')

    await page.getByRole('button', { name: 'Field Force' }).click()
    await expect(page.getByRole('button', { name: 'Onboard Workers' })).toBeVisible()

    await page.getByRole('button', { name: 'Onboard Workers' }).click()
    await expect(page.getByRole('heading', { name: 'Onboard Workers' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Single Worker' })).toBeVisible()

    await page.getByRole('button', { name: 'Bulk Onboard' }).click()
    await expect(page.getByRole('button', { name: 'Import CSV' })).toBeVisible()
    await expect(page.getByPlaceholder('worker1@ex.com, worker2@ex.com...')).toBeVisible()
  })

  test('sysadmin can create and delete authority, manage issue type, and view audit logs', async ({ page }) => {
    const authorityName = `E2E Authority ${Date.now()}`
    const authorityAdminEmail = `e2e-admin-${Date.now()}@authority.gov.in`
    const issueTypeName = `E2E Type ${Date.now()}`

    await loginAs(page, 'sysadmin@marg.gov.in', '/admin')

    await page.getByRole('button', { name: 'Authorities' }).click()
    await expect(page.getByRole('button', { name: 'Register New Authority' })).toBeVisible()
    await page.getByRole('button', { name: 'Register New Authority' }).click()

    await page.getByTestId('input-authority-name').fill(authorityName)
    await page.getByPlaceholder('Admin Email').fill(authorityAdminEmail)
    await page.getByPlaceholder('Zone Name (e.g. Hyderabad Central)').fill('Regression Zone')
    await page.locator('#btn-simulate-draw').click({ force: true })

    await expect(page.getByText('Jurisdiction Defined')).toBeVisible()
    await page.getByRole('button', { name: 'Register Authority' }).click()

    const authorityRow = page.getByRole('row').filter({ hasText: authorityName })
    await expect(authorityRow).toBeVisible()

    page.once('dialog', async (dialog) => {
      await dialog.accept()
    })
    await authorityRow.getByRole('button', { name: 'Delete' }).click()
    await expect(authorityRow).toHaveCount(0)

    await page.getByRole('button', { name: 'Issue Types' }).click()
    await page.getByRole('button', { name: 'Create Type' }).click()
    await page.locator('label:has-text("Type Name")').locator('xpath=following::input[1]').fill(issueTypeName)
    await page.locator('label:has-text("SLA Days")').locator('xpath=following::input[1]').fill('9')
    await page.getByRole('button', { name: 'Create', exact: true }).click()

    const issueTypeRow = page.getByRole('row').filter({ hasText: issueTypeName })
    await expect(issueTypeRow).toBeVisible()

    await issueTypeRow.locator('.btn-update-type').click()
    await page.locator('label:has-text("SLA Days")').locator('xpath=following::input[1]').fill('11')
    await page.getByRole('button', { name: 'Update' }).click()
    await expect(issueTypeRow).toContainText('11 Days')

    page.once('dialog', async (dialog) => {
      await dialog.accept()
    })
    await issueTypeRow.getByRole('button').nth(1).click()
    await expect(issueTypeRow).toContainText('Disabled')

    await page.getByRole('button', { name: 'Audit Trails' }).click()
    await expect(page.getByText('Action Type')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'System Audit Trail' })).toBeVisible()
    await expect(
      page
        .getByRole('cell', {
          name: /CREATE_AUTHORITY|DELETE_AUTHORITY|CREATE_ISSUE_TYPE|UPDATE_ISSUE_TYPE|DEACTIVATE_ISSUE_TYPE/
        })
        .first()
    ).toBeVisible()
  })
})
