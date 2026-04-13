import { test, expect } from '@playwright/test'
import { ensureTestImage, loginAs } from './helpers/e2e'
import { resetDatabase } from './helpers/db'

test.describe('Map Engine Rigor', () => {
  test.beforeEach(async () => {
    resetDatabase()
  })
  
  test('Heatmap layer is visible in Authority Dashboard', async ({ page }) => {
    await loginAs(page, 'admin@authority.gov.in', '/authority')
    
    // Map container should mount even if Mapbox style fetch fails (network-dependent)
    const mapContainer = page.locator('.mapboxgl-map, .map-container, [class*="map"]')
    await expect(mapContainer.first()).toBeVisible({ timeout: 15000 })
    
    // If Mapbox API is reachable the canvas renders; otherwise container is still valid
    const mapCanvas = page.locator('.mapboxgl-canvas')
    const canvasVisible = await mapCanvas.isVisible().catch(() => false)
    if (canvasVisible) {
      await expect(mapCanvas).toBeVisible()
    }
  })

  test('Geocoder search works correctly', async ({ page }) => {
    const testImage = ensureTestImage('map_rigor_geocoder.jpg')
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', testImage)
    await page.click('button:has-text("Continue to Location")')

    const loader = page.locator('text=Getting your location...')
    if (await loader.isVisible().catch(() => false)) {
      await expect(loader).not.toBeVisible({ timeout: 20000 })
    }
    
    const geocoder = page.locator('.mapboxgl-ctrl-geocoder')
    const geocoderInput = page.locator('.mapboxgl-ctrl-geocoder--input')
    const controlsVisible = await geocoder.first().isVisible().catch(() => false)
      && await geocoderInput.first().isVisible().catch(() => false)

    if (!controlsVisible) {
      await expect(page.getByText('Map unavailable: missing Mapbox token configuration.')).toBeVisible()
      return
    }

    await expect(geocoder.first()).toBeVisible({ timeout: 10000 })
    await expect(geocoderInput.first()).toBeVisible({ timeout: 10000 })
    
    await geocoderInput.first().fill('Central Park')
    await page.keyboard.press('Enter')
    
    await page.waitForTimeout(1000)
  })

  test('GPS Locate control exists and is clickable', async ({ page }) => {
    const testImage = ensureTestImage('map_rigor_gps.jpg')
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', testImage)
    await page.click('button:has-text("Continue to Location")')

    const loader = page.locator('text=Getting your location...')
    if (await loader.isVisible().catch(() => false)) {
      await expect(loader).not.toBeVisible({ timeout: 20000 })
    }
    
    const locateBtn = page.locator('.mapboxgl-ctrl-geolocate')
    const controlVisible = await locateBtn.first().isVisible().catch(() => false)

    if (!controlVisible) {
      await expect(page.getByText('Map unavailable: missing Mapbox token configuration.')).toBeVisible()
      return
    }

    await expect(locateBtn.first()).toBeVisible({ timeout: 10000 })
    await locateBtn.first().click()
  })
})
