import { apiService } from './api'

export interface CheckoutResponse {
  checkout_url: string
  session_id: string
  plan: string
  price: number
  success: boolean
  error?: string
}

export const checkoutService = {
  /**
   * Check if user is logged in
   */
  isLoggedIn(): boolean {
    const token = localStorage.getItem('access_token')
    return !!token
  },

  /**
   * Check for pending upgrade after login and execute it
   */
  async checkPendingUpgrade() {
    const pendingUpgrade = sessionStorage.getItem('pendingUpgrade')
    if (pendingUpgrade && this.isLoggedIn()) {
      // Clear the pending upgrade
      sessionStorage.removeItem('pendingUpgrade')
      sessionStorage.removeItem('returnTo')
      
      console.log(`🔄 Executing pending upgrade: ${pendingUpgrade}`)
      
      // Execute the pending upgrade
      switch (pendingUpgrade) {
        case 'hobby':
          await this.upgradeToHobby()
          break
        case 'standard':
          await this.upgradeToStandard()
          break
        case 'pro':
          await this.upgradeToPro()
          break
      }
    }
  },

  /**
   * Create Stripe checkout session for plan upgrade
   */
  async createCheckoutSession(plan: 'hobby' | 'standard' | 'pro'): Promise<CheckoutResponse> {
    // Check authentication first
    if (!this.isLoggedIn()) {
      return {
        success: false,
        error: 'Please login first to upgrade your plan',
        checkout_url: '',
        session_id: '',
        plan: plan,
        price: 0
      }
    }

    try {
      console.log(`🔄 Creating checkout session for ${plan} plan...`)
      
      const response = await fetch('/api/v1/checkout/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ plan: plan })
      })
      
      if (!response.ok) {
        if (response.status === 401) {
          return {
            success: false,
            error: 'Please login first to upgrade your plan',
            checkout_url: '',
            session_id: '',
            plan: plan,
            price: 0
          }
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      console.log(`✅ Checkout session created:`, data)
      
      // Ensure response has success field
      return {
        ...data,
        success: data.success !== undefined ? data.success : true
      }
      
    } catch (error: any) {
      console.error('❌ Checkout creation failed:', error)
      
      // Try to extract error message from response if available
      let errorMessage = 'Failed to create checkout session'
      if (error.message) {
        errorMessage = error.message
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (typeof error === 'string') {
        errorMessage = error
      }
      
      return {
        success: false,
        error: errorMessage,
        checkout_url: '',
        session_id: '',
        plan: plan,
        price: 0
      }
    }
  },
  
  /**
   * Redirect to Stripe checkout
   */
  async upgradeToHobby() {
    if (!this.isLoggedIn()) {
      const shouldLogin = confirm('Please login first to upgrade your plan. Would you like to go to the login page?')
      if (shouldLogin) {
        // Save the intended action for after login
        sessionStorage.setItem('pendingUpgrade', 'hobby')
        sessionStorage.setItem('returnTo', window.location.href)
        window.location.href = '/login?redirect=' + encodeURIComponent('/#pricing')
      }
      return
    }

    const result = await this.createCheckoutSession('hobby')
    if (result.success) {
      console.log('🔗 Redirecting to Stripe checkout...')
      window.location.href = result.checkout_url
    } else {
      if (result.error?.includes('login')) {
        const shouldLogin = confirm(`${result.error}. Would you like to go to the login page?`)
        if (shouldLogin) {
          window.location.href = '/login'
        }
      } else {
        alert(`Checkout failed: ${result.error}`)
      }
    }
  },
  
  async upgradeToStandard() {
    if (!this.isLoggedIn()) {
      const shouldLogin = confirm('Please login first to upgrade your plan. Would you like to go to the login page?')
      if (shouldLogin) {
        sessionStorage.setItem('pendingUpgrade', 'standard')
        sessionStorage.setItem('returnTo', window.location.href)
        window.location.href = '/login?redirect=' + encodeURIComponent('/#pricing')
      }
      return
    }

    const result = await this.createCheckoutSession('standard')
    if (result.success) {
      console.log('🔗 Redirecting to Stripe checkout...')
      window.location.href = result.checkout_url
    } else {
      if (result.error?.includes('login')) {
        const shouldLogin = confirm(`${result.error}. Would you like to go to the login page?`)
        if (shouldLogin) {
          window.location.href = '/login'
        }
      } else {
        alert(`Checkout failed: ${result.error}`)
      }
    }
  },
  
  async upgradeToPro() {
    if (!this.isLoggedIn()) {
      const shouldLogin = confirm('Please login first to upgrade your plan. Would you like to go to the login page?')
      if (shouldLogin) {
        sessionStorage.setItem('pendingUpgrade', 'pro')
        sessionStorage.setItem('returnTo', window.location.href)
        window.location.href = '/login?redirect=' + encodeURIComponent('/#pricing')
      }
      return
    }

    const result = await this.createCheckoutSession('pro')
    if (result.success) {
      console.log('🔗 Redirecting to Stripe checkout...')
      window.location.href = result.checkout_url
    } else {
      if (result.error?.includes('login')) {
        const shouldLogin = confirm(`${result.error}. Would you like to go to the login page?`)
        if (shouldLogin) {
          window.location.href = '/login'
        }
      } else {
        alert(`Checkout failed: ${result.error}`)
      }
    }
  }
}