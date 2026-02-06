import { test, expect } from '@playwright/test';

test.describe('Authentication Persistence & Security', () => {
  test('should set HttpOnly cookies on login', async ({ page }) => {
    const response = await page.request.post('/api/v1/auth/google-mock?email=admin@authority.gov.in');
    expect(response.ok()).toBeTruthy();
    
    const headers = response.headers();
    const setCookie = headers['set-cookie'] || headers['Set-Cookie'];
    expect(setCookie).toBeDefined();
  });

  test('should verify tokens are HttpOnly and invisible to JavaScript (XSS Protection)', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(async () => {
        await fetch('/api/v1/auth/google-mock?email=admin@authority.gov.in', { method: 'POST' });
    });
    
    const cookieString = await page.evaluate(() => document.cookie);
    
    expect(cookieString).not.toContain('access_token');
    expect(cookieString).not.toContain('refresh_token');
  });

  test('should persist login across page reloads', async ({ page, context }) => {
    await page.goto('/');
    
    await page.evaluate(async () => {
        await fetch('/api/v1/auth/google-mock?email=admin@authority.gov.in', { method: 'POST' });
    });
    
    const cookies = await context.cookies();
    console.log('Cookies after login:', JSON.stringify(cookies, null, 2));
    
    await page.goto('/authority');
    await page.waitForLoadState('networkidle');
    
    const url = page.url();
    if (url.includes('/login')) {
        console.log('Redirected to login. Checking why...');
        const meRes = await page.evaluate(async () => {
            const r = await fetch('/api/v1/auth/me');
            return { status: r.status, body: await r.text() };
        });
        console.log('Direct /me check:', JSON.stringify(meRes, null, 2));
    }
    
    await expect(page).toHaveURL(/\/authority/);
  });

  test('should refresh token automatically on 401', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(async () => {
        await fetch('/api/v1/auth/google-mock?email=admin@authority.gov.in', { method: 'POST' });
    });
    
    await page.goto('/authority');
    
    await page.route('**/api/v1/admin/issues**', async (route) => {
        const request = route.request();
        if (!request.headers()['x-test-retried']) {
            await route.fulfill({
                status: 401,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Token expired' })
            });
        } else {
            await route.continue();
        }
    });
    
    const refreshPromise = page.waitForResponse(resp => 
        resp.url().includes('/api/v1/auth/refresh') && resp.status() === 200
    );
    
    await page.reload(); 
    
    const refreshResponse = await refreshPromise;
    expect(refreshResponse.status()).toBe(200);
  });
});
