// Visual regression tests for pricing and subscription UI
const { test, expect } = require('@playwright/test');

test.describe('Visual Regression Tests', () => {
  
  test('Pricing Page: Desktop Layout', async ({ page }) => {
    await page.goto('/#pricing');
    
    // Wait for content to load
    await page.waitForSelector('text="Simple, Transparent Pricing"');
    await page.waitForSelector('text="Free"');
    await page.waitForSelector('text="Hobby"');
    
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Scroll to pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    
    // Take screenshot of pricing section
    await expect(page.locator('#pricing')).toHaveScreenshot('pricing-desktop.png');
    
    console.log('✅ Desktop pricing layout screenshot captured');
  });

  test('Pricing Page: Mobile Layout', async ({ page }) => {
    await page.goto('/#pricing');
    
    // Wait for content to load
    await page.waitForSelector('text="Simple, Transparent Pricing"');
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Scroll to pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    
    // Take screenshot of pricing section on mobile
    await expect(page.locator('#pricing')).toHaveScreenshot('pricing-mobile.png');
    
    console.log('✅ Mobile pricing layout screenshot captured');
  });

  test('Pricing Page: Tablet Layout', async ({ page }) => {
    await page.goto('/#pricing');
    
    // Wait for content to load
    await page.waitForSelector('text="Simple, Transparent Pricing"');
    
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // Scroll to pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    
    // Take screenshot of pricing section on tablet
    await expect(page.locator('#pricing')).toHaveScreenshot('pricing-tablet.png');
    
    console.log('✅ Tablet pricing layout screenshot captured');
  });

  test('Individual Plan Cards: Visual Consistency', async ({ page }) => {
    await page.goto('/#pricing');
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Wait for pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    await page.waitForSelector('text="Free"');
    
    // Screenshot each plan card
    const plans = ['Free', 'Hobby', 'Standard', 'Pro'];
    
    for (const planName of plans) {
      const planCard = page.locator(`text="${planName}"`).locator('..').locator('..');
      await expect(planCard).toHaveScreenshot(`plan-card-${planName.toLowerCase()}.png`);
    }
    
    console.log('✅ Individual plan card screenshots captured');
  });

  test('Add-ons Section: Visual Layout', async ({ page }) => {
    await page.goto('/#pricing');
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Scroll to add-ons section
    await page.locator('text="Add-ons & Extras"').scrollIntoViewIfNeeded();
    
    // Wait for add-ons to load
    await page.waitForSelector('text="Extra Message Credits"');
    
    // Screenshot add-ons section
    const addonsSection = page.locator('text="Add-ons & Extras"').locator('..').locator('..');
    await expect(addonsSection).toHaveScreenshot('addons-section.png');
    
    console.log('✅ Add-ons section screenshot captured');
  });

  test('Dashboard: Initial State Visual', async ({ page }) => {
    // This test would need a registered user
    // For now, just test the login page visual
    await page.goto('/login');
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Wait for login page to load
    await page.waitForSelector('input[type="email"], [name="email"]');
    
    // Take screenshot of login page
    await expect(page).toHaveScreenshot('login-page.png');
    
    console.log('✅ Login page screenshot captured');
  });

  test('Responsive Pricing Cards: Mobile Stacking', async ({ page }) => {
    await page.goto('/#pricing');
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Wait for pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    await page.waitForSelector('text="Free"');
    
    // Check that cards stack vertically on mobile
    const pricingGrid = page.locator('#pricing').locator('div').filter({ hasText: 'Free' }).locator('..');
    await expect(pricingGrid).toHaveScreenshot('pricing-mobile-stack.png');
    
    console.log('✅ Mobile responsive pricing layout captured');
  });

  test('Hover States: Plan Cards', async ({ page }) => {
    await page.goto('/#pricing');
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Wait for pricing section
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    await page.waitForSelector('text="Free"');
    
    // Test hover state on Hobby plan (most popular)
    const hobbyCard = page.locator('text="Hobby"').locator('..').locator('..');
    await hobbyCard.hover();
    
    await expect(hobbyCard).toHaveScreenshot('plan-card-hobby-hover.png');
    
    console.log('✅ Hover state screenshot captured');
  });

  test('Dark Mode: Pricing Page', async ({ page, browserName }) => {
    // Skip webkit (Safari) for dark mode testing
    test.skip(browserName === 'webkit', 'Dark mode not supported in webkit tests');
    
    await page.goto('/#pricing');
    
    // Emulate dark mode
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Wait for content
    await page.locator('#pricing').scrollIntoViewIfNeeded();
    await page.waitForSelector('text="Simple, Transparent Pricing"');
    
    // Take screenshot in dark mode
    await expect(page.locator('#pricing')).toHaveScreenshot('pricing-dark-mode.png');
    
    console.log('✅ Dark mode pricing layout captured');
  });

});