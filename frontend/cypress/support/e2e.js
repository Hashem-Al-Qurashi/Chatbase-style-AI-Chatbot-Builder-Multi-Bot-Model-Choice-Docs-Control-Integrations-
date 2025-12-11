// Cypress support file for E2E testing

import './commands'

// Global configuration
Cypress.on('uncaught:exception', (err, runnable) => {
  // Don't fail tests on uncaught exceptions (React dev mode warnings, etc.)
  return false
})

// Before each test
beforeEach(() => {
  // Clear localStorage and cookies
  cy.clearLocalStorage()
  cy.clearCookies()
})

// Custom logging
Cypress.Commands.overwrite('log', (originalFn, message) => {
  const timestamp = new Date().toLocaleTimeString()
  originalFn(`[${timestamp}] ${message}`)
})