import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'
import { resetDatabase } from './helpers/db'

test.describe('Map Engine Rigor', () => {
  test.beforeEach(async () => {
    resetDatabase()
  })
  
  test.use({ 
    permissions: ['geolocation'],
    geolocation: { latitude: 12.9716, longitude: 77.5946 }
  })

  test('Heatmap and Geocoder exist in Analytics Dashboard', async ({ page }) => {
    await loginAs(page, 'sysadmin@marg.gov.in', '/admin')
    await page.goto('/analytics')
    
    await expect(page.locator('.mapboxgl-map')).toBeVisible()
    
    await page.click('button:has-text("Live Markers")')
    await page.waitForTimeout(1000)
    
    await page.click('button:has-text("Heatmap")')
    await page.waitForTimeout(1000)
    
    await expect(page.locator('.mapboxgl-ctrl-geocoder')).toBeVisible()
  })

  test('Locate control and Geocoder in Report Issue page', async ({ page }) => {
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', {
      name: 'test.png',
      mimeType: 'image/png',
      buffer: Buffer.from('fake-image')
    })
    
    await page.click('button:has-text("Pothole")')
    await page.click('button:has-text("Continue to Location")')
    
    const loader = page.locator('text=Getting your location...')
    if (await loader.isVisible()) {
        await expect(loader).not.toBeVisible({ timeout: 20000 })
    }
    
    await expect(page.locator('.mapboxgl-map')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('.mapboxgl-ctrl-geolocate')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('.mapboxgl-ctrl-geocoder')).toBeVisible({ timeout: 10000 })
    
    await page.fill('.mapboxgl-ctrl-geocoder--input', 'Koramangala')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)
  })
})
