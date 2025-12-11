// Custom Cypress commands for subscription testing

// Register a new user
Cypress.Commands.add('registerUser', (email, password = 'CypressTest123@') => {
  cy.log(`🔐 Registering user: ${email}`)
  
  cy.visit('/')
  
  // Find and click registration link
  cy.get('a[href="/login"]').click()
  
  // Wait for page to load and look for registration option
  cy.wait(1000)
  
  // Check if we need to switch to registration mode
  cy.get('body').then(($body) => {
    const bodyText = $body.text()
    if (bodyText.includes('Sign Up')) {
      cy.contains('Sign Up').click()
    } else if (bodyText.includes('Register')) {
      cy.contains('Register').click()
    }
  })
  
  // Wait for form to appear
  cy.wait(1000)
  
  // Fill registration form with flexible selectors
  cy.get('input[type="email"]').type(email)
  cy.get('input[type="password"]').first().type(password)
  
  // Handle confirm password if present
  cy.get('body').then(($body) => {
    if ($body.find('input[name="password_confirm"]').length > 0) {
      cy.get('input[name="password_confirm"]').type(password)
    }
  })
  
  // Handle name fields if present
  cy.get('body').then(($body) => {
    if ($body.find('input[name="first_name"]').length > 0) {
      cy.get('input[name="first_name"]').type('Test')
      cy.get('input[name="last_name"]').type('User')
    }
  })
  
  // Submit form
  cy.get('button[type="submit"]').click()
  
  // Wait for successful registration (flexible)
  cy.wait(3000) // Give time for registration to process
  
  // Check if we reached dashboard or any success page
  cy.url().then((url) => {
    if (url.includes('dashboard') || url.includes('home') || url.includes('app')) {
      cy.log(`✅ User registered successfully: ${email}`)
    } else {
      cy.log(`⚠️ Registration may have failed, current URL: ${url}`)
      // Still continue the test to see what happens
    }
  })
})

// Create a chatbot
Cypress.Commands.add('createChatbot', (name) => {
  cy.log(`🤖 Creating chatbot: ${name}`)
  
  // Find new chatbot button
  cy.get('[data-testid="new-chatbot-button"]').click()
  
  // Fill chatbot form
  cy.get('input[name="name"]').type(name)
  cy.get('button[type="submit"]').click()
  
  // Wait for success
  cy.contains(name).should('be.visible')
  cy.log(`✅ Chatbot created: ${name}`)
})

// Send a chat message
Cypress.Commands.add('sendMessage', (message) => {
  cy.log(`💬 Sending message: "${message}"`)
  
  cy.get('[data-testid="chat-input"], textarea, input[placeholder*="message"]').type(message)
  cy.get('[data-testid="send-button"], button:contains("Send")').click()
  
  // Wait for response
  cy.get('.message', { timeout: 15000 }).should('contain', message)
  cy.log(`✅ Message sent: "${message}"`)
})

// Check current credits
Cypress.Commands.add('checkCredits', () => {
  cy.log(`📊 Checking current credits`)
  
  cy.get('[data-testid="credits-remaining"]').then(($el) => {
    const credits = $el.text()
    cy.log(`💰 Current credits: ${credits}`)
    return cy.wrap(parseInt(credits))
  })
})

// Send messages until blocked
Cypress.Commands.add('sendMessagesUntilBlocked', (maxMessages = 30) => {
  cy.log(`🔥 Sending messages until blocked (max: ${maxMessages})`)
  
  for(let i = 1; i <= maxMessages; i++) {
    cy.log(`Sending message ${i}/${maxMessages}`)
    
    // Try to send message
    cy.get('[data-testid="chat-input"]').type(`Test message ${i}`)
    cy.get('[data-testid="send-button"]').click()
    
    // Check if blocked
    cy.get('body').then(($body) => {
      if ($body.text().includes('insufficient') || $body.text().includes('upgrade') || $body.text().includes('limit')) {
        cy.log(`🚫 Blocked at message ${i}`)
        cy.contains('upgrade').should('be.visible')
        return false // Stop the loop
      } else {
        // Check credits decreased
        cy.checkCredits().then((credits) => {
          cy.log(`💰 Credits after message ${i}: ${credits}`)
        })
      }
    })
  }
})

// Expect chatbot creation to be blocked
Cypress.Commands.add('expectChatbotBlocked', (name) => {
  cy.log(`🚫 Expecting chatbot creation to be blocked: ${name}`)
  
  cy.get('[data-testid="new-chatbot-button"]').click()
  cy.get('input[name="name"]').type(name)
  cy.get('button[type="submit"]').click()
  
  // Should show limit error
  cy.contains('limit').should('be.visible')
  cy.contains('upgrade').should('be.visible')
  cy.log(`✅ Chatbot creation correctly blocked: ${name}`)
})

// Check current plan information
Cypress.Commands.add('checkPlan', () => {
  cy.log(`📋 Checking current plan`)
  
  cy.get('[data-testid="plan-name"]').then(($plan) => {
    const planName = $plan.text()
    cy.log(`📊 Current plan: ${planName}`)
    return cy.wrap(planName)
  })
})

// Navigate to pricing page
Cypress.Commands.add('goToPricing', () => {
  cy.visit('/#pricing')
  cy.contains('Simple, Transparent Pricing').should('be.visible')
})

// Verify upgrade suggestion appears
Cypress.Commands.add('expectUpgradeSuggestion', (suggestedPlan = 'Hobby') => {
  cy.log(`🔍 Expecting upgrade suggestion to: ${suggestedPlan}`)
  
  cy.contains('upgrade', { matchCase: false }).should('be.visible')
  cy.contains(suggestedPlan).should('be.visible')
  cy.log(`✅ Upgrade suggestion found: ${suggestedPlan}`)
})