import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import {
  X,
  Zap,
  Code,
  Settings,
  BarChart3,
  Upload,
  Copy,
  Check,
  TestTube,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
  Globe,
  Sparkles
} from 'lucide-react'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

// Stagger animation variants for panel content
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1
    }
  }
}

const itemVariants: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: 'spring', stiffness: 400, damping: 25 }
  }
}

// ChatSidebar can accept either full Chatbot or minimal props
type ChatbotProp = Chatbot | { id: string; name: string; description?: string }

interface ChatSidebarProps {
  isOpen: boolean
  onClose: () => void
  chatbot: ChatbotProp
  onChatbotUpdate?: () => void
}

type SidebarPanel = 'crm' | 'embed' | 'settings' | 'stats' | 'knowledge'

export function ChatSidebar({ isOpen, onClose, chatbot, onChatbotUpdate }: ChatSidebarProps) {
  const { t } = useTranslation()
  const [activePanel, setActivePanel] = useState<SidebarPanel>('crm')
  const [loading, setLoading] = useState(false)

  // CRM State
  const [crmEnabled, setCrmEnabled] = useState(false)
  const [crmUrl, setCrmUrl] = useState('')
  const [crmApiKey, setCrmApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [crmStatus, setCrmStatus] = useState<'not_configured' | 'configured' | 'testing'>('not_configured')

  // Embed State
  const [embedCopied, setEmbedCopied] = useState(false)
  const [embedType, setEmbedType] = useState<'iframe' | 'script'>('iframe')

  const loadCrmSettings = async () => {
    if (!chatbot.id) return

    try {
      const response = await (apiService as any).request(`/chatbots/${chatbot.id}/crm/settings/`)
      setCrmEnabled(response.crm_enabled || false)
      setCrmUrl(response.crm_webhook_url || '')
      setCrmStatus(response.status || 'not_configured')
    } catch (error) {
      console.error('Failed to load CRM settings:', error)
    }
  }

  const saveCrmSettings = async () => {
    if (!chatbot.id) return

    try {
      setLoading(true)
      await (apiService as any).request(`/chatbots/${chatbot.id}/crm/settings/`, {
        method: 'POST',
        body: JSON.stringify({
          crm_enabled: crmEnabled,
          crm_provider: 'hubspot',
          webhook_url: crmUrl,
          api_key: crmApiKey
        })
      })
      setCrmStatus('configured')
      if (onChatbotUpdate) onChatbotUpdate()
    } catch (error) {
      console.error('Failed to save CRM settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const testCrmConnection = async () => {
    if (!chatbot.id || !crmUrl) return

    try {
      setCrmStatus('testing')
      const response = await (apiService as any).request(`/chatbots/${chatbot.id}/crm/test/`, {
        method: 'POST',
        body: JSON.stringify({
          provider: 'hubspot',
          webhook_url: crmUrl,
          api_key: crmApiKey
        })
      })

      if (response.success) {
        setCrmStatus('configured')
        alert('Connection successful!')
      } else {
        alert(`Connection failed: ${response.message}`)
        setCrmStatus('not_configured')
      }
    } catch (error) {
      console.error('Failed to test CRM connection:', error)
      alert('Connection test failed')
      setCrmStatus('not_configured')
    }
  }

  const getEmbedCode = () => {
    const baseUrl = window.location.origin
    const slug = ('public_url_slug' in chatbot && chatbot.public_url_slug) || chatbot.id

    if (embedType === 'iframe') {
      return `<iframe
  src="${baseUrl}/widget/${slug}"
  width="100%"
  height="600"
  frameborder="0"
  style="border: 1px solid #1e293b; border-radius: 12px;"
  title="${chatbot.name} - AI Assistant"
></iframe>`
    } else {
      return `<script>
  (function() {
    var script = document.createElement('script');
    script.src = '${baseUrl}/widget/chatbot-widget.js';
    script.setAttribute('data-chatbot-slug', '${slug}');
    script.setAttribute('data-position', 'bottom-right');
    script.async = true;
    document.head.appendChild(script);
  })();
</script>`
    }
  }

  const copyEmbedCode = () => {
    navigator.clipboard.writeText(getEmbedCode())
    setEmbedCopied(true)
    setTimeout(() => setEmbedCopied(false), 2000)
  }

  const panels = [
    { id: 'crm' as SidebarPanel, labelKey: 'CRM', icon: Zap, color: 'text-amber-400' },
    { id: 'embed' as SidebarPanel, labelKey: 'chatbot.embed', icon: Code, color: 'text-cyan-400' },
    { id: 'settings' as SidebarPanel, labelKey: 'sidebar.settings', icon: Settings, color: 'text-slate-400' },
    { id: 'stats' as SidebarPanel, labelKey: 'chatSidebar.liveStats', icon: BarChart3, color: 'text-emerald-400' },
    { id: 'knowledge' as SidebarPanel, labelKey: 'chatbot.knowledge', icon: Upload, color: 'text-violet-400' }
  ]

  const renderPanelContent = () => {
    switch (activePanel) {
      case 'crm':
        return (
          <div className="space-y-4">
            <motion.div variants={itemVariants}>
              <h3 className="font-semibold text-white mb-1">{t('chatSidebar.hubspotIntegration')}</h3>
              <p className="text-xs text-slate-500">{t('chatSidebar.hubspotDesc')}</p>
            </motion.div>

            {/* Enable Toggle */}
            <motion.div
              variants={itemVariants}
              className="flex items-center justify-between p-4 bg-white/[0.04] rounded-xl border border-white/10 hover:bg-white/[0.06] transition-colors"
            >
              <span className="text-sm font-medium text-slate-300">{t('chatSidebar.enableCrm')}</span>
              <motion.button
                onClick={() => setCrmEnabled(!crmEnabled)}
                whileTap={{ scale: 0.95 }}
                className={`relative w-12 h-7 rounded-full transition-all duration-300 ${crmEnabled
                  ? 'bg-gradient-to-r from-violet-500 to-fuchsia-500 shadow-lg shadow-violet-500/25'
                  : 'bg-white/10'
                  }`}
              >
                <motion.span
                  layout
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow-md ${crmEnabled ? 'left-6' : 'left-1'
                    }`}
                />
              </motion.button>
            </motion.div>

            {crmEnabled && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="space-y-4"
              >
                {/* HubSpot URL */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    {t('chatSidebar.hubspotFormUrl')}
                  </label>
                  <input
                    type="url"
                    placeholder="https://forms.hubspot.com/..."
                    value={crmUrl}
                    onChange={(e) => setCrmUrl(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50"
                  />
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    {t('chatSidebar.apiKey')}
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? "text" : "password"}
                      placeholder={t('chatSidebar.apiKeyPlaceholder')}
                      value={crmApiKey}
                      onChange={(e) => setCrmApiKey(e.target.value)}
                      className="w-full px-3 py-2 pr-10 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50 rtl:pr-3 rtl:pl-10"
                    />
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-2 rtl:right-auto rtl:left-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-400"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={testCrmConnection}
                    disabled={!crmUrl || crmStatus === 'testing'}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 hover:bg-white/10 disabled:opacity-50 transition-colors"
                  >
                    <TestTube className="w-4 h-4" />
                    {crmStatus === 'testing' ? t('chatSidebar.testing') : t('chatSidebar.test')}
                  </button>
                  <button
                    onClick={saveCrmSettings}
                    disabled={loading}
                    className="flex-1 px-3 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 text-sm text-white font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    {t('chatSidebar.save')}
                  </button>
                </div>

                {/* Status */}
                <div className="flex items-center gap-2 p-2 bg-white/5 rounded-lg">
                  <div className={`w-2 h-2 rounded-full ${crmStatus === 'configured' ? 'bg-emerald-500' :
                      crmStatus === 'testing' ? 'bg-amber-500 animate-pulse' : 'bg-slate-500'
                    }`} />
                  <span className="text-xs text-slate-400">
                    {crmStatus === 'configured' ? t('chatSidebar.connected') :
                      crmStatus === 'testing' ? t('chatSidebar.testing') : t('chatSidebar.notConfigured')}
                  </span>
                </div>
              </motion.div>
            )}
          </div>
        )

      case 'embed':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-white mb-1">{t('chatSidebar.embedWidget')}</h3>
              <p className="text-xs text-slate-500">{t('chatSidebar.embedWidgetDesc')}</p>
            </div>

            {/* Widget URL */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t('chatSidebar.widgetUrl')}
              </label>
              <div className="flex items-center gap-2 p-2.5 bg-white/5 rounded-lg border border-white/10">
                <Globe className="w-4 h-4 text-slate-500" />
                <code className="text-xs text-cyan-400 truncate flex-1" dir="ltr">
                  {window.location.origin}/widget/{('public_url_slug' in chatbot && chatbot.public_url_slug) || chatbot.id}
                </code>
              </div>
            </div>

            {/* Embed Type */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2">
                {t('chatSidebar.embedType')}
              </label>
              <div className="flex gap-2">
                {['iframe', 'script'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setEmbedType(type as 'iframe' | 'script')}
                    className={`flex-1 px-3 py-2 text-sm rounded-lg border transition-colors ${embedType === type
                        ? 'bg-violet-500/20 border-violet-500/50 text-violet-300'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:text-white hover:bg-white/10'
                      }`}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Embed Code */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t('chatSidebar.code')}
              </label>
              <div className="relative">
                <pre className="bg-slate-900 text-slate-300 text-xs p-3 rounded-xl border border-white/10 overflow-x-auto max-h-32" dir="ltr">
                  <code>{getEmbedCode()}</code>
                </pre>
                <button
                  onClick={copyEmbedCode}
                  className="absolute top-2 right-2 rtl:right-auto rtl:left-2 p-1.5 rounded-lg bg-white/10 text-slate-400 hover:text-white hover:bg-white/20 transition-colors"
                >
                  {embedCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        )

      case 'settings':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-white mb-1">{t('chatSidebar.quickSettings')}</h3>
              <p className="text-xs text-slate-500">{t('chatSidebar.settingsDesc')}</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t('chatSidebar.botName')}
              </label>
              <input
                value={chatbot.name}
                disabled
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-slate-300 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t('chatbotModal.description')}
              </label>
              <textarea
                value={chatbot.description || ''}
                disabled
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-slate-300 text-sm resize-none"
                rows={2}
              />
            </div>

            <div className="p-3 bg-violet-500/10 rounded-xl border border-violet-500/20">
              <p className="text-xs text-violet-300">
                {t('chatSidebar.settingsNote')}
              </p>
            </div>
          </div>
        )

      case 'stats':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-white mb-1">{t('chatSidebar.liveStats')}</h3>
              <p className="text-xs text-slate-500">{t('chatSidebar.statsDesc')}</p>
            </div>

            <div className="grid grid-cols-1 gap-3">
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
                <div className="text-2xl font-bold text-white">{('total_conversations' in chatbot && chatbot.total_conversations) || 0}</div>
                <div className="text-xs text-slate-500 mt-1">{t('chatSidebar.conversations')}</div>
              </div>

              <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
                <div className="text-2xl font-bold text-white">{('total_messages' in chatbot && chatbot.total_messages) || 0}</div>
                <div className="text-xs text-slate-500 mt-1">{t('chatSidebar.messages')}</div>
              </div>

              <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
                <div className="flex items-center justify-center gap-2">
                  {('status' in chatbot && (chatbot.status === 'active' || chatbot.status === 'completed')) ? (
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-6 h-6 text-amber-400" />
                  )}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {('status' in chatbot && (chatbot.status === 'active' || chatbot.status === 'completed')) ? t('chatSidebar.active') : ('status' in chatbot ? t(`chatbot.status.${chatbot.status}`) : t('common.loading'))}
                </div>
              </div>
            </div>
          </div>
        )

      case 'knowledge':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-white mb-1">{t('chatSidebar.knowledgeBase')}</h3>
              <p className="text-xs text-slate-500">{t('chatSidebar.knowledgeDesc')}</p>
            </div>

            <div className="p-4 bg-white/5 rounded-xl border border-white/10">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">{t('chatSidebar.knowledgeSources')}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${('has_knowledge_sources' in chatbot && chatbot.has_knowledge_sources)
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-500/20 text-slate-400'
                  }`}>
                  {('has_knowledge_sources' in chatbot && chatbot.has_knowledge_sources) ? t('chatSidebar.active') : t('chatSidebar.none')}
                </span>
              </div>
            </div>

            <div className="p-3 bg-violet-500/10 rounded-xl border border-violet-500/20">
              <p className="text-xs text-violet-300">
                {t('chatSidebar.knowledgeNote')}
              </p>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  React.useEffect(() => {
    if (isOpen && activePanel === 'crm') {
      loadCrmSettings()
    }
  }, [isOpen, activePanel])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/20 backdrop-blur-sm z-10"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 350 }}
            className="absolute right-0 top-0 bottom-0 w-80 bg-slate-900/95 backdrop-blur-xl border-l border-white/10 shadow-2xl shadow-slate-950/50 z-20"
          >
            {/* Ambient glow inside sidebar */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              <div className="absolute -top-20 -right-20 w-40 h-40 bg-violet-500/10 rounded-full blur-[60px]" />
              <div className="absolute -bottom-20 -left-20 w-32 h-32 bg-fuchsia-500/10 rounded-full blur-[50px]" />
            </div>

            {/* Header */}
            <motion.div
              initial={{ y: -10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="relative flex items-center justify-between px-4 py-4 border-b border-white/10 bg-gradient-to-r from-white/5 via-white/[0.07] to-white/5"
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <h2 className="font-semibold text-white">{t('chatSidebar.quickActions')}</h2>
              </div>
              <motion.button
                onClick={onClose}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </motion.button>
            </motion.div>

            {/* Panel Navigation */}
            <div className="relative flex overflow-x-auto p-2 border-b border-white/10 bg-white/[0.03] gap-1 scrollbar-hide">
              {panels.map((panel) => (
                <motion.button
                  key={panel.id}
                  onClick={() => setActivePanel(panel.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`relative flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 whitespace-nowrap ${activePanel === panel.id
                      ? 'bg-white/10 text-white shadow-lg'
                      : 'text-slate-500 hover:text-white hover:bg-white/5'
                    }`}
                >
                  {activePanel === panel.id && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 rounded-xl border border-violet-500/20"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  <panel.icon className={`w-3.5 h-3.5 relative z-10 ${activePanel === panel.id ? panel.color : ''}`} />
                  <span className="relative z-10">{panel.id === 'crm' ? 'CRM' : t(panel.labelKey)}</span>
                </motion.button>
              ))}
            </div>

            {/* Content */}
            <div className="relative flex-1 overflow-y-auto p-4">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activePanel}
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  exit="hidden"
                >
                  {renderPanelContent()}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
