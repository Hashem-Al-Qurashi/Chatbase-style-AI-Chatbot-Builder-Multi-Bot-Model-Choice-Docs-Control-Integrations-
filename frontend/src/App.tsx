import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { Loader2, Sparkles, Bot, Zap, Shield, Users } from 'lucide-react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { LoginForm } from './components/auth/LoginForm'
import { RegisterForm } from './components/auth/RegisterForm'
import { Dashboard } from './components/dashboard/Dashboard'
import { ChatInterface } from './components/chat/ChatInterface'
import { ButtonTest } from './components/test/ButtonTest'
import { StandaloneWidget } from './components/widget/StandaloneWidget'
import ChatbotSaaSLanding from './components/landing/ChatbotSaaSLanding'
import SubscriptionUpgradeExact from './components/billing/SubscriptionUpgradeExact'

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
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Ambient Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-violet-500/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-fuchsia-500/15 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/5 rounded-full blur-[150px]" />
      </div>

      {/* Grid Pattern Overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }}
      />

      {/* Content */}
      <div className="relative z-10 min-h-screen">
        <div className="container mx-auto px-4 py-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center min-h-screen">

            {/* Brand Section */}
            <div className="space-y-8 animate-slide-up">
              {/* Logo and Brand */}
              <div className="space-y-6">
                <div className="flex items-center space-x-3">
                  <div className="relative w-12 h-12 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/25">
                    <Bot className="w-6 h-6 text-white" />
                    <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-slate-950 flex items-center justify-center">
                      <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                    </div>
                  </div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                    Chatava
                  </h1>
                </div>

                <h2 className="text-4xl lg:text-5xl font-bold text-white leading-tight">
                  AI-Powered Customer Support{' '}
                  <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent">
                    Platform
                  </span>
                </h2>

                <p className="text-xl text-slate-400 leading-relaxed max-w-lg">
                  Transform your customer support with intelligent chatbots that learn,
                  adapt, and deliver exceptional experiences 24/7.
                </p>
              </div>

              {/* Feature Highlights */}
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-violet-500/20 rounded-xl flex items-center justify-center group-hover:bg-violet-500/30 transition-colors duration-200">
                    <Zap className="w-5 h-5 text-violet-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Real-time Chat</h3>
                    <p className="text-sm text-slate-500">WebSocket-powered instant messaging</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-fuchsia-500/20 rounded-xl flex items-center justify-center group-hover:bg-fuchsia-500/30 transition-colors duration-200">
                    <Shield className="w-5 h-5 text-fuchsia-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Secure & Private</h3>
                    <p className="text-sm text-slate-500">Enterprise-grade security</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center group-hover:bg-emerald-500/30 transition-colors duration-200">
                    <Bot className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Smart Automation</h3>
                    <p className="text-sm text-slate-500">AI-driven conversation management</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 group">
                  <div className="w-10 h-10 bg-cyan-500/20 rounded-xl flex items-center justify-center group-hover:bg-cyan-500/30 transition-colors duration-200">
                    <Users className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Team Collaboration</h3>
                    <p className="text-sm text-slate-500">Live conversation monitoring</p>
                  </div>
                </div>
              </div>

              {/* Social Proof */}
              <div className="flex items-center space-x-8 pt-8">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">10k+</div>
                  <div className="text-sm text-slate-500">Active Users</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">99.9%</div>
                  <div className="text-sm text-slate-500">Uptime</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">24/7</div>
                  <div className="text-sm text-slate-500">Support</div>
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
      <div className="absolute top-10 right-10 w-2 h-2 bg-violet-400 rounded-full animate-pulse opacity-60" />
      <div className="absolute bottom-20 left-10 w-3 h-3 bg-fuchsia-400 rounded-full animate-bounce-gentle opacity-50" />
      <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-cyan-500 rounded-full animate-pulse opacity-40" />
    </div>
  )
}

// Chat page component with chatbot ID from URL
function ChatPage() {
  const { chatbotId } = useParams<{ chatbotId: string }>()
  
  if (!chatbotId) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="h-screen">
      <ChatInterface 
        chatbot={{ id: chatbotId, name: `Chatbot ${chatbotId}` }}
        onClose={() => window.history.back()}
      />
    </div>
  )
}

function AppContent() {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingScreen />
  }

  return (
    <Routes>
      <Route path="/" element={!user ? <ChatbotSaaSLanding /> : <Navigate to="/dashboard" replace />} />
      <Route path="/login" element={!user ? <AuthPage /> : <Navigate to="/dashboard" replace />} />
      <Route path="/register" element={!user ? <AuthPage /> : <Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={user ? <Dashboard /> : <Navigate to="/login" replace />} />
      <Route path="/chat/:chatbotId" element={user ? <ChatPage /> : <Navigate to="/login" replace />} />
      <Route path="/subscription" element={<SubscriptionUpgradeExact />} />
      <Route path="/test" element={<ButtonTest />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Public Widget Route - No Authentication Required */}
        <Route path="/widget/:slug" element={<StandaloneWidget />} />
        
        {/* Authenticated Routes */}
        <Route path="/*" element={
          <AuthProvider>
            <AppContent />
          </AuthProvider>
        } />
      </Routes>
    </Router>
  )
}

export default App