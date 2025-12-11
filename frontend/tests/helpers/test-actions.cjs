// Test helper functions for subscription system testing

const { expect } = require('@playwright/test');

/**
 * Register a new user through the frontend
 */
async function registerUser(page, email, password = 'SecurePass123@') {
  console.log(`🔐 Registering user: ${email}`);
  
  await page.goto('/');
  
  // Navigate to registration with fallback selectors
  const registrationSelectors = [
    '[data-testid="get-started"]',
    'a[href="/login"]', 
    'text="Get Started"',
    'text="Sign Up"',
    'text="Register"',
    'button:has-text("Get Started")'
  ];
  
  let clicked = false;
  for (const selector of registrationSelectors) {
    try {
      await page.click(selector);
      clicked = true;
      break;
    } catch (e) {
      continue;
    }
  }
  
  if (!clicked) {
    throw new Error('Could not find registration link');
  }
  
  // Fill registration form with robust selectors
  const fillField = async (fieldSelectors, value) => {
    for (const selector of fieldSelectors) {
      try {
        await page.fill(selector, value);
        break;
      } catch (e) {
        continue;
      }
    }
  };
  
  await fillField(['[data-testid="email"]', 'input[type="email"]', '[name="email"]'], email);
  await fillField(['[data-testid="password"]', 'input[type="password"]', '[name="password"]'], password);
  await fillField(['[data-testid="password_confirm"]', '[name="password_confirm"]', '[name="confirmPassword"]'], password);
  await fillField(['[data-testid="first_name"]', '[name="first_name"]', '[name="firstName"]'], 'Test');
  await fillField(['[data-testid="last_name"]', '[name="last_name"]', '[name="lastName"]'], 'User');
  
  // Submit registration with fallback selectors
  const submitSelectors = [
    '[data-testid="register-button"]',
    'button[type="submit"]',
    'button:has-text("Register")',
    'button:has-text("Sign Up")',
    'button:has-text("Create Account")'
  ];
  
  for (const selector of submitSelectors) {
    try {
      await page.click(selector);
      break;
    } catch (e) {
      continue;
    }
  }
  
  // Wait for successful registration with flexible URL matching
  await page.waitForFunction(() => {
    return window.location.pathname.includes('dashboard') || 
           window.location.pathname.includes('home') ||
           window.location.pathname.includes('app') ||
           document.querySelector('[data-testid="user-dashboard"]') ||
           document.querySelector('.dashboard') ||
           document.title.toLowerCase().includes('dashboard');
  }, { timeout: 15000 });
  
  console.log(`✅ User registered successfully: ${email}`);
  return { email, password };
}

/**
 * Create a new chatbot
 */
async function createChatbot(page, name) {
  console.log(`🤖 Creating chatbot: ${name}`);
  
  // Navigate to dashboard if not already there
  if (!page.url().includes('dashboard')) {
    await page.goto('/dashboard');
  }
  
  // Click new chatbot button
  await page.click('[data-testid="new-chatbot"], button:has-text("New Chatbot"), text="Create Chatbot"');
  
  // Fill chatbot details
  await page.fill('[name="name"], input[placeholder*="name"]', name);
  
  // Save chatbot
  await page.click('button[type="submit"], [data-testid="save-chatbot"], text="Save", text="Create"');
  
  // Wait for success
  await page.waitForResponse('**/api/v1/chatbots/', { timeout: 10000 });
  
  console.log(`✅ Chatbot created: ${name}`);
  return name;
}

/**
 * Attempt to create a chatbot and expect it to be blocked
 */
async function expectChatbotCreationBlocked(page, name) {
  console.log(`🚫 Testing chatbot creation should be blocked: ${name}`);
  
  try {
    await createChatbot(page, name);
    throw new Error('Chatbot creation should have been blocked but succeeded');
  } catch (error) {
    if (error.message.includes('should have been blocked')) {
      throw error;
    }
    // Expected to fail - look for limit error message
    await expect(page.locator('text="upgrade", text="limit", text="maximum"')).toBeVisible({ timeout: 5000 });
    console.log(`✅ Chatbot creation correctly blocked for: ${name}`);
  }
}

/**
 * Send a chat message
 */
async function sendMessage(page, message, chatbotName = null) {
  console.log(`💬 Sending message: "${message}"`);
  
  // If chatbot name provided, navigate to that chatbot
  if (chatbotName) {
    await page.click(`text="${chatbotName}"`);
  }
  
  // Find chat interface
  await page.fill('[data-testid="chat-input"], textarea, input[placeholder*="message"]', message);
  await page.click('[data-testid="send"], button:has-text("Send")');
  
  // Wait for response
  await page.waitForResponse('**/chat/**', { timeout: 15000 });
  
  console.log(`✅ Message sent: "${message}"`);
}

/**
 * Send multiple messages and track credit consumption
 */
async function consumeCredits(page, numberOfMessages, startingCredits) {
  console.log(`🔥 Consuming credits with ${numberOfMessages} messages (starting credits: ${startingCredits})`);
  
  const creditsPerMessage = 2; // Assuming GPT-3.5-turbo = 2 credits
  
  for (let i = 1; i <= numberOfMessages; i++) {
    const expectedCreditsAfter = startingCredits - (i * creditsPerMessage);
    
    if (expectedCreditsAfter < 0) {
      // Should be blocked
      console.log(`🚫 Message ${i} should be blocked (would need ${Math.abs(expectedCreditsAfter)} more credits)`);
      
      try {
        await sendMessage(page, `Test message ${i} - should be blocked`);
        throw new Error(`Message ${i} should have been blocked but succeeded`);
      } catch (error) {
        if (error.message.includes('should have been blocked')) {
          throw error;
        }
        // Expected to fail - check for upgrade suggestion
        await expect(page.locator('text="upgrade", text="credits", text="Hobby"')).toBeVisible({ timeout: 5000 });
        console.log(`✅ Message ${i} correctly blocked - upgrade suggestion shown`);
        break;
      }
    } else {
      // Should succeed
      await sendMessage(page, `Test message ${i}`);
      
      // Check remaining credits if displayed
      const creditsDisplay = page.locator('[data-testid="credits"], text*="credits"');
      if (await creditsDisplay.isVisible()) {
        const creditsText = await creditsDisplay.textContent();
        console.log(`📊 Credits after message ${i}: ${creditsText}`);
      }
    }
  }
  
  console.log(`✅ Credit consumption test completed`);
}

/**
 * Check current plan information
 */
async function checkPlanInfo(page) {
  console.log(`📋 Checking current plan information`);
  
  // Navigate to dashboard or billing section
  if (!page.url().includes('dashboard')) {
    await page.goto('/dashboard');
  }
  
  // Look for plan information
  const planInfo = {
    name: null,
    credits: null,
    agents: null
  };
  
  try {
    const planElement = page.locator('[data-testid="plan"], text*="Plan:", text*="Free", text*="Hobby", text*="Standard", text*="Pro"');
    if (await planElement.isVisible()) {
      planInfo.name = await planElement.textContent();
    }
    
    const creditsElement = page.locator('[data-testid="credits"], text*="credit"');
    if (await creditsElement.isVisible()) {
      planInfo.credits = await creditsElement.textContent();
    }
    
    const agentsElement = page.locator('[data-testid="agents"], text*="agent", text*="chatbot"');
    if (await agentsElement.isVisible()) {
      planInfo.agents = await agentsElement.textContent();
    }
  } catch (error) {
    console.log(`⚠️ Could not find all plan info elements: ${error.message}`);
  }
  
  console.log(`📊 Plan info:`, planInfo);
  return planInfo;
}

/**
 * Simulate plan upgrade (for testing upgrade flow)
 */
async function upgradePlan(page, targetPlan) {
  console.log(`⬆️ Testing upgrade to ${targetPlan} plan`);
  
  // Look for upgrade buttons
  await page.click(`text="Upgrade", text="${targetPlan}", button:has-text("Upgrade")`);
  
  // Should see pricing or checkout interface
  await expect(page.locator(`text="${targetPlan}", text="$"`)).toBeVisible({ timeout: 5000 });
  
  console.log(`✅ Upgrade flow initiated for ${targetPlan} plan`);
}

/**
 * Check for upgrade suggestions when limits are hit
 */
async function checkUpgradeSuggestion(page, expectedPlan = 'Hobby') {
  console.log(`🔍 Checking for upgrade suggestion to ${expectedPlan}`);
  
  // Look for upgrade modal or message
  await expect(page.locator(`text="upgrade", text="${expectedPlan}"`)).toBeVisible({ timeout: 10000 });
  
  console.log(`✅ Upgrade suggestion found for ${expectedPlan} plan`);
}

/**
 * Verify plan limits are enforced
 */
async function verifyPlanLimits(page, expectedLimits) {
  console.log(`🔒 Verifying plan limits:`, expectedLimits);
  
  const planInfo = await checkPlanInfo(page);
  
  // Test chatbot creation limits
  if (expectedLimits.maxChatbots) {
    for (let i = 1; i <= expectedLimits.maxChatbots + 1; i++) {
      if (i <= expectedLimits.maxChatbots) {
        await createChatbot(page, `Test Bot ${i}`);
      } else {
        await expectChatbotCreationBlocked(page, `Test Bot ${i} - Should be blocked`);
      }
    }
  }
  
  // Test credit limits
  if (expectedLimits.credits) {
    const messagesToSend = Math.ceil(expectedLimits.credits / 2) + 5; // Extra messages to test blocking
    await consumeCredits(page, messagesToSend, expectedLimits.credits);
  }
  
  console.log(`✅ Plan limits verified`);
}

module.exports = {
  registerUser,
  createChatbot,
  expectChatbotCreationBlocked,
  sendMessage,
  consumeCredits,
  checkPlanInfo,
  upgradePlan,
  checkUpgradeSuggestion,
  verifyPlanLimits
};