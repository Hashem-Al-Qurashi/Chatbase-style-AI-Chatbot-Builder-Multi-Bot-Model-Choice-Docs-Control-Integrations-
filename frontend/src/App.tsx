import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Loader2, Sparkles, Bot, Zap, Shield, Users } from 'lucide-react'
import { LanguageToggle } from './components/ui/LanguageToggle'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { LoginForm } from './components/auth/LoginForm'
import { RegisterForm } from './components/auth/RegisterForm'
import { Dashboard } from './components/dashboard/Dashboard'
import { ChatInterface } from './components/chat/ChatInterface'
import { ButtonTest } from './components/test/ButtonTest'
import { StandaloneWidget } from './components/widget/StandaloneWidget'
import ChatbotSaaSLanding from './components/landing/ChatbotSaaSLanding'
import SubscriptionUpgradeExact from './components/billing/SubscriptionUpgradeExact'
import { apiService } from './services/api'
import { Chatbot } from './types'

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
  const { t } = useTranslation()
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

      {/* Language Toggle - Top Right */}
      <div className="fixed top-6 right-6 z-50">
        <LanguageToggle />
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
                  <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent">
                    {t('auth.brand.tagline')}
                  </span>
                </h2>

                <p className="text-xl text-slate-400 leading-relaxed max-w-lg">
                  {t('auth.brand.description')}
                </p>
              </div>

              {/* Feature Highlights */}
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="flex items-start space-x-3 rtl:space-x-reverse group">
                  <div className="w-10 h-10 bg-violet-500/20 rounded-xl flex items-center justify-center group-hover:bg-violet-500/30 transition-colors duration-200">
                    <Zap className="w-5 h-5 text-violet-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{t('auth.brand.realtime')}</h3>
                    <p className="text-sm text-slate-500">{t('auth.brand.realtimeDesc')}</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 rtl:space-x-reverse group">
                  <div className="w-10 h-10 bg-fuchsia-500/20 rounded-xl flex items-center justify-center group-hover:bg-fuchsia-500/30 transition-colors duration-200">
                    <Shield className="w-5 h-5 text-fuchsia-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{t('auth.brand.secure')}</h3>
                    <p className="text-sm text-slate-500">{t('auth.brand.secureDesc')}</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 rtl:space-x-reverse group">
                  <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center group-hover:bg-emerald-500/30 transition-colors duration-200">
                    <Bot className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{t('auth.brand.automation')}</h3>
                    <p className="text-sm text-slate-500">{t('auth.brand.automationDesc')}</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 rtl:space-x-reverse group">
                  <div className="w-10 h-10 bg-cyan-500/20 rounded-xl flex items-center justify-center group-hover:bg-cyan-500/30 transition-colors duration-200">
                    <Users className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{t('auth.brand.collaboration')}</h3>
                    <p className="text-sm text-slate-500">{t('auth.brand.collaborationDesc')}</p>
                  </div>
                </div>
              </div>

              {/* Social Proof */}
              <div className="flex items-center space-x-8 rtl:space-x-reverse pt-8">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">10k+</div>
                  <div className="text-sm text-slate-500">{t('auth.brand.activeUsers')}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">99.9%</div>
                  <div className="text-sm text-slate-500">{t('auth.brand.uptime')}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">24/7</div>
                  <div className="text-sm text-slate-500">{t('auth.brand.support')}</div>
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
  const [chatbot, setChatbot] = useState<Chatbot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (chatbotId) {
      loadChatbot(chatbotId)
    }
  }, [chatbotId])

  const loadChatbot = async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiService.getChatbot(id)
      setChatbot(data)
    } catch (err: any) {
      console.error('Failed to load chatbot:', err)
      setError(err.message || 'Failed to load chatbot')
    } finally {
      setLoading(false)
    }
  }

  if (!chatbotId) {
    return <Navigate to="/dashboard" replace />
  }

  if (loading) {
    return (
      <div className="h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 text-violet-500 animate-spin mx-auto" />
          <p className="text-slate-400">Loading chatbot...</p>
        </div>
      </div>
    )
  }

  if (error || !chatbot) {
    return (
      <div className="h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Bot className="w-12 h-12 text-rose-500 mx-auto" />
          <h2 className="text-xl font-semibold text-white">Chatbot Not Found</h2>
          <p className="text-slate-400">{error || 'The chatbot could not be loaded.'}</p>
          <button
            onClick={() => window.history.back()}
            className="px-4 py-2 bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen">
      <ChatInterface
        chatbot={chatbot}
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