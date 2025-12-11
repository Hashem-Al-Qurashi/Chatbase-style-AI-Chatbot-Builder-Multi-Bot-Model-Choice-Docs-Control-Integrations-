const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3005',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    
    // Test file patterns
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    
    env: {
      backendUrl: 'http://localhost:8000',
      // Test user credentials
      testEmail: 'cypress-test@example.com',
      testPassword: 'CypressTest123@'
    }
  },
  
  component: {
    devServer: {
      framework: 'vite',
      bundler: 'vite',
    },
  },
})