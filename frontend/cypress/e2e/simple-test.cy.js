// Simple test to debug navigation
describe('Debug Registration Navigation', () => {
  
  it('Can navigate to registration form', () => {
    cy.visit('/')
    
    // Take screenshot of landing page
    cy.screenshot('01-landing-page')
    
    // Click login link
    cy.get('a[href="/login"]').click()
    
    // Take screenshot after click
    cy.screenshot('02-after-login-click')
    
    // Wait and see what page we're on
    cy.wait(2000)
    cy.screenshot('03-final-page')
    
    // Check if we can find any form fields
    cy.get('body').then(($body) => {
      if ($body.find('input[type="email"]').length > 0) {
        cy.log('✅ Found email input')
      } else {
        cy.log('❌ No email input found')
      }
      
      if ($body.find('[data-testid="email"]').length > 0) {
        cy.log('✅ Found email testid')
      } else {
        cy.log('❌ No email testid found')
      }
    })
    
    // Try to find registration form elements
    cy.get('input, button, form').then(($elements) => {
      cy.log(`Found ${$elements.length} form elements`)
    })
  })
  
})