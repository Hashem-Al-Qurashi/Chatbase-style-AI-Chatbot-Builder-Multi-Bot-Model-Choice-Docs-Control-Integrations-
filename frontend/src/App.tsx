import { useState } from 'react'
import { Loader2, Sparkles, Bot, Zap, Shield, Users } from 'lucide-react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { LoginForm } from './components/auth/LoginForm'
import { RegisterForm } from './components/auth/RegisterForm'
import { Dashboard } from './components/dashboard/Dashboard'
import { ButtonTest } from './components/test/ButtonTest'

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="text-center space-y-4 animate-fade-in">
        <div className="w-16 h-16 mx-auto bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/25">
          <Sparkles className="w-8 h-8 text-white animate-pulse" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-gray-800">Loading application...</h2>
          <Loader2 className="w-6 h-6 mx-auto text-primary-600 animate-spin" />
        </div>
      </div>
    </div>
  )
}

function AuthPage() {
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Modern Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-100" />
      
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-gradient-to-br from-primary-400/20 to-accent-400/20 rounded-full blur-3xl animate-float" />
        <div className="absolute -top-20 -right-40 w-96 h-96 bg-gradient-to-br from-accent-400/15 to-primary-400/15 rounded-full blur-3xl animate-float" style={{animationDelay: '2s'}} />
        <div className="absolute -bottom-40 -left-20 w-96 h-96 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-float" style={{animationDelay: '4s'}} />
        <div className="absolute top-1/4 right-1/4 w-32 h-32 bg-gradient-to-br from-accent-300/20 to-primary-300/20 rounded-full blur-2xl animate-pulse-gentle" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen">
        <div className="container mx-auto px-4 py-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center min-h-screen">
            
            {/* Brand Section */}
            <div className="space-y-8 animate-slide-up">
              {/* Logo and Brand */}
              <div className="space-y-6">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                    <Bot className="w-6 h-6 text-white" />
                  </div>
                  <h1 className="text-3xl font-bold gradient-text-elegant">
                    Chatbot SaaS
                  </h1>
                </div>
                
                <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
                  AI-Powered Customer Support{' '}
                  <span className="gradient-text">
                    Platform
                  </span>
                </h2>
                
                <p className="text-xl text-gray-600 leading-relaxed max-w-lg">
                  Transform your customer support with intelligent chatbots that learn, 
                  adapt, and deliver exceptional experiences 24/7.
                </p>
              </div>

              {/* Feature Highlights */}
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors duration-200">
                    <Zap className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Real-time Chat</h3>
                    <p className="text-sm text-gray-600">WebSocket-powered instant messaging</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-accent-100 rounded-lg flex items-center justify-center group-hover:bg-accent-200 transition-colors duration-200">
                    <Shield className="w-5 h-5 text-accent-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Secure & Private</h3>
                    <p className="text-sm text-gray-600">Enterprise-grade security</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-success-100 rounded-lg flex items-center justify-center group-hover:bg-success-200 transition-colors duration-200">
                    <Bot className="w-5 h-5 text-success-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Smart Automation</h3>
                    <p className="text-sm text-gray-600">AI-driven conversation management</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors duration-200">
                    <Users className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Team Collaboration</h3>
                    <p className="text-sm text-gray-600">Live conversation monitoring</p>
                  </div>
                </div>
              </div>

              {/* Social Proof */}
              <div className="flex items-center space-x-8 pt-8">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">10k+</div>
                  <div className="text-sm text-gray-600">Active Users</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">99.9%</div>
                  <div className="text-sm text-gray-600">Uptime</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">24/7</div>
                  <div className="text-sm text-gray-600">Support</div>
                </div>
              </div>
            </div>

            {/* Authentication Section */}
            <div className="flex items-center justify-center animate-slide-up" style={{animationDelay: '0.2s'}}>
              {authMode === 'login' ? (
                <LoginForm 
                  onSuccess={() => {}} 
                  onSwitchToRegister={() => setAuthMode('register')}
                />
              ) : (
                <RegisterForm 
                  onSuccess={() => {}} 
                  onSwitchToLogin={() => setAuthMode('login')}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Decorative Elements */}
      <div className="absolute top-10 right-10 w-2 h-2 bg-primary-400 rounded-full animate-pulse opacity-60" />
      <div className="absolute bottom-20 left-10 w-3 h-3 bg-accent-400 rounded-full animate-bounce-gentle opacity-50" />
      <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-primary-500 rounded-full animate-pulse opacity-40" />
    </div>
  )
}

function AppContent() {
  const { user, loading } = useAuth()

  // Test route for debugging button functionality
  if (window.location.pathname === '/test') {
    return <ButtonTest />
  }

  if (loading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <AuthPage />
  }

  return <Dashboard />
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App