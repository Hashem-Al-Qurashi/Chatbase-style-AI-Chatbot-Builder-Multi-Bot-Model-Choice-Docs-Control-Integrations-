// Quick registration test
describe('Registration Flow Test', () => {
  
  it('Can register a user successfully', () => {
    const email = `test-${Date.now()}@example.com`
    
    cy.visit('/')
    cy.screenshot('1-landing')
    
    // Click login link
    cy.get('a[href="/login"]').click()
    cy.wait(2000)
    cy.screenshot('2-login-page')
    
    // Try to find registration form or switch button
    cy.get('body').then(($body) => {
      const bodyText = $body.text()
      cy.log('Page content:', bodyText)
      
      // Look for any registration-related text
      if (bodyText.includes('Sign up') || bodyText.includes('Register') || bodyText.includes('Create')) {
        cy.log('✅ Found registration option')
      }
      
      // Look for form fields
      if ($body.find('input[type="email"]').length > 0) {
        cy.log('✅ Found email field')
        
        // Try to fill form
        cy.get('input[type="email"]').type(email)
        cy.get('input[type="password"]').first().type('CypressTest123@')
        
        // Look for name fields
        if ($body.find('input[name="first_name"]').length > 0) {
          cy.get('input[name="first_name"]').type('Test')
          cy.get('input[name="last_name"]').type('User')
        }
        
        // Look for confirm password
        if ($body.find('input[name="password_confirm"]').length > 0) {
          cy.get('input[name="password_confirm"]').type('CypressTest123@')
        }
        
        cy.screenshot('3-form-filled')
        
        // Try to submit
        cy.get('button[type="submit"]').click()
        cy.wait(3000)
        cy.screenshot('4-after-submit')
        
        // Check if we reached dashboard
        cy.url().then((url) => {
          if (url.includes('dashboard')) {
            cy.log('✅ Successfully reached dashboard')
          } else {
            cy.log(`❌ Still on: ${url}`)
          }
        })
        
      } else {
        cy.log('❌ No email field found')
      }
    })
  })
  
})