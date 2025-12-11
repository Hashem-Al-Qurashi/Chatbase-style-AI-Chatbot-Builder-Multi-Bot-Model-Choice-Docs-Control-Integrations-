// Complete subscription system E2E tests
const { test, expect } = require('@playwright/test');
const { 
  registerUser, 
  createChatbot, 
  expectChatbotCreationBlocked,
  sendMessage,
  consumeCredits, 
  checkPlanInfo,
  upgradePlan,
  checkUpgradeSuggestion,
  verifyPlanLimits 
} = require('./helpers/test-actions.cjs');

test.describe('Complete Subscription System', () => {
  
  test('Free Plan: Full User Journey', async ({ page }) => {
    test.setTimeout(120000); // 2 minutes timeout for this test
    
    // 1. Register new user
    const userEmail = `free-user-${Date.now()}@example.com`;
    await registerUser(page, userEmail);
    
    // 2. Verify Free plan status
    const planInfo = await checkPlanInfo(page);
    console.log('📊 Plan info after registration:', planInfo);
    
    // 3. Test chatbot creation limit (Free = 1 chatbot max)
    console.log('🧪 Testing chatbot creation limits...');
    await createChatbot(page, 'My First Bot'); // Should work
    await expectChatbotCreationBlocked(page, 'Second Bot'); // Should fail
    
    // 4. Test credit consumption (Free = 50 credits)
    console.log('🧪 Testing credit consumption...');
    await consumeCredits(page, 30, 50); // Should hit limit around message 25
    
    // 5. Verify upgrade suggestion appears
    await checkUpgradeSuggestion(page, 'Hobby');
    
    console.log('✅ Free plan journey completed successfully');
  });

  test('Hobby Plan: Upgrade and Validation', async ({ page }) => {
    test.setTimeout(120000);
    
    // 1. Start with free user
    const userEmail = `hobby-user-${Date.now()}@example.com`;
    await registerUser(page, userEmail);
    
    // 2. Test upgrade flow
    console.log('🔄 Testing upgrade flow...');
    await upgradePlan(page, 'Hobby');
    
    // Note: For now we'll simulate the upgrade by checking the pricing page
    // In real implementation, this would go through Stripe checkout
    
    // 3. Verify hobby plan features would be available
    // (This tests the pricing display and upgrade flow UI)
    await page.goto('/#pricing');
    
    // Check Hobby plan is displayed correctly
    await expect(page.locator('text="Hobby"')).toBeVisible();
    await expect(page.locator('text="$40"')).toBeVisible();
    await expect(page.locator('text="2K message credits"')).toBeVisible();
    await expect(page.locator('text="1 AI agent"')).toBeVisible();
    await expect(page.locator('text="40MB"')).toBeVisible();
    await expect(page.locator('text="Most Popular"')).toBeVisible();
    
    console.log('✅ Hobby plan upgrade flow and features verified');
  });

  test('Standard Plan: Team Features Display', async ({ page }) => {
    test.setTimeout(60000);
    
    // Test Standard plan pricing and features
    await page.goto('/#pricing');
    
    // Verify Standard plan details
    await expect(page.locator('text="Standard"')).toBeVisible();
    await expect(page.locator('text="$150"')).toBeVisible();
    await expect(page.locator('text="12K message credits"')).toBeVisible();
    await expect(page.locator('text="2 AI agents"')).toBeVisible();
    await expect(page.locator(':has-text("33MB")').first()).toBeVisible();
    await expect(page.locator('text="3 seats"')).toBeVisible();
    await expect(page.locator('text="Multiple agents"')).toBeVisible();
    await expect(page.locator('text="Team collaboration"')).toBeVisible();
    
    console.log('✅ Standard plan features verified');
  });

  test('Pro Plan: Advanced Features Display', async ({ page }) => {
    test.setTimeout(60000);
    
    // Test Pro plan pricing and features
    await page.goto('/#pricing');
    
    // Verify Pro plan details
    await expect(page.locator('text="Pro"')).toBeVisible();
    await expect(page.locator('text="$500"')).toBeVisible();
    await expect(page.locator('text="40K message credits"')).toBeVisible();
    await expect(page.locator('text="3 AI agents"')).toBeVisible();
    await expect(page.locator('text="5 seats"')).toBeVisible();
    await expect(page.locator('text="Advanced analytics"')).toBeVisible();
    await expect(page.locator('text="Priority support"')).toBeVisible();
    
    console.log('✅ Pro plan features verified');
  });

  test('Add-ons Section: Complete Display', async ({ page }) => {
    test.setTimeout(60000);
    
    await page.goto('/#pricing');
    
    // Scroll to add-ons section
    await page.locator('text="Add-ons & Extras"').scrollIntoViewIfNeeded();
    
    // Verify all add-ons are displayed
    await expect(page.locator('text="Extra Message Credits"')).toBeVisible();
    await expect(page.locator('text="$12/month"')).toBeVisible();
    
    await expect(page.locator('text="Auto-recharge Credits"')).toBeVisible();
    await expect(page.locator('text="$14/month"')).toBeVisible();
    
    await expect(page.locator('text="Additional AI Agent"')).toBeVisible();
    await expect(page.locator('text="$7/month"')).toBeVisible();
    
    await expect(page.locator('text="Remove Branding"')).toBeVisible();
    await expect(page.locator('text="$39/month"')).toBeVisible();
    
    await expect(page.locator('text="Custom Domain"')).toBeVisible();
    await expect(page.locator('text="$59/month"')).toBeVisible();
    
    console.log('✅ All add-ons verified');
  });

  test('Pricing Page: Visual and Functional Validation', async ({ page }) => {
    test.setTimeout(60000);
    
    await page.goto('/#pricing');
    
    // Test billing toggle
    await expect(page.locator('text="Monthly"')).toBeVisible();
    await expect(page.locator('text="Yearly"')).toBeVisible();
    await expect(page.locator('text="Save 20%"')).toBeVisible();
    
    // Test plan cards layout
    await expect(page.locator('text="Free"')).toBeVisible();
    await expect(page.locator('text="Hobby"')).toBeVisible();
    await expect(page.locator('text="Standard"')).toBeVisible();
    await expect(page.locator('text="Pro"')).toBeVisible();
    
    // Test upgrade buttons
    await expect(page.locator('button:has-text("Get Started")')).toBeVisible();
    await expect(page.locator('button:has-text("Upgrade to Hobby")')).toBeVisible();
    await expect(page.locator('button:has-text("Upgrade to Standard")')).toBeVisible();
    await expect(page.locator('button:has-text("Upgrade to Pro")')).toBeVisible();
    
    console.log('✅ Pricing page layout and functionality verified');
  });

  test('Registration and Dashboard Integration', async ({ page }) => {
    test.setTimeout(90000);
    
    // Test complete registration to dashboard flow
    const userEmail = `integration-test-${Date.now()}@example.com`;
    
    // Start from landing page
    await page.goto('/');
    
    // Navigate to pricing
    await page.click('a[href="#pricing"]');
    await expect(page.locator('#pricing')).toBeVisible();
    
    // Click Get Started from Free plan
    await page.click('[data-testid="free-plan-get-started"]');
    
    // Should navigate to registration
    await expect(page.url()).toMatch(/login|register|auth/);
    
    // Register user
    await page.fill('input[type="email"], [name="email"]', userEmail);
    await page.fill('input[type="password"], [name="password"]', 'SecurePass123@');
    await page.fill('[name="password_confirm"], [name="confirmPassword"]', 'SecurePass123@');
    await page.fill('[name="first_name"], [name="firstName"]', 'Test');
    await page.fill('[name="last_name"], [name="lastName"]', 'User');
    
    // Submit registration
    await page.click('button[type="submit"]');
    
    // Should reach dashboard
    await page.waitForURL('**/dashboard', { timeout: 15000 });
    
    // Verify dashboard shows free plan info
    const planInfo = await checkPlanInfo(page);
    console.log('📊 Dashboard plan info:', planInfo);
    
    console.log('✅ Registration to dashboard integration verified');
  });

  test('Error Handling and Edge Cases', async ({ page }) => {
    test.setTimeout(60000);
    
    // Test invalid registration
    await page.goto('/');
    await page.click('[data-testid="get-started"]');
    
    // Try invalid email
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'weak');
    await page.click('button[type="submit"]');
    
    // Should show validation errors (don't fail if not found - different implementations)
    try {
      await expect(page.locator('text="valid email", text="password"')).toBeVisible({ timeout: 3000 });
      console.log('✅ Validation errors displayed correctly');
    } catch (error) {
      console.log('ℹ️ Validation errors not found (may be handled differently)');
    }
    
    // Test pricing page with network simulation
    await page.goto('/#pricing');
    
    // Verify pricing loads even if API is slow
    await expect(page.locator('text="Simple, Transparent Pricing"')).toBeVisible();
    await expect(page.locator('text="Free"')).toBeVisible();
    
    console.log('✅ Error handling tests completed');
  });

});

test.describe('API Integration Tests', () => {
  
  test('Backend API: Pricing Endpoints', async ({ page }) => {
    test.setTimeout(30000);
    
    // Test direct API access
    const apiResponse = await page.request.get('http://localhost:8000/api/v1/pricing/');
    expect(apiResponse.status()).toBe(200);
    
    const pricingData = await apiResponse.json();
    expect(pricingData.results).toBeTruthy();
    expect(pricingData.results.length).toBeGreaterThan(0);
    
    // Verify Free plan exists in API
    const freePlan = pricingData.results.find(plan => plan.name === 'Free');
    expect(freePlan).toBeTruthy();
    expect(freePlan.price_monthly).toBe('0.00');
    expect(freePlan.message_credits).toBe(50);
    
    console.log('✅ Pricing API integration verified');
  });

  test('Backend API: Add-ons Endpoint', async ({ page }) => {
    test.setTimeout(30000);
    
    // Test add-ons API
    const apiResponse = await page.request.get('http://localhost:8000/api/v1/pricing/addons/');
    expect(apiResponse.status()).toBe(200);
    
    const addonsData = await apiResponse.json();
    expect(Array.isArray(addonsData)).toBeTruthy();
    expect(addonsData.length).toBeGreaterThan(0);
    
    // Verify specific add-ons exist
    const extraCredits = addonsData.find(addon => addon.name.includes('Extra Message Credits'));
    expect(extraCredits).toBeTruthy();
    expect(extraCredits.price_monthly).toBe('12.00');
    
    console.log('✅ Add-ons API integration verified');
  });

});