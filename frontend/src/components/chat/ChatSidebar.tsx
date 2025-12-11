import React, { useState } from 'react'
import { 
  X,
  Zap,
  Code,
  Settings,
  BarChart3,
  Upload,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  TestTube,
  Eye,
  EyeOff
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface ChatSidebarProps {
  isOpen: boolean
  onClose: () => void
  chatbot: Chatbot
  onChatbotUpdate?: () => void
}

type SidebarPanel = 'crm' | 'embed' | 'settings' | 'stats' | 'knowledge'

export function ChatSidebar({ isOpen, onClose, chatbot, onChatbotUpdate }: ChatSidebarProps) {
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

  // Load CRM settings when sidebar opens
  const loadCrmSettings = async () => {
    if (!chatbot.id) return
    
    try {
      const response = await apiService.request(`/chatbots/${chatbot.id}/crm/settings/`)
      setCrmEnabled(response.crm_enabled || false)
      setCrmUrl(response.crm_webhook_url || '')
      setCrmStatus(response.status || 'not_configured')
    } catch (error) {
      console.error('Failed to load CRM settings:', error)
    }
  }

  // Save CRM settings
  const saveCrmSettings = async () => {
    if (!chatbot.id) return
    
    try {
      setLoading(true)
      await apiService.request(`/chatbots/${chatbot.id}/crm/settings/`, {
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

  // Test CRM connection
  const testCrmConnection = async () => {
    if (!chatbot.id || !crmUrl) return
    
    try {
      setCrmStatus('testing')
      const response = await apiService.request(`/chatbots/${chatbot.id}/crm/test/`, {
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

  // Generate embed code
  const getEmbedCode = () => {
    const baseUrl = window.location.origin
    const slug = chatbot.public_url_slug || chatbot.id
    
    if (embedType === 'iframe') {
      return `<iframe
  src="${baseUrl}/widget/${slug}"
  width="100%"
  height="600"
  frameborder="0"
  style="border: 1px solid #e5e7eb; border-radius: 8px;"
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
    { id: 'crm' as SidebarPanel, label: 'CRM', icon: Zap, color: 'text-orange-600' },
    { id: 'embed' as SidebarPanel, label: 'Embed', icon: Code, color: 'text-blue-600' },
    { id: 'settings' as SidebarPanel, label: 'Settings', icon: Settings, color: 'text-gray-600' },
    { id: 'stats' as SidebarPanel, label: 'Stats', icon: BarChart3, color: 'text-green-600' },
    { id: 'knowledge' as SidebarPanel, label: 'Knowledge', icon: Upload, color: 'text-purple-600' }
  ]

  const renderPanelContent = () => {
    switch (activePanel) {
      case 'crm':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">HubSpot Integration</h3>
              <p className="text-sm text-gray-600">Automatically send leads to your CRM when emails are captured.</p>
            </div>

            {/* Enable Toggle */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Enable CRM</span>
              <button
                onClick={() => setCrmEnabled(!crmEnabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  crmEnabled ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    crmEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {crmEnabled && (
              <>
                {/* HubSpot URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    HubSpot Form URL
                  </label>
                  <Input
                    type="url"
                    placeholder="https://forms.hubspot.com/..."
                    value={crmUrl}
                    onChange={(e) => setCrmUrl(e.target.value)}
                    className="text-sm"
                  />
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key (Optional)
                  </label>
                  <div className="relative">
                    <Input
                      type={showApiKey ? "text" : "password"}
                      placeholder="Optional API key"
                      value={crmApiKey}
                      onChange={(e) => setCrmApiKey(e.target.value)}
                      className="text-sm pr-10"
                    />
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex space-x-2">
                  <Button
                    onClick={testCrmConnection}
                    variant="outline"
                    size="sm"
                    disabled={!crmUrl || crmStatus === 'testing'}
                    className="flex-1"
                  >
                    <TestTube className="w-4 h-4 mr-1" />
                    {crmStatus === 'testing' ? 'Testing...' : 'Test'}
                  </Button>
                  <Button
                    onClick={saveCrmSettings}
                    variant="primary"
                    size="sm"
                    disabled={loading}
                    className="flex-1"
                  >
                    Save
                  </Button>
                </div>

                {/* Status */}
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    crmStatus === 'configured' ? 'bg-green-500' : 
                    crmStatus === 'testing' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-sm text-gray-600">
                    {crmStatus === 'configured' ? 'Connected' : 
                     crmStatus === 'testing' ? 'Testing...' : 'Not configured'}
                  </span>
                </div>
              </>
            )}
          </div>
        )

      case 'embed':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Embed Widget</h3>
              <p className="text-sm text-gray-600">Copy this code to add the chatbot to any website.</p>
            </div>

            {/* Widget Preview URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Widget URL
              </label>
              <div className="p-2 bg-gray-50 rounded border text-sm font-mono text-gray-800">
                {window.location.origin}/widget/{chatbot.public_url_slug}
              </div>
            </div>

            {/* Embed Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Embed Type
              </label>
              <div className="flex space-x-2">
                <button
                  onClick={() => setEmbedType('iframe')}
                  className={`flex-1 px-3 py-2 text-sm rounded-lg border transition-colors ${
                    embedType === 'iframe' 
                      ? 'bg-primary-50 border-primary-200 text-primary-700' 
                      : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  Iframe
                </button>
                <button
                  onClick={() => setEmbedType('script')}
                  className={`flex-1 px-3 py-2 text-sm rounded-lg border transition-colors ${
                    embedType === 'script' 
                      ? 'bg-primary-50 border-primary-200 text-primary-700' 
                      : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  Script
                </button>
              </div>
            </div>

            {/* Embed Code */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Code
              </label>
              <div className="relative">
                <pre className="bg-gray-900 text-gray-100 text-xs p-3 rounded-lg overflow-x-auto max-h-32">
                  <code>{getEmbedCode()}</code>
                </pre>
                <Button
                  onClick={copyEmbedCode}
                  variant="ghost"
                  size="sm"
                  className="absolute top-2 right-2 text-gray-400 hover:text-gray-200"
                >
                  {embedCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          </div>
        )

      case 'settings':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Quick Settings</h3>
              <p className="text-sm text-gray-600">Adjust chatbot behavior during testing.</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bot Name
              </label>
              <Input
                value={chatbot.name}
                disabled
                className="text-sm bg-gray-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={chatbot.description || ''}
                disabled
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-gray-50 resize-none"
                rows={2}
              />
            </div>

            <div className="pt-2">
              <p className="text-xs text-gray-500">
                💡 To edit settings, go to Dashboard → Chatbot Settings
              </p>
            </div>
          </div>
        )

      case 'stats':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Live Stats</h3>
              <p className="text-sm text-gray-600">Real-time chatbot performance metrics.</p>
            </div>

            <div className="grid grid-cols-1 gap-3">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">{chatbot.total_conversations || 0}</div>
                <div className="text-xs text-gray-500">Conversations</div>
              </div>
              
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">{chatbot.total_messages || 0}</div>
                <div className="text-xs text-gray-500">Messages</div>
              </div>
              
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">
                  {chatbot.status === 'ready' ? '✓' : '○'}
                </div>
                <div className="text-xs text-gray-500">Status</div>
              </div>
            </div>
          </div>
        )

      case 'knowledge':
        return (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Knowledge Base</h3>
              <p className="text-sm text-gray-600">Documents and sources this bot can reference.</p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Knowledge Sources:</span>
                <Badge variant={chatbot.has_knowledge_sources ? 'success' : 'secondary'}>
                  {chatbot.has_knowledge_sources ? 'Active' : 'None'}
                </Badge>
              </div>
            </div>

            <div className="pt-2">
              <p className="text-xs text-gray-500">
                💡 To manage knowledge sources, go to Dashboard → Knowledge Sources
              </p>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  // Load CRM settings when sidebar opens
  React.useEffect(() => {
    if (isOpen && activePanel === 'crm') {
      loadCrmSettings()
    }
  }, [isOpen, activePanel])

  if (!isOpen) return null

  return (
    <div className="absolute right-0 top-0 bottom-0 w-80 bg-white border-l border-gray-200 shadow-lg z-10">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Quick Actions</h2>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Panel Navigation */}
      <div className="flex overflow-x-auto p-2 border-b border-gray-200 bg-gray-50">
        {panels.map((panel) => (
          <button
            key={panel.id}
            onClick={() => setActivePanel(panel.id)}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              activePanel === panel.id
                ? 'bg-white text-primary-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <panel.icon className={`w-4 h-4 ${panel.color}`} />
            <span>{panel.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {renderPanelContent()}
      </div>
    </div>
  )
}