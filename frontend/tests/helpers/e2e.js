import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'
import { getLatestOtp } from './db'

export async function loginAs(page, email, targetPath) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })

  const otpRequest = await page.request.post('/api/v1/auth/otp-request', {
    data: { email }
  })

  if (!otpRequest.ok()) {
    throw new Error(`OTP request failed for ${email} with status ${otpRequest.status()}`)
  }

  let otp = ''
  for (let attempt = 0; attempt < 20; attempt += 1) {
    otp = getLatestOtp(email)
    if (otp) {
      break
    }
    await page.waitForTimeout(250)
  }

  if (!otp) {
    throw new Error(`No OTP found in DB for ${email}`)
  }

  const loginResponse = await page.request.post('/api/v1/auth/login', {
    data: { email, otp }
  })

  if (!loginResponse.ok()) {
    throw new Error(`Login failed for ${email} with status ${loginResponse.status()}`)
  }

  await page.goto(targetPath, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(
    () => !document.body.innerText.includes('Loading session...'),
    { timeout: 15000 }
  )
}

export function ensureTestImage(filename = 'golden_test.jpg') {
  const imagePath = path.join(process.cwd(), filename)

  if (!fs.existsSync(imagePath)) {
    execSync(
      `python3 -c "from PIL import Image; Image.new('RGB', (100, 100), color=(255, 0, 0)).save('${imagePath}')"`
    )
  }

  return imagePath
}

export async function waitForMapOrFallback(page, timeout = 15000) {
  const map = page.locator('.mapboxgl-map')
  const fallback = page.getByText('Map unavailable: missing Mapbox token configuration.')

  await Promise.any([
    map.first().waitFor({ state: 'visible', timeout }),
    fallback.waitFor({ state: 'visible', timeout }),
  ])

  if (await fallback.isVisible().catch(() => false)) {
    return 'fallback'
  }

  await map.first().waitFor({ state: 'visible', timeout })
  return 'map'
}
