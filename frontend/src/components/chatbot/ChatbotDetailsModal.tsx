import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  X,
  Bot,
  MessageSquare,
  Settings,
  Upload,
  Eye,
  Code,
  BarChart3,
  Calendar,
  Users,
  Clock,
  Zap,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Globe
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { KnowledgeSourceManager } from './KnowledgeSourceManager'
import { ChatbotWizard } from './ChatbotWizard'
import { EmbedCodeModal } from './EmbedCodeModal'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface ChatbotDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  chatbot: Chatbot | null
  onChatbotUpdated: () => void
}

type TabType = 'overview' | 'knowledge' | 'settings' | 'analytics' | 'embed' | 'integrations'

export function ChatbotDetailsModal({
  isOpen,
  onClose,
  chatbot,
  onChatbotUpdated
}: ChatbotDetailsModalProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [loading, setLoading] = useState(false)
  const [showEditWizard, setShowEditWizard] = useState(false)
  const [showEmbedModal, setShowEmbedModal] = useState(false)

  // Reset tab when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setActiveTab('overview')
    }
  }, [isOpen])

  if (!chatbot) return null

  const tabs = [
    { id: 'overview' as TabType, labelKey: 'chatbot.overview', icon: Bot, color: 'text-violet-400' },
    { id: 'knowledge' as TabType, labelKey: 'chatbot.knowledge', icon: Upload, color: 'text-emerald-400' },
    { id: 'settings' as TabType, labelKey: 'sidebar.settings', icon: Settings, color: 'text-slate-400' },
    { id: 'analytics' as TabType, labelKey: 'chatbot.analytics', icon: BarChart3, color: 'text-cyan-400' },
    { id: 'embed' as TabType, labelKey: 'chatbot.embed', icon: Code, color: 'text-amber-400' },
    { id: 'integrations' as TabType, labelKey: 'chatbot.integrations', icon: Zap, color: 'text-fuchsia-400' }
  ]

  const handleEditChatbot = () => {
    setShowEditWizard(true)
  }

  const handleWizardSuccess = () => {
    setShowEditWizard(false)
    onChatbotUpdated()
  }

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, string> = {
      active: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      training: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      error: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
      draft: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      ready: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${statusStyles[status] || statusStyles.draft}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${status === 'active' || status === 'completed' || status === 'ready' ? 'bg-emerald-400' : status === 'training' ? 'bg-amber-400 animate-pulse' : status === 'error' ? 'bg-rose-400' : 'bg-slate-400'}`} />
        {status}
      </span>
    )
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Chatbot Info Card */}
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10 backdrop-blur-sm">
              <div className="flex items-start gap-4">
                <motion.div
                  whileHover={{ scale: 1.05, rotate: 5 }}
                  className="w-14 h-14 bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 rounded-2xl flex items-center justify-center shadow-xl shadow-violet-500/25 flex-shrink-0"
                >
                  <Bot className="w-7 h-7 text-white" />
                </motion.div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xl font-semibold text-white truncate">{chatbot.name}</h3>
                  <p className="text-slate-400 text-sm mt-1 line-clamp-2">{chatbot.description || t('chatbot.noDescription')}</p>
                  <div className="flex flex-wrap items-center gap-3 mt-3">
                    {getStatusBadge(chatbot.status)}
                    <span className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Calendar className="w-3.5 h-3.5" />
                      Created {formatDate(chatbot.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-3">
              <motion.div
                whileHover={{ scale: 1.02, y: -2 }}
                className="p-4 bg-white/[0.04] rounded-xl border border-white/10 text-center group hover:bg-white/[0.06] transition-colors"
              >
                <div className="w-10 h-10 bg-violet-500/20 rounded-xl flex items-center justify-center mx-auto mb-2 group-hover:bg-violet-500/30 transition-colors">
                  <MessageSquare className="w-5 h-5 text-violet-400" />
                </div>
                <p className="text-2xl font-bold text-white">{chatbot.total_conversations || 0}</p>
                <p className="text-xs text-slate-500 mt-1">{t('chatbot.stats.conversations')}</p>
              </motion.div>

              <motion.div
                whileHover={{ scale: 1.02, y: -2 }}
                className="p-4 bg-white/[0.04] rounded-xl border border-white/10 text-center group hover:bg-white/[0.06] transition-colors"
              >
                <div className="w-10 h-10 bg-cyan-500/20 rounded-xl flex items-center justify-center mx-auto mb-2 group-hover:bg-cyan-500/30 transition-colors">
                  <Users className="w-5 h-5 text-cyan-400" />
                </div>
                <p className="text-2xl font-bold text-white">{chatbot.total_messages || 0}</p>
                <p className="text-xs text-slate-500 mt-1">{t('chatbot.stats.messages')}</p>
              </motion.div>

              <motion.div
                whileHover={{ scale: 1.02, y: -2 }}
                className="p-4 bg-white/[0.04] rounded-xl border border-white/10 text-center group hover:bg-white/[0.06] transition-colors"
              >
                <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center mx-auto mb-2 group-hover:bg-emerald-500/30 transition-colors">
                  <Upload className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="flex items-center justify-center">
                  {chatbot.has_knowledge_sources ? (
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  ) : (
                    <span className="text-2xl font-bold text-white">0</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1">{t('chatbot.stats.knowledge')}</p>
              </motion.div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => window.open(`/chat/${chatbot.id}`, '_blank')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-violet-600 text-white font-medium rounded-xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-shadow"
              >
                <MessageSquare className="w-4 h-4" />
                {t('chatbot.testChat')}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab('knowledge')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white/[0.06] border border-white/10 text-slate-300 font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
              >
                <Upload className="w-4 h-4" />
                {t('chatbot.knowledge')}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab('embed')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white/[0.06] border border-white/10 text-slate-300 font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
              >
                <Code className="w-4 h-4" />
                {t('chatbot.embed')}
              </motion.button>
            </div>
          </motion.div>
        )

      case 'knowledge':
        return (
          <KnowledgeSourceManager 
            chatbot={chatbot} 
            onUploadRequested={() => setShowEditWizard(true)}
          />
        )

      case 'settings':
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Configuration Card */}
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-slate-500/20 rounded-xl flex items-center justify-center">
                  <Settings className="w-5 h-5 text-slate-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{t('chatbot.config.title')}</h3>
                  <p className="text-xs text-slate-500">{t('chatbot.config.subtitle')}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-white/[0.04] rounded-xl border border-white/5">
                  <span className="text-xs font-medium text-slate-500 block mb-1">{t('chatbot.config.model')}</span>
                  <span className="text-sm text-white">{chatbot.model_name || 'gpt-3.5-turbo'}</span>
                </div>
                <div className="p-3 bg-white/[0.04] rounded-xl border border-white/5">
                  <span className="text-xs font-medium text-slate-500 block mb-1">{t('chatbot.config.temperature')}</span>
                  <span className="text-sm text-white">{chatbot.temperature || 0.7}</span>
                </div>
                <div className="p-3 bg-white/[0.04] rounded-xl border border-white/5">
                  <span className="text-xs font-medium text-slate-500 block mb-1">{t('chatbot.config.maxTokens')}</span>
                  <span className="text-sm text-white">{chatbot.max_tokens || 150}</span>
                </div>
                <div className="p-3 bg-white/[0.04] rounded-xl border border-white/5">
                  <span className="text-xs font-medium text-slate-500 block mb-1">{t('chatbot.config.citations')}</span>
                  <span className={`text-sm ${chatbot.enable_citations ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {chatbot.enable_citations ? t('chatbot.config.enabled') : t('chatbot.config.disabled')}
                  </span>
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleEditChatbot}
                className="mt-4 flex items-center gap-2 px-4 py-2.5 bg-white/[0.06] border border-white/10 text-slate-300 text-sm font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
              >
                <Settings className="w-4 h-4" />
                {t('chatbot.config.editConfig')}
              </motion.button>
            </div>

            {/* Public Access Card */}
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-cyan-500/20 rounded-xl flex items-center justify-center">
                  <Globe className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{t('chatbot.publicAccess.title')}</h3>
                  <p className="text-xs text-slate-500">{t('chatbot.publicAccess.subtitle')}</p>
                </div>
              </div>

              <div className="p-3 bg-slate-900/50 rounded-xl border border-white/5">
                <span className="text-xs font-medium text-slate-500 block mb-1">{t('chatbot.publicAccess.publicUrl')}</span>
                <code className="text-sm text-cyan-400 break-all">
                  {chatbot.public_url || `${window.location.origin}/chat/${chatbot.public_url_slug}`}
                </code>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowEmbedModal(true)}
                className="mt-4 flex items-center gap-2 px-4 py-2.5 bg-white/[0.06] border border-white/10 text-slate-300 text-sm font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
              >
                <Code className="w-4 h-4" />
                {t('chatbot.publicAccess.getEmbed')}
              </motion.button>
            </div>
          </motion.div>
        )

      case 'analytics':
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="p-8 bg-white/[0.04] rounded-2xl border border-white/10 text-center">
              <div className="w-16 h-16 bg-cyan-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="w-8 h-8 text-cyan-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {t('chatbot.analyticsComingSoon.title')}
              </h3>
              <p className="text-sm text-slate-400 max-w-sm mx-auto">
                {t('chatbot.analyticsComingSoon.desc')}
              </p>
              <div className="mt-6 flex items-center justify-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-violet-400 font-medium">{t('chatbot.analyticsComingSoon.badge')}</span>
              </div>
            </div>
          </motion.div>
        )

      case 'embed':
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-amber-500/20 rounded-xl flex items-center justify-center">
                  <Code className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{t('chatbot.embedWidget.title')}</h3>
                  <p className="text-xs text-slate-500">{t('chatbot.embedWidget.subtitle')}</p>
                </div>
              </div>

              <div className="p-4 bg-violet-500/10 rounded-xl border border-violet-500/20 mb-4">
                <div className="flex items-start gap-3">
                  <Globe className="w-5 h-5 text-violet-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium text-violet-300 text-sm">{t('chatbot.embedWidget.widgetUrl')}</h4>
                    <code className="text-xs text-violet-400 mt-1 break-all">
                      {window.location.origin}/widget/{chatbot.public_url_slug}
                    </code>
                  </div>
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowEmbedModal(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-violet-600 text-white font-medium rounded-xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-shadow"
              >
                <Code className="w-4 h-4" />
                {t('chatbot.publicAccess.getEmbed')}
              </motion.button>
            </div>
          </motion.div>
        )

      case 'integrations':
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">{t('integrations.title')}</h3>
              <p className="text-slate-400 text-sm">
                {t('integrations.subtitle')}
              </p>
            </div>

            {/* HubSpot Integration Card */}
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 bg-orange-500/20 rounded-xl flex items-center justify-center">
                  <Zap className="w-6 h-6 text-orange-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">{t('integrations.hubspot.title')}</h4>
                  <p className="text-xs text-slate-500">{t('integrations.hubspot.desc')}</p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Status Toggle */}
                <div className="flex items-center justify-between p-3 bg-white/[0.04] rounded-xl border border-white/5">
                  <span className="text-sm font-medium text-slate-300">{t('integrations.status')}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{t('chatbot.config.disabled')}</span>
                    <button className="relative w-11 h-6 bg-white/10 rounded-full transition-colors">
                      <span className="absolute top-1 left-1 rtl:left-auto rtl:right-1 w-4 h-4 bg-slate-400 rounded-full transition-transform" />
                    </button>
                    <span className="text-xs text-slate-500">{t('chatbot.config.enabled')}</span>
                  </div>
                </div>

                {/* HubSpot Form URL */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-2">
                    {t('integrations.hubspot.formUrl')}
                  </label>
                  <input
                    type="url"
                    placeholder={t('integrations.hubspot.formUrlPlaceholder')}
                    className="w-full px-4 py-3 bg-white/[0.04] border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50 focus:bg-white/[0.06] transition-colors"
                  />
                  <p className="text-xs text-slate-600 mt-1.5">
                    {t('integrations.hubspot.formUrlHint')}
                  </p>
                </div>

                {/* Trigger Settings */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-2">
                    {t('integrations.hubspot.whenToSend')}
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 p-3 bg-white/[0.04] rounded-xl border border-white/5 cursor-pointer hover:bg-white/[0.06] transition-colors">
                      <input type="radio" name="trigger" defaultChecked className="w-4 h-4 text-violet-500 border-white/20 bg-white/10 focus:ring-violet-500/50" />
                      <span className="text-sm text-slate-300">{t('integrations.hubspot.onEmail')}</span>
                    </label>
                    <label className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/5 cursor-not-allowed opacity-50">
                      <input type="radio" name="trigger" disabled className="w-4 h-4 text-violet-500 border-white/20 bg-white/10" />
                      <span className="text-sm text-slate-500">{t('integrations.hubspot.allConversations')}</span>
                    </label>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="flex-1 px-4 py-2.5 bg-white/[0.06] border border-white/10 text-slate-300 text-sm font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
                  >
                    {t('integrations.hubspot.testConnection')}
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="flex-1 px-4 py-2.5 bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-shadow"
                  >
                    {t('integrations.hubspot.saveSettings')}
                  </motion.button>
                </div>

                {/* Status */}
                <div className="flex items-center gap-2 p-3 bg-white/[0.04] rounded-xl">
                  <div className="w-2 h-2 bg-slate-500 rounded-full" />
                  <span className="text-xs text-slate-500">{t('integrations.hubspot.notConfigured')}</span>
                </div>
              </div>
            </div>

            {/* Future Integrations */}
            <div className="p-5 bg-white/[0.04] rounded-2xl border border-white/10">
              <h4 className="font-semibold text-white mb-4">{t('integrations.comingSoon')}</h4>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-4 bg-white/[0.04] rounded-xl border border-white/5 opacity-60">
                  <div className="w-10 h-10 bg-blue-500/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                    <Zap className="w-5 h-5 text-blue-400" />
                  </div>
                  <p className="text-sm font-medium text-white">Zoho CRM</p>
                  <p className="text-xs text-slate-500 mt-1">{t('integrations.comingSoon')}</p>
                </div>

                <div className="text-center p-4 bg-white/[0.04] rounded-xl border border-white/5 opacity-60">
                  <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                    <Zap className="w-5 h-5 text-emerald-400" />
                  </div>
                  <p className="text-sm font-medium text-white">Salesforce</p>
                  <p className="text-xs text-slate-500 mt-1">{t('integrations.comingSoon')}</p>
                </div>

                <div className="text-center p-4 bg-white/[0.04] rounded-xl border border-white/5 opacity-60">
                  <div className="w-10 h-10 bg-fuchsia-500/20 rounded-xl flex items-center justify-center mx-auto mb-2">
                    <MessageSquare className="w-5 h-5 text-fuchsia-400" />
                  </div>
                  <p className="text-sm font-medium text-white">Slack</p>
                  <p className="text-xs text-slate-500 mt-1">{t('integrations.comingSoon')}</p>
                </div>
              </div>
            </div>
          </motion.div>
        )

      default:
        return null
    }
  }

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="xl"
        title="Chatbot Settings"
        showCloseButton={true}
      >
        <div className="space-y-6">
          {/* Tabs - Premium dark style */}
          <div className="flex flex-wrap gap-1.5 p-1.5 bg-white/[0.04] rounded-xl border border-white/10">
            {tabs.map((tab) => (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`relative flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'text-white'
                    : 'text-slate-500 hover:text-white hover:bg-white/5'
                }`}
              >
                {activeTab === tab.id && (
                  <motion.div
                    layoutId="activeTabBg"
                    className="absolute inset-0 bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 rounded-lg border border-violet-500/20"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <tab.icon className={`w-4 h-4 flex-shrink-0 relative z-10 ${activeTab === tab.id ? tab.color : ''}`} />
                <span className="relative z-10">{t(tab.labelKey)}</span>
              </motion.button>
            ))}
          </div>

          {/* Content */}
          <div className="min-h-[300px] max-h-[60vh] overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            <AnimatePresence mode="wait">
              {loading ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center justify-center py-12"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
                    <span className="text-slate-400">Loading...</span>
                  </div>
                </motion.div>
              ) : (
                renderTabContent()
              )}
            </AnimatePresence>
          </div>

          {/* Close Button */}
          <div className="flex justify-end pt-4 border-t border-white/10">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onClose}
              className="px-5 py-2.5 bg-white/[0.06] border border-white/10 text-slate-300 text-sm font-medium rounded-xl hover:bg-white/10 hover:text-white transition-colors"
            >
              Close
            </motion.button>
          </div>
        </div>
      </Modal>

      {/* Edit Wizard */}
      <ChatbotWizard
        isOpen={showEditWizard}
        onClose={() => setShowEditWizard(false)}
        onSuccess={handleWizardSuccess}
        existingChatbot={chatbot}
      />

      {/* Embed Code Modal */}
      <EmbedCodeModal
        isOpen={showEmbedModal}
        onClose={() => setShowEmbedModal(false)}
        chatbot={chatbot}
      />
    </>
  )
}