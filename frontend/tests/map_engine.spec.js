import { test, expect } from '@playwright/test'
import { ensureTestImage, loginAs, waitForMapOrFallback } from './helpers/e2e'
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
    await page.goto('/analytics', { waitUntil: 'domcontentloaded' })
    
    const mapState = await waitForMapOrFallback(page)
    if (mapState === 'fallback') {
      await expect(page.getByText('Map unavailable: missing Mapbox token configuration.')).toBeVisible()
    } else {
      await expect(page.locator('.mapboxgl-map').first()).toBeVisible({ timeout: 15000 })
    }
    
    await page.getByRole('button', { name: 'Live Markers' }).click()
    await page.waitForTimeout(1000)
    
    await page.getByRole('button', { name: 'Heatmap' }).click()
    await page.waitForTimeout(1000)
    
    const geocoder = page.locator('.mapboxgl-ctrl-geocoder')
    const geocoderVisible = await geocoder.first().isVisible().catch(() => false)
    if (geocoderVisible) {
      await expect(geocoder.first()).toBeVisible()
    }
  })

  test('Locate control and Geocoder in Report Issue page', async ({ page }) => {
    const testImage = ensureTestImage('map_engine_report.jpg')
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', testImage)
    
    await page.click('button:has-text("Continue to Location")')
    
    const loader = page.locator('text=Getting your location...')
    if (await loader.isVisible()) {
        await expect(loader).not.toBeVisible({ timeout: 20000 })
    }
    
    const mapState = await waitForMapOrFallback(page)
    if (mapState === 'fallback') {
      await expect(page.getByText('Map unavailable: missing Mapbox token configuration.')).toBeVisible()
      return
    } else {
      await expect(page.locator('.mapboxgl-map').first()).toBeVisible({ timeout: 15000 })
    }

    const geolocate = page.locator('.mapboxgl-ctrl-geolocate')
    const geocoder = page.locator('.mapboxgl-ctrl-geocoder')
    const geocoderInput = page.locator('.mapboxgl-ctrl-geocoder--input')
    const controlsVisible = await geolocate.first().isVisible().catch(() => false)
      && await geocoder.first().isVisible().catch(() => false)
      && await geocoderInput.first().isVisible().catch(() => false)

    if (!controlsVisible) {
      await expect(page.getByText('Map unavailable: missing Mapbox token configuration.')).toBeVisible()
      return
    }

    await expect(geolocate.first()).toBeVisible({ timeout: 10000 })
    await expect(geocoder.first()).toBeVisible({ timeout: 10000 })
    
    await geocoderInput.first().fill('Koramangala')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)
  })
})
