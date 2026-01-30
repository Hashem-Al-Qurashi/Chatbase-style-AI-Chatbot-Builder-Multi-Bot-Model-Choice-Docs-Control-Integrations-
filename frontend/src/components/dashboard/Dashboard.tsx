import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bot,
  MessageSquare,
  Zap,
  CreditCard,
  Plus,
  Search,
  Grid3X3,
  List,
  RefreshCw,
  Sparkles
} from 'lucide-react'
import { DashboardLayout } from './DashboardLayout'
import { StatCard, StatCardSkeleton } from './StatCard'
import { ActivityFeed } from './ActivityFeed'
import { QuickActions, FeaturedAction } from './QuickActions'
import { ChatbotCard, ChatbotCardSkeleton, ChatbotsEmptyState } from './ChatbotCard'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'
import { ChatbotWizard } from '../chatbot/ChatbotWizard'
import { ChatbotDetailsModal } from '../chatbot/ChatbotDetailsModal'

export function Dashboard() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()

  // State
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [userPlan, setUserPlan] = useState<any>(null)
  const [planLoading, setPlanLoading] = useState(true)

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedChatbot, setSelectedChatbot] = useState<Chatbot | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)

  // Load data
  useEffect(() => {
    loadChatbots()
    loadUserPlan()
  }, [])

  const loadChatbots = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiService.getChatbots()
      const chatbotsData = Array.isArray(response) ? response : (response as any).results || []
      setChatbots(chatbotsData)
    } catch (err: any) {
      console.error('Failed to load chatbots:', err)
      setError(err.message || 'Failed to load chatbots')
      setChatbots([])
    } finally {
      setLoading(false)
    }
  }

  const loadUserPlan = async () => {
    try {
      setPlanLoading(true)
      const response = await apiService.get<any>('/billing/current_plan/')
      setUserPlan(response.plan || response.data?.plan || {
        tier: 'free',
        message_credits: 50,
        credits_used: 0,
        credits_remaining: 50,
        max_ai_agents: 1
      })
    } catch (error) {
      console.error('Failed to load user plan:', error)
      setUserPlan({
        tier: 'free',
        message_credits: 50,
        credits_used: 0,
        credits_remaining: 50,
        max_ai_agents: 1
      })
    } finally {
      setPlanLoading(false)
    }
  }

  // Handlers
  const handleChatbotClick = (chatbot: Chatbot) => {
    navigate(`/chat/${chatbot.id}`)
  }

  const handleChatbotSettings = (chatbot: Chatbot) => {
    setSelectedChatbot(chatbot)
    setShowDetailsModal(true)
  }

  const handleCreateSuccess = () => {
    setShowCreateModal(false)
    loadChatbots()
  }

  const handleCloseDetailsModal = () => {
    setShowDetailsModal(false)
    setSelectedChatbot(null)
  }

  // Filter chatbots
  const filteredChatbots = chatbots.filter(bot =>
    searchQuery
      ? bot.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        bot.description.toLowerCase().includes(searchQuery.toLowerCase())
      : true
  )

  // Calculate stats
  const totalConversations = chatbots.reduce((acc, bot) => acc + (bot.total_conversations || 0), 0)
  const totalMessages = chatbots.reduce((acc, bot) => acc + (bot.total_messages || 0), 0)
  const creditsRemaining = userPlan?.credits_remaining || 50
  const creditsTotal = userPlan?.message_credits || 50

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return t('dashboard.greeting.morning')
    if (hour < 18) return t('dashboard.greeting.afternoon')
    return t('dashboard.greeting.evening')
  }

  return (
    <DashboardLayout activeSection="dashboard">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">
              {getGreeting()}, {user?.first_name || user?.email?.split('@')[0] || 'there'}
            </h1>
            <p className="text-slate-500">
              {t('dashboard.subtitle')}
            </p>
          </div>

          <motion.button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Plus className="w-5 h-5" />
            {t('dashboard.newChatbot')}
          </motion.button>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {loading || planLoading ? (
            <>
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
            </>
          ) : (
            <>
              <StatCard
                title={t('dashboard.stats.totalChatbots')}
                value={chatbots.length}
                icon={Bot}
                color="violet"
                trend={{ value: 12, isPositive: true }}
                delay={0}
                description={t('dashboard.stats.maxAllowed', { count: userPlan?.max_ai_agents || 1 })}
              />
              <StatCard
                title={t('dashboard.stats.totalConversations')}
                value={totalConversations}
                icon={MessageSquare}
                color="fuchsia"
                trend={{ value: 8, isPositive: true }}
                delay={0.1}
              />
              <StatCard
                title={t('dashboard.stats.messagesThisMonth')}
                value={totalMessages}
                icon={Zap}
                color="cyan"
                trend={{ value: 23, isPositive: true }}
                delay={0.2}
              />
              <StatCard
                title={t('dashboard.stats.creditsRemaining')}
                value={creditsRemaining}
                suffix={` / ${creditsTotal}`}
                icon={CreditCard}
                color={creditsRemaining < 10 ? 'rose' : 'emerald'}
                delay={0.3}
                description={creditsRemaining < 10 ? t('dashboard.stats.runningLow') : t('dashboard.stats.thisBillingCycle')}
              />
            </>
          )}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Chatbots */}
          <div className="lg:col-span-2 space-y-6">
            {/* Chatbots Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">{t('dashboard.yourChatbots')}</h2>
                <p className="text-sm text-slate-500">
                  {t('dashboard.chatbotsCount', { filtered: filteredChatbots.length, total: chatbots.length })}
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    placeholder={t('dashboard.searchChatbots')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-48 pl-9 rtl:pl-4 rtl:pr-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all"
                  />
                </div>

                {/* View Toggle */}
                <div className="flex items-center bg-white/5 rounded-lg p-1 border border-white/10">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-white'} transition-colors`}
                  >
                    <Grid3X3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-white'} transition-colors`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>

                {/* Refresh */}
                <motion.button
                  onClick={loadChatbots}
                  className="p-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                  whileTap={{ rotate: 180 }}
                >
                  <RefreshCw className="w-4 h-4" />
                </motion.button>
              </div>
            </div>

            {/* Chatbots Grid/List */}
            {loading ? (
              <div className={`grid ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'} gap-4`}>
                <ChatbotCardSkeleton />
                <ChatbotCardSkeleton />
                <ChatbotCardSkeleton />
              </div>
            ) : error ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl bg-rose-500/10 border border-rose-500/20 p-8 text-center"
              >
                <p className="text-rose-400 mb-4">{error}</p>
                <button
                  onClick={loadChatbots}
                  className="px-4 py-2 rounded-lg bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 transition-colors"
                >
                  {t('dashboard.tryAgain')}
                </button>
              </motion.div>
            ) : filteredChatbots.length === 0 && chatbots.length === 0 ? (
              <ChatbotsEmptyState onCreateChatbot={() => setShowCreateModal(true)} />
            ) : filteredChatbots.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl bg-white/5 border border-white/10 p-8 text-center"
              >
                <Search className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                <h3 className="text-white font-medium mb-1">{t('dashboard.noResults')}</h3>
                <p className="text-slate-500 text-sm">
                  {t('dashboard.tryAdjusting')}
                </p>
              </motion.div>
            ) : (
              <motion.div
                layout
                className={`grid ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'} gap-4`}
              >
                <AnimatePresence mode="popLayout">
                  {filteredChatbots.map((chatbot, index) => (
                    <ChatbotCard
                      key={chatbot.id}
                      chatbot={chatbot}
                      index={index}
                      onChat={() => handleChatbotClick(chatbot)}
                      onSettings={() => handleChatbotSettings(chatbot)}
                      onEmbed={() => handleChatbotSettings(chatbot)}
                    />
                  ))}
                </AnimatePresence>
              </motion.div>
            )}
          </div>

          {/* Right Column - Quick Actions & Activity */}
          <div className="space-y-6">
            <QuickActions
              onCreateChatbot={() => setShowCreateModal(true)}
            />

            <ActivityFeed maxItems={4} />

            {/* Upgrade Banner (for free users) */}
            {userPlan?.tier === 'free' && (
              <FeaturedAction
                title={t('dashboard.upgrade.title')}
                description={t('dashboard.upgrade.description')}
                icon={Sparkles}
                buttonText={t('dashboard.upgrade.viewPlans')}
                onClick={() => navigate('/#pricing')}
                gradient="from-amber-500 to-orange-500"
              />
            )}
          </div>
        </div>
      </div>

      {/* Create Chatbot Modal */}
      <ChatbotWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />

      {/* Chatbot Details Modal */}
      <ChatbotDetailsModal
        isOpen={showDetailsModal}
        onClose={handleCloseDetailsModal}
        chatbot={selectedChatbot}
        onChatbotUpdated={loadChatbots}
      />
    </DashboardLayout>
  )
}
