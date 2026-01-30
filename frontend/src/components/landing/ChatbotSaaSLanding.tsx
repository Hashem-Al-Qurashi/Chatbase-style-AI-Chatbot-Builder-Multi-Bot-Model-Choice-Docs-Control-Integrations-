import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  ArrowRight,
  Bot,
  BarChart3,
  Shield,
  Zap,
  Check,
  Play,
  Code,
  Brain,
  Users,
  Clock,
  Globe,
  Sparkles,
  X,
  Settings,
  Database,
  Crown,
  AlertCircle,
  Menu,
  FileText,
  Rocket
} from 'lucide-react'
import { checkoutService } from '../../services/checkout'
import { LanguageToggle } from '../ui/LanguageToggle'

interface ChatMessage {
  role: 'bot' | 'user'
  text: string
  source?: string
}

const ChatbotSaaSLanding = () => {
  const { t } = useTranslation()
  const [isTyping, setIsTyping] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [demoInput, setDemoInput] = useState('')
  const [isSubmittingDemo, setIsSubmittingDemo] = useState(false)
  const [isSigningUp, setIsSigningUp] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'bot', text: "How can I help you today?" },
    { role: 'user', text: "What are your business hours?" },
    { role: 'bot', text: "We're open Monday-Friday, 9 AM to 6 PM EST. You can also reach us 24/7 through this chat!", source: "Business Hours Policy.pdf" }
  ])

  useEffect(() => {
    checkoutService.checkPendingUpgrade()
  }, [])

  const handleDemoSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!demoInput.trim() || isSubmittingDemo) return

    setIsSubmittingDemo(true)
    const userMessage: ChatMessage = { role: 'user', text: demoInput }
    setChatMessages(prev => [...prev, userMessage])
    setDemoInput('')
    setIsTyping(true)

    setTimeout(() => {
      setIsTyping(false)
      const responses: ChatMessage[] = [
        { role: 'bot', text: "I can help you with that! Let me check our knowledge base.", source: "FAQ.pdf" },
        { role: 'bot', text: "Based on our documentation, here's what I found...", source: "User Guide.pdf" },
        { role: 'bot', text: "Great question! Our system is designed to handle exactly this scenario.", source: "Technical Docs.pdf" }
      ]
      const randomResponse = responses[Math.floor(Math.random() * responses.length)]
      setChatMessages(prev => [...prev, randomResponse])
      setIsSubmittingDemo(false)
    }, 2000)
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-hidden">
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

      {/* Header */}
      <header className="relative z-50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex pt-6 pb-6 items-center justify-between"
          >
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="relative w-12 h-12 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/25">
                <Bot className="w-6 h-6 text-white" />
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-slate-950 flex items-center justify-center">
                  <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                </div>
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Chatava
              </span>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">{t('nav.features')}</a>
              <a href="#demo" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">{t('nav.demo')}</a>
              <a href="#pricing" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">{t('nav.pricing')}</a>
              <LanguageToggle variant="compact" />
              <motion.a
                href="/login"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-sm font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {t('nav.getStarted')}
                <ArrowRight className="w-4 h-4" />
              </motion.a>
            </nav>

            {/* Mobile Menu Button */}
            <motion.button
              className="md:hidden p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              whileTap={{ scale: 0.95 }}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </motion.button>
          </motion.div>

          {/* Mobile Navigation Menu */}
          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="md:hidden absolute top-full left-0 right-0 bg-slate-900/95 backdrop-blur-xl border-b border-white/10 z-50"
              >
                <nav className="px-6 py-6 space-y-4">
                  <a href="#features" className="block text-lg font-medium text-slate-300 hover:text-white transition-colors">{t('nav.features')}</a>
                  <a href="#demo" className="block text-lg font-medium text-slate-300 hover:text-white transition-colors">{t('nav.demo')}</a>
                  <a href="#pricing" className="block text-lg font-medium text-slate-300 hover:text-white transition-colors">{t('nav.pricing')}</a>
                  <div className="pt-4 border-t border-white/10 space-y-4">
                    <LanguageToggle variant="compact" className="w-full justify-center" />
                    <a
                      href="/login"
                      className="block w-full text-center px-5 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium"
                    >
                      {t('nav.getStarted')}
                    </a>
                  </div>
                </nav>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </header>

      <main className="relative z-10">
        {/* Hero Section */}
        <section className="relative px-6 lg:px-8 pt-20 pb-32">
          <div className="max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              {/* Left: Value Proposition */}
              <motion.div
                className="max-w-2xl"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
              >
                {/* Social Proof */}
                <motion.div variants={itemVariants} className="flex items-center gap-4 mb-8">
                  <div className="flex -space-x-3 rtl:space-x-reverse">
                    {['S', 'M', 'A', 'J', 'K'].map((letter, i) => (
                      <div
                        key={i}
                        className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-full flex items-center justify-center text-white text-sm font-semibold ring-2 ring-slate-950"
                      >
                        {letter}
                      </div>
                    ))}
                  </div>
                  <div className="text-sm text-slate-400">
                    {t('landing.hero.badge')}
                  </div>
                </motion.div>

                {/* Main Headline */}
                <motion.h1
                  variants={itemVariants}
                  className="text-4xl lg:text-6xl font-bold leading-tight mb-8"
                >
                  {t('landing.hero.title')}
                </motion.h1>

                <motion.p variants={itemVariants} className="text-xl text-slate-400 leading-relaxed mb-10">
                  {t('landing.hero.subtitle')}
                </motion.p>

                {/* Value Props */}
                <motion.div variants={itemVariants} className="grid sm:grid-cols-3 gap-6 mb-12">
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center group-hover:bg-violet-500/30 transition-colors">
                      <Clock className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{t('landing.features.setup')}</p>
                      <p className="text-sm text-slate-500">{t('landing.features.setupDesc')}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 rounded-xl bg-fuchsia-500/20 flex items-center justify-center group-hover:bg-fuchsia-500/30 transition-colors">
                      <Shield className="w-5 h-5 text-fuchsia-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{t('landing.features.private')}</p>
                      <p className="text-sm text-slate-500">{t('landing.features.privateDesc')}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 group">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center group-hover:bg-cyan-500/30 transition-colors">
                      <Globe className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{t('landing.features.embed')}</p>
                      <p className="text-sm text-slate-500">{t('landing.features.embedDesc')}</p>
                    </div>
                  </div>
                </motion.div>

                {/* CTA Buttons */}
                <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-4">
                  <motion.button
                    onClick={() => {
                      setIsSigningUp(true)
                      setTimeout(() => {
                        window.location.href = '/login'
                      }, 500)
                    }}
                    className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    disabled={isSigningUp}
                  >
                    {isSigningUp ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        {t('landing.hero.cta')}
                      </>
                    )}
                  </motion.button>
                  <motion.button
                    className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 hover:border-white/20 transition-all"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Play className="w-5 h-5" />
                    {t('landing.hero.watchDemo')}
                  </motion.button>
                </motion.div>

                {/* Trust Indicators */}
                <motion.div variants={itemVariants} className="mt-12">
                  <p className="text-sm text-slate-500 mb-4">{t('landing.hero.trustedBy')}</p>
                  <div className="flex items-center gap-8 opacity-40">
                    <div className="text-lg font-bold text-slate-400">OPENAI</div>
                    <div className="text-lg font-bold text-slate-400">STRIPE</div>
                    <div className="text-lg font-bold text-slate-400">VERCEL</div>
                    <div className="text-lg font-bold text-slate-400">PINECONE</div>
                  </div>
                </motion.div>
              </motion.div>

              {/* Right: Live Chatbot Demo */}
              <motion.div
                className="relative"
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
              >
                <div className="relative rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm overflow-hidden shadow-2xl shadow-violet-500/10">
                  {/* Browser UI */}
                  <div className="flex items-center gap-2 px-4 py-3 bg-white/5 border-b border-white/10">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                      <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                      <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                    </div>
                    <div className="flex-1 text-center">
                      <div className="text-xs text-slate-500 bg-white/5 px-3 py-1 rounded-full inline-block">
                        yoursite.com/chat
                      </div>
                    </div>
                  </div>

                  {/* Chat Interface Demo */}
                  <div className="h-96 p-6 flex flex-col">
                    {/* Chat Header */}
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-full flex items-center justify-center">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{t('landing.demo.aiAssistant')}</h3>
                        <p className="text-sm text-emerald-400 flex items-center gap-1">
                          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                          {t('landing.demo.online')}
                        </p>
                      </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 space-y-4 overflow-y-auto max-h-60 scrollbar-thin">
                      {chatMessages.map((message, index) => (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                        >
                          {message.role === 'bot' ? (
                            <div className="flex gap-3">
                              <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-full flex items-center justify-center flex-shrink-0">
                                <Bot className="w-4 h-4 text-white" />
                              </div>
                              <div className="space-y-2">
                                <div className="bg-white/10 rounded-2xl rounded-tl-md px-4 py-3 border border-white/5 max-w-xs">
                                  <p className="text-sm text-slate-200">{message.text}</p>
                                </div>
                                {message.source && (
                                  <div className="text-xs text-slate-500 px-2 flex items-center gap-1">
                                    <FileText className="w-3 h-3" />
                                    {t('landing.demo.source')}: {message.source}
                                  </div>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="flex gap-3 justify-end">
                              <div className="bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-2xl rounded-br-md px-4 py-3 max-w-xs">
                                <p className="text-sm text-white">{message.text}</p>
                              </div>
                              <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center flex-shrink-0">
                                <span className="text-sm font-semibold text-slate-300">U</span>
                              </div>
                            </div>
                          )}
                        </motion.div>
                      ))}

                      {/* Typing Indicator */}
                      {isTyping && (
                        <div className="flex gap-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-full flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-white" />
                          </div>
                          <div className="bg-white/10 rounded-2xl rounded-tl-md px-4 py-3 border border-white/5">
                            <div className="flex items-center gap-1">
                              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                              <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat Input */}
                    <form onSubmit={handleDemoSubmit} className="mt-4 flex gap-2">
                      <input
                        type="text"
                        placeholder={t('landing.demo.askAnything')}
                        value={demoInput}
                        onChange={(e) => setDemoInput(e.target.value)}
                        className="flex-1 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all"
                      />
                      <motion.button
                        type="submit"
                        className="px-4 py-3 bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50"
                        disabled={!demoInput.trim() || isSubmittingDemo}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {isSubmittingDemo ? (
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <ArrowRight className="w-5 h-5 text-white" />
                        )}
                      </motion.button>
                    </form>
                  </div>

                  {/* Floating Feature Badges */}
                  <motion.div
                    className="absolute -top-3 -right-3 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-medium flex items-center gap-1"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Sparkles className="w-3 h-3" />
                    {t('landing.demo.aiPowered')}
                  </motion.div>
                  <motion.div
                    className="absolute -bottom-3 -left-3 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 text-xs font-medium flex items-center gap-1"
                    animate={{ y: [0, 5, 0] }}
                    transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                  >
                    <Rocket className="w-3 h-3" />
                    {t('landing.demo.instantSetup')}
                  </motion.div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <motion.div
              className="text-center mb-20"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-4xl lg:text-5xl font-bold tracking-tight mb-6">
                {t('landing.benefits.title')}
              </h2>
              <p className="text-xl text-slate-400 max-w-3xl mx-auto">
                {t('landing.benefits.subtitle')}
              </p>
            </motion.div>

            <div className="grid lg:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <motion.div
                className="group p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-violet-500/30 transition-all duration-300"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                whileHover={{ y: -4 }}
              >
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Brain className="w-8 h-8 text-violet-400" />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-white">{t('landing.benefits.rag.title')}</h3>
                <p className="text-slate-400 leading-relaxed mb-6">
                  {t('landing.benefits.rag.desc')}
                </p>
              </motion.div>

              {/* Feature 2 */}
              <motion.div
                className="group p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-cyan-500/30 transition-all duration-300"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                whileHover={{ y: -4 }}
              >
                <div className="w-16 h-16 rounded-xl bg-cyan-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Code className="w-8 h-8 text-cyan-400" />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-white">{t('landing.benefits.integration.title')}</h3>
                <p className="text-slate-400 leading-relaxed mb-6">
                  {t('landing.benefits.integration.desc')}
                </p>
                <div className="bg-slate-900/50 rounded-lg p-3 text-xs font-mono text-slate-400 border border-white/5">
                  &lt;script src="chatbot.js"&gt;&lt;/script&gt;
                </div>
              </motion.div>

              {/* Feature 3 */}
              <motion.div
                className="group p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-emerald-500/30 transition-all duration-300"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                whileHover={{ y: -4 }}
              >
                <div className="w-16 h-16 rounded-xl bg-emerald-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <BarChart3 className="w-8 h-8 text-emerald-400" />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-white">{t('landing.benefits.analytics.title')}</h3>
                <p className="text-slate-400 leading-relaxed mb-6">
                  {t('landing.benefits.analytics.desc')}
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-emerald-500 rounded-full" />
                    <span className="text-slate-400">95% {t('landing.benefits.analytics.satisfaction')}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-cyan-500 rounded-full" />
                    <span className="text-slate-400">1.2k {t('landing.benefits.analytics.questions')}</span>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-24 px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <motion.div
              className="text-center mb-16"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-4xl lg:text-5xl font-bold tracking-tight mb-6">
                <span className="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                  {t('landing.pricing.title')}
                </span>
              </h2>
              <p className="text-xl text-slate-400 max-w-3xl mx-auto">
                {t('landing.pricing.subtitle')}
              </p>

              {/* Billing Toggle */}
              <div className="flex items-center justify-center space-x-4 rtl:space-x-reverse mt-8">
                <span className="text-slate-400 font-medium">{t('landing.pricing.monthly')}</span>
                <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-white/10 border border-white/10 transition-all hover:bg-white/15">
                  <span className="inline-block h-4 w-4 transform rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 shadow transition-transform translate-x-1" />
                </button>
                <span className="text-slate-400 font-medium">{t('landing.pricing.yearly')}</span>
                <span className="text-sm bg-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-full font-medium border border-emerald-500/30">
                  {t('landing.pricing.save')}
                </span>
              </div>
            </motion.div>

            <div className="grid lg:grid-cols-4 gap-6 mb-16">
              {/* Free Plan */}
              <motion.div
                className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                whileHover={{ y: -4 }}
              >
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.pricing.free.name')}</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold text-white">{t('landing.pricing.free.price')}</span>
                    <span className="text-slate-500">{t('landing.pricing.free.period')}</span>
                  </div>
                  <p className="text-slate-500 text-sm">{t('landing.pricing.free.desc')}</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center text-slate-300">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-cyan-400" />
                    <span className="font-medium">{t('landing.pricing.metrics.messageCredits', { value: 50 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Settings className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.metrics.aiAgents', { count: 1 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Database className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-violet-400" />
                    <span>{t('landing.pricing.metrics.perAgent', { size: '400KB' })}</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.embedUnlimited')}</span>
                  </li>
                  <li className="flex items-center text-slate-500">
                    <X className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-slate-600" />
                    <span>{t('landing.pricing.featuresList.apiAccess')}</span>
                  </li>
                </ul>

                {/* Warning */}
                <div className="mb-6 text-sm text-amber-400/80 bg-amber-500/10 border border-amber-500/20 p-3 rounded-lg flex items-start">
                  <AlertCircle className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 mt-0.5 flex-shrink-0" />
                  <span>{t('landing.pricing.free.note')}</span>
                </div>

                <motion.button
                  onClick={() => window.location.href = '/login'}
                  className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {t('landing.pricing.getStarted')}
                </motion.button>
              </motion.div>

              {/* Hobby Plan - Most Popular */}
              <motion.div
                className="p-6 rounded-2xl bg-gradient-to-b from-violet-500/10 to-fuchsia-500/5 border-2 border-violet-500/50 relative transform lg:scale-105 shadow-xl shadow-violet-500/10"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
              >
                <motion.div
                  className="absolute -top-4 left-1/2 transform -translate-x-1/2 px-4 py-1.5 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-sm font-medium flex items-center gap-1 shadow-lg"
                  animate={{ y: [0, -3, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Crown className="w-4 h-4" />
                  {t('landing.pricing.hobby.popular')}
                </motion.div>

                <div className="text-center mb-6 mt-2">
                  <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.pricing.hobby.name')}</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold text-white">{t('landing.pricing.hobby.price')}</span>
                    <span className="text-slate-500">{t('landing.pricing.hobby.period')}</span>
                  </div>
                  <p className="text-slate-500 text-sm">{t('landing.pricing.hobby.desc')}</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center text-slate-300">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-cyan-400" />
                    <span className="font-medium">{t('landing.pricing.metrics.messageCredits', { value: '2K' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Settings className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.metrics.aiAgents', { count: 1 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Database className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-violet-400" />
                    <span>{t('landing.pricing.metrics.perAgent', { size: '40MB' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-amber-400" />
                    <span>{t('landing.pricing.metrics.aiActions', { count: 5 })}</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.unlimitedTraining')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.apiAccess')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.basicIntegrations')}</span>
                  </li>
                </ul>

                <motion.button
                  onClick={() => checkoutService.upgradeToHobby()}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {t('landing.pricing.upgrade', { plan: t('landing.pricing.hobby.name') })}
                </motion.button>
              </motion.div>

              {/* Standard Plan */}
              <motion.div
                className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-cyan-500/30 transition-all"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                whileHover={{ y: -4 }}
              >
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.pricing.standard.name')}</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold text-white">{t('landing.pricing.standard.price')}</span>
                    <span className="text-slate-500">{t('landing.pricing.standard.period')}</span>
                  </div>
                  <p className="text-slate-500 text-sm">{t('landing.pricing.standard.desc')}</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center text-slate-300">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-cyan-400" />
                    <span className="font-medium">{t('landing.pricing.metrics.messageCredits', { value: '12K' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Settings className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.metrics.aiAgents_plural', { count: 2 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Database className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-violet-400" />
                    <span>{t('landing.pricing.metrics.perAgent', { size: '33MB' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-amber-400" />
                    <span>{t('landing.pricing.metrics.aiActions', { count: 10 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Users className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-indigo-400" />
                    <span>{t('landing.pricing.metrics.seats', { count: 3 })}</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.multipleAgents')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.teamCollab')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.moreActions')}</span>
                  </li>
                </ul>

                <motion.button
                  onClick={() => checkoutService.upgradeToStandard()}
                  className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {t('landing.pricing.upgrade', { plan: t('landing.pricing.standard.name') })}
                </motion.button>
              </motion.div>

              {/* Pro Plan */}
              <motion.div
                className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-fuchsia-500/30 transition-all"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
                whileHover={{ y: -4 }}
              >
                <div className="text-center mb-6">
                  <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.pricing.pro.name')}</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-4xl font-bold text-white">{t('landing.pricing.pro.price')}</span>
                    <span className="text-slate-500">{t('landing.pricing.pro.period')}</span>
                  </div>
                  <p className="text-slate-500 text-sm">{t('landing.pricing.pro.desc')}</p>
                </div>

                {/* Key Metrics */}
                <div className="space-y-3 mb-6 text-sm">
                  <div className="flex items-center text-slate-300">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-cyan-400" />
                    <span className="font-medium">{t('landing.pricing.metrics.messageCredits', { value: '40K' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Settings className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.metrics.aiAgents_plural', { count: 3 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Database className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-violet-400" />
                    <span>{t('landing.pricing.metrics.perAgent', { size: '33MB' })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Zap className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-amber-400" />
                    <span>{t('landing.pricing.metrics.aiActions', { count: 15 })}</span>
                  </div>
                  <div className="flex items-center text-slate-400">
                    <Users className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-indigo-400" />
                    <span>{t('landing.pricing.metrics.seats', { count: 5 })}</span>
                  </div>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6 text-sm">
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.advancedAnalytics')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.prioritySupport')}</span>
                  </li>
                  <li className="flex items-center text-slate-400">
                    <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2 text-emerald-400" />
                    <span>{t('landing.pricing.featuresList.largerTeams')}</span>
                  </li>
                </ul>

                <motion.button
                  onClick={() => checkoutService.upgradeToPro()}
                  className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium hover:bg-white/10 transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {t('landing.pricing.upgrade', { plan: t('landing.pricing.pro.name') })}
                </motion.button>
              </motion.div>
            </div>

            {/* Add-ons Section */}
            <motion.div
              className="rounded-2xl bg-white/5 border border-white/10 p-8"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold mb-4">
                  <span className="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                    {t('landing.addons.title')}
                  </span>
                </h2>
                <p className="text-slate-400">
                  {t('landing.addons.subtitle')}
                </p>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                  { title: t('landing.addons.credits.title'), desc: t('landing.addons.credits.desc'), price: '$12/month' },
                  { title: t('landing.addons.autoRecharge.title'), desc: t('landing.addons.autoRecharge.desc'), price: '$14/month' },
                  { title: t('landing.addons.agent.title'), desc: t('landing.addons.agent.desc'), price: '$7/month' },
                  { title: t('landing.addons.branding.title'), desc: t('landing.addons.branding.desc'), price: '$39/month' },
                  { title: t('landing.addons.domain.title'), desc: t('landing.addons.domain.desc'), price: '$59/month' }
                ].map((addon, index) => (
                  <motion.div
                    key={index}
                    className="p-6 rounded-xl bg-white/5 border border-white/10 hover:border-violet-500/30 transition-all"
                    whileHover={{ y: -2 }}
                  >
                    <h3 className="font-semibold text-white mb-2">{addon.title}</h3>
                    <p className="text-slate-500 text-sm mb-4">{addon.desc}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-white">{addon.price}</span>
                      <motion.button
                        className="px-4 py-2 rounded-lg bg-violet-500/20 text-violet-400 text-sm font-medium hover:bg-violet-500/30 transition-colors"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {t('landing.addons.add')}
                      </motion.button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Enterprise CTA */}
            <div className="text-center mt-12">
              <p className="text-slate-400">
                {t('landing.enterprise.text')}{' '}
                <a href="#" className="text-violet-400 hover:text-violet-300 font-medium">
                  {t('landing.enterprise.link')}
                </a>
              </p>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 px-6 lg:px-8 relative overflow-hidden">
          {/* Background Gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 via-fuchsia-500/10 to-cyan-500/20" />
          <div className="absolute inset-0 backdrop-blur-3xl" />

          {/* Decorative Elements */}
          <div className="absolute inset-0 overflow-hidden">
            <motion.div
              className="absolute -top-32 -left-32 w-96 h-96 bg-violet-500/20 rounded-full blur-3xl"
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
              transition={{ duration: 5, repeat: Infinity }}
            />
            <motion.div
              className="absolute -bottom-32 -right-32 w-96 h-96 bg-fuchsia-500/20 rounded-full blur-3xl"
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
              transition={{ duration: 5, repeat: Infinity, delay: 1 }}
            />
          </div>

          <motion.div
            className="max-w-4xl mx-auto text-center relative z-10"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl lg:text-5xl font-bold tracking-tight mb-6">
              {t('landing.cta.title')}
            </h2>
            <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto">
              {t('landing.cta.subtitle')}
            </p>

            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <motion.button
                onClick={() => window.location.href = '/login'}
                className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-slate-900 font-medium hover:bg-slate-100 transition-colors shadow-xl"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Sparkles className="w-5 h-5" />
                {t('landing.cta.primary')}
              </motion.button>
              <motion.button
                className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white/10 border border-white/20 text-white font-medium hover:bg-white/20 transition-colors"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Play className="w-5 h-5" />
                {t('landing.cta.secondary')}
              </motion.button>
            </div>

            <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-slate-400 text-sm">
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" />
                {t('landing.cta.noCreditCard')}
              </div>
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" />
                {t('landing.cta.quickSetup')}
              </div>
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" />
                {t('landing.cta.cancelAnytime')}
              </div>
            </div>
          </motion.div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-16 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">Chatava</span>
              </div>
              <p className="text-slate-500 leading-relaxed">
                {t('landing.footer.tagline')}
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('landing.footer.product')}</h4>
              <ul className="space-y-3 text-slate-500">
                <li><a href="#features" className="hover:text-white transition-colors">{t('nav.features')}</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">{t('nav.pricing')}</a></li>
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.apiDocs')}</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('landing.footer.support')}</h4>
              <ul className="space-y-3 text-slate-500">
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.helpCenter')}</a></li>
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.contact')}</a></li>
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.status')}</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-4">{t('landing.footer.company')}</h4>
              <ul className="space-y-3 text-slate-500">
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.about')}</a></li>
                <li><a href="#" className="hover:text-white transition-colors">{t('landing.footer.privacy')}</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-white/10 pt-8 flex flex-col sm:flex-row justify-between items-center">
            <p className="text-slate-500 text-sm">
              {t('landing.footer.copyright')}
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default ChatbotSaaSLanding
