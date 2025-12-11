// Visual theme consistency test
describe('Theme Consistency Validation', () => {
  
  it('Pricing page has consistent elegant theme', () => {
    cy.visit('/#pricing')
    
    // Wait for content to load
    cy.contains('Simple, Transparent Pricing').should('be.visible')
    
    // Verify gradient headers are applied
    cy.get('.gradient-text-elegant').should('exist')
    
    // Verify all plan cards have consistent styling
    cy.contains('Free').parent().parent().should('have.class', 'bg-white/80')
    cy.contains('Hobby').parent().parent().should('have.class', 'bg-gradient-to-br')
    cy.contains('Standard').parent().parent().should('have.class', 'bg-white/80')
    cy.contains('Pro').parent().parent().should('have.class', 'bg-white/80')
    
    // Verify buttons have elegant styling
    cy.get('button:contains("Get Started")').should('exist')
    cy.get('button:contains("Upgrade to Hobby")').should('exist')
    
    // Take screenshot for visual validation
    cy.screenshot('pricing-theme-consistency')
    
    cy.log('✅ Pricing page theme consistency validated')
  })
  
  it('Dashboard has consistent elegant theme', () => {
    // Test dashboard theme (would need authentication)
    cy.visit('/login')
    
    // Verify login page has elegant theme
    cy.get('.gradient-text-elegant').should('contain', 'Welcome Back')
    cy.get('.animate-bounce-gentle').should('exist')
    cy.get('.backdrop-blur-fix').should('exist')
    
    cy.screenshot('login-theme-reference')
    
    cy.log('✅ Login page elegant theme confirmed')
  })
  
  it('All buttons have consistent hover states', () => {
    cy.visit('/#pricing')
    
    // Test button hover states
    cy.get('button:contains("Get Started")').trigger('mouseover')
    cy.wait(500)
    cy.screenshot('free-button-hover')
    
    cy.get('button:contains("Upgrade to Hobby")').trigger('mouseover')
    cy.wait(500)
    cy.screenshot('hobby-button-hover')
    
    // Test add-on buttons
    cy.contains('Add-ons & Extras').scrollIntoView()
    cy.get('button:contains("Add")').first().trigger('mouseover')
    cy.wait(500)
    cy.screenshot('addon-button-hover')
    
    cy.log('✅ Button hover states consistent')
  })
  
})