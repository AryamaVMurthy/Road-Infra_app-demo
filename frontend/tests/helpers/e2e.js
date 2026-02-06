import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'

export async function loginAs(page, email, targetPath) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })

  const response = await page.request.post(
    `/api/v1/auth/google-mock?email=${encodeURIComponent(email)}`
  )

  if (!response.ok()) {
    throw new Error(`Login failed for ${email} with status ${response.status()}`)
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
