import { useState, useEffect } from 'react'
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
  Zap
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
    { id: 'overview' as TabType, label: 'Overview', icon: Bot },
    { id: 'knowledge' as TabType, label: 'Knowledge Sources', icon: Upload },
    { id: 'settings' as TabType, label: 'Settings', icon: Settings },
    { id: 'analytics' as TabType, label: 'Analytics', icon: BarChart3 },
    { id: 'embed' as TabType, label: 'Embed', icon: Code },
    { id: 'integrations' as TabType, label: 'Integrations', icon: Zap }
  ]

  const handleEditChatbot = () => {
    setShowEditWizard(true)
  }

  const handleWizardSuccess = () => {
    setShowEditWizard(false)
    onChatbotUpdated()
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'success' as const,
      training: 'warning' as const,
      error: 'error' as const,
      draft: 'secondary' as const
    }
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>
        {status}
      </Badge>
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
          <div className="space-y-4">
            {/* Chatbot Info */}
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">{chatbot.name}</h3>
                <p className="text-gray-600">{chatbot.description}</p>
                <div className="flex items-center space-x-2 mt-1">
                  {getStatusBadge(chatbot.status)}
                  <span className="text-sm text-gray-500">
                    Created {formatDate(chatbot.created_at)}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <MessageSquare className="w-5 h-5 text-primary-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-gray-900">{chatbot.total_conversations || 0}</p>
                <p className="text-xs text-gray-500">Conversations</p>
              </div>
              
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <Users className="w-5 h-5 text-accent-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-gray-900">{chatbot.total_messages || 0}</p>
                <p className="text-xs text-gray-500">Messages</p>
              </div>
              
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <Upload className="w-5 h-5 text-success-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-gray-900">{chatbot.has_knowledge_sources ? '✓' : '0'}</p>
                <p className="text-xs text-gray-500">Knowledge</p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4">
              <Button 
                variant="gradient" 
                onClick={() => window.open(`/chat/${chatbot.id}`, '_blank')}
                className="w-full"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Test Chat
              </Button>
              <Button 
                variant="outline"
                onClick={() => setActiveTab('knowledge')}
                className="w-full"
              >
                <Upload className="w-4 h-4 mr-2" />
                Knowledge
              </Button>
              <Button 
                variant="outline"
                onClick={() => setActiveTab('embed')}
                className="w-full"
              >
                <Code className="w-4 h-4 mr-2" />
                Embed
              </Button>
            </div>
          </div>
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
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Chatbot Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Model:</span>
                    <span className="ml-2 text-gray-600">{chatbot.model_name || 'gpt-3.5-turbo'}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Temperature:</span>
                    <span className="ml-2 text-gray-600">{chatbot.temperature || 0.7}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Max Tokens:</span>
                    <span className="ml-2 text-gray-600">{chatbot.max_tokens || 150}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Citations:</span>
                    <span className="ml-2 text-gray-600">
                      {chatbot.enable_citations ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>
                
                <div className="pt-4 border-t">
                  <Button onClick={handleEditChatbot} variant="outline">
                    <Settings className="w-4 h-4 mr-2" />
                    Edit Configuration
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Public Access</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <span className="font-medium text-gray-700">Public URL:</span>
                    <div className="mt-1 p-2 bg-gray-50 rounded border text-sm font-mono">
                      {chatbot.public_url || `https://your-domain.com/chat/${chatbot.public_url_slug}`}
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setShowEmbedModal(true)}
                  >
                    <Code className="w-4 h-4 mr-2" />
                    Get Embed Code
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'analytics':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Usage Analytics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Analytics Coming Soon
                  </h3>
                  <p className="text-sm text-gray-600">
                    Detailed conversation analytics and performance metrics will be available here.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'embed':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Embed Your Chatbot</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Get the embed code to add this chatbot to any website.
                  </p>
                  
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <Code className="w-5 h-5 text-blue-600 mt-0.5" />
                      <div>
                        <h4 className="font-medium text-blue-900">Widget URL</h4>
                        <p className="text-sm text-blue-700 mt-1">
                          {window.location.origin}/widget/{chatbot.public_url_slug}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <Button 
                    variant="gradient"
                    onClick={() => setShowEmbedModal(true)}
                    className="w-full"
                  >
                    <Code className="w-4 h-4 mr-2" />
                    Get Embed Code
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'integrations':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Connect Your Tools</h3>
              <p className="text-gray-600 text-sm">
                Automatically send leads and conversation data to your business tools.
              </p>
            </div>

            {/* HubSpot Integration Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <Zap className="w-5 h-5 text-orange-600" />
                  </div>
                  <div>
                    <CardTitle>HubSpot Integration</CardTitle>
                    <p className="text-sm text-gray-600">Send leads directly to HubSpot CRM</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Status Toggle */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Status:</span>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">Disabled</span>
                      <div className="relative">
                        <input type="checkbox" className="sr-only" />
                        <div className="w-10 h-6 bg-gray-200 rounded-full shadow-inner cursor-pointer">
                          <div className="w-4 h-4 bg-white rounded-full shadow transform translate-x-1 translate-y-1 transition-transform"></div>
                        </div>
                      </div>
                      <span className="text-sm text-gray-500">Enabled</span>
                    </div>
                  </div>

                  {/* HubSpot Form URL */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      HubSpot Form URL
                    </label>
                    <input
                      type="url"
                      placeholder="https://forms.hubspot.com/uploads/form/v2/your-portal-id/your-form-guid"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      ℹ️ Paste your HubSpot form submission URL from your forms settings
                    </p>
                  </div>

                  {/* Trigger Settings */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      When to Send Leads
                    </label>
                    <div className="space-y-2">
                      <label className="flex items-center">
                        <input type="radio" name="trigger" className="mr-2" defaultChecked />
                        <span className="text-sm text-gray-700">When email is captured in conversation</span>
                      </label>
                      <label className="flex items-center">
                        <input type="radio" name="trigger" className="mr-2" disabled />
                        <span className="text-sm text-gray-400">Send all conversations (Coming Soon)</span>
                      </label>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex space-x-3 pt-4">
                    <Button variant="outline" size="sm">
                      Test Connection
                    </Button>
                    <Button variant="primary" size="sm">
                      Save Settings
                    </Button>
                  </div>

                  {/* Status */}
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      <span className="text-sm text-gray-600">Not configured</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Future Integrations */}
            <Card>
              <CardHeader>
                <CardTitle>Coming Soon</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-gray-50 rounded-lg opacity-60">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                      <Zap className="w-4 h-4 text-blue-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-700">Zoho CRM</p>
                    <p className="text-xs text-gray-500">Coming Soon</p>
                  </div>
                  
                  <div className="text-center p-4 bg-gray-50 rounded-lg opacity-60">
                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                      <Zap className="w-4 h-4 text-green-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-700">Salesforce</p>
                    <p className="text-xs text-gray-500">Coming Soon</p>
                  </div>
                  
                  <div className="text-center p-4 bg-gray-50 rounded-lg opacity-60">
                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                      <MessageSquare className="w-4 h-4 text-purple-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-700">Slack</p>
                    <p className="text-xs text-gray-500">Coming Soon</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
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
        showCloseButton={false}
      >
        <div className="space-y-6">
          {/* Tabs */}
          <div className="flex flex-wrap gap-2 bg-gray-100 rounded-lg p-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <tab.icon className="w-4 h-4 flex-shrink-0" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="min-h-[300px] max-h-[60vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner className="w-8 h-8" />
              </div>
            ) : (
              renderTabContent()
            )}
          </div>
          
          {/* Close Button */}
          <div className="flex justify-end pt-4 border-t border-gray-200">
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
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