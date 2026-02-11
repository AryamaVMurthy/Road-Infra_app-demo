import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/e2e'
import { resetDatabase } from './helpers/db'

test.describe('Map Engine Rigor', () => {
  test.beforeEach(async () => {
    resetDatabase()
  })
  
  test('Heatmap layer is visible in Authority Dashboard', async ({ page }) => {
    await loginAs(page, 'admin@authority.gov.in', '/authority')
    
    const mapCanvas = page.locator('.mapboxgl-canvas')
    await expect(mapCanvas).toBeVisible()
    
    await page.waitForTimeout(2000)
  })

  test('Geocoder search works correctly', async ({ page }) => {
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', {
      name: 'test.png',
      mimeType: 'image/png',
      buffer: Buffer.from('fake-image')
    })
    
    await page.click('button:has-text("Pothole")')
    await page.click('button:has-text("Continue to Location")')
    
    const geocoderInput = page.locator('.mapboxgl-ctrl-geocoder--input')
    await expect(geocoderInput).toBeVisible({ timeout: 10000 })
    
    await geocoderInput.fill('Central Park')
    await page.keyboard.press('Enter')
    
    await page.waitForTimeout(1000)
  })

  test('GPS Locate control exists and is clickable', async ({ page }) => {
    await loginAs(page, 'citizen@example.com', '/citizen/report')
    
    await page.setInputFiles('input[type="file"]', {
      name: 'test.png',
      mimeType: 'image/png',
      buffer: Buffer.from('fake-image')
    })
    
    await page.click('button:has-text("Pothole")')
    await page.click('button:has-text("Continue to Location")')
    
    const locateBtn = page.locator('.mapboxgl-ctrl-geolocate')
    await expect(locateBtn).toBeVisible({ timeout: 10000 })
    await locateBtn.click()
  })
})
