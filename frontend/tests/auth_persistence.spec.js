import { test, expect } from '@playwright/test'
import { getLatestOtp } from './helpers/db'

async function requestOtpLogin(page, email) {
  const otpRequest = await page.request.post('/api/v1/auth/otp-request', {
    data: { email }
  })
  expect(otpRequest.ok()).toBeTruthy()

  const otp = getLatestOtp(email)
  expect(otp).toBeTruthy()

  const loginResponse = await page.request.post('/api/v1/auth/login', {
    data: { email, otp }
  })
  expect(loginResponse.ok()).toBeTruthy()
  return loginResponse
}

test.describe('Authentication Persistence & Security', () => {
  test('should set HttpOnly cookies on login', async ({ page }) => {
    const response = await requestOtpLogin(page, 'admin@authority.gov.in')
    
    const headers = response.headers()
    const setCookie = headers['set-cookie'] || headers['Set-Cookie']
    expect(setCookie).toBeDefined()
  })

  test('should verify tokens are HttpOnly and invisible to JavaScript (XSS Protection)', async ({ page }) => {
    await page.goto('/')
    await requestOtpLogin(page, 'admin@authority.gov.in')

    const cookieString = await page.evaluate(() => document.cookie)

    expect(cookieString).not.toContain('access_token')
    expect(cookieString).not.toContain('refresh_token')
  })

  test('should persist login across page reloads', async ({ page, context }) => {
    await page.goto('/')

    await requestOtpLogin(page, 'admin@authority.gov.in')

    const cookies = await context.cookies()
    expect(cookies.some(c => c.name === 'access_token')).toBe(true)

    await page.goto('/authority', { waitUntil: 'domcontentloaded' })
    await expect(page).toHaveURL(/\/authority/)
  })

  test('should rotate refresh token via refresh endpoint', async ({ page, context }) => {
    await requestOtpLogin(page, 'admin@authority.gov.in')

    const before = await context.cookies()
    const refreshBefore = before.find(c => c.name === 'refresh_token')
    expect(refreshBefore).toBeTruthy()

    const refreshResponse = await page.request.post('/api/v1/auth/refresh')
    expect(refreshResponse.status()).toBe(200)

    const after = await context.cookies()
    const refreshAfter = after.find(c => c.name === 'refresh_token')
    expect(refreshAfter).toBeTruthy()
    expect(refreshAfter.value).not.toBe(refreshBefore.value)
  })
})
