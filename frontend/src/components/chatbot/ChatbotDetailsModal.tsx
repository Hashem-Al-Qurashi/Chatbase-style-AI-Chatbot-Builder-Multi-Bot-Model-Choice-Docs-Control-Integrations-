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
  Clock
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

type TabType = 'overview' | 'knowledge' | 'settings' | 'analytics' | 'embed'

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
    { id: 'embed' as TabType, label: 'Embed', icon: Code }
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
          <div className="space-y-6">
            {/* Chatbot Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg">
                  <Bot className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{chatbot.name}</h3>
                  <p className="text-gray-600 mt-1">{chatbot.description}</p>
                  <div className="flex items-center space-x-3 mt-2">
                    {getStatusBadge(chatbot.status)}
                    <span className="text-sm text-gray-500">
                      Created {formatDate(chatbot.created_at)}
                    </span>
                  </div>
                </div>
              </div>
              <Button onClick={handleEditChatbot} variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Edit Settings
              </Button>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <MessageSquare className="w-6 h-6 text-primary-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">
                    {chatbot.total_conversations || 0}
                  </p>
                  <p className="text-sm text-gray-500">Conversations</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4 text-center">
                  <Users className="w-6 h-6 text-accent-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">
                    {chatbot.total_messages || 0}
                  </p>
                  <p className="text-sm text-gray-500">Messages</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4 text-center">
                  <Upload className="w-6 h-6 text-success-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">
                    {chatbot.has_knowledge_sources ? '✓' : '0'}
                  </p>
                  <p className="text-sm text-gray-500">Knowledge Sources</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4 text-center">
                  <Clock className="w-6 h-6 text-warning-600 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-gray-900">&lt; 1s</p>
                  <p className="text-sm text-gray-500">Avg Response</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 text-sm">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-gray-600">Chatbot is active and responding</span>
                    <span className="text-gray-400">2 minutes ago</span>
                  </div>
                  <div className="flex items-center space-x-3 text-sm">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-gray-600">New conversation started</span>
                    <span className="text-gray-400">1 hour ago</span>
                  </div>
                  <div className="flex items-center space-x-3 text-sm">
                    <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                    <span className="text-gray-600">Chatbot created</span>
                    <span className="text-gray-400">{formatDate(chatbot.created_at)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <div className="flex space-x-3">
              <Button 
                variant="gradient" 
                onClick={() => window.open(`/chat/${chatbot.id}`, '_blank')}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Test Chatbot
              </Button>
              <Button 
                variant="outline"
                onClick={() => setShowEmbedModal(true)}
              >
                <Code className="w-4 h-4 mr-2" />
                Get Embed Code
              </Button>
              <Button 
                variant="outline"
                onClick={() => setActiveTab('knowledge')}
              >
                <Upload className="w-4 h-4 mr-2" />
                Manage Knowledge
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
                  <p className="text-sm text-gray-600">
                    Copy and paste this code into your website to embed your chatbot.
                  </p>
                  
                  <div className="p-3 bg-gray-50 rounded border">
                    <code className="text-sm text-gray-800">
                      {`<script src="https://your-domain.com/widget/chatbot-widget.js"></script>
<div id="chatbot-widget" data-chatbot-id="${chatbot.id}"></div>`}
                    </code>
                  </div>
                  
                  <Button 
                    variant="gradient"
                    onClick={() => setShowEmbedModal(true)}
                  >
                    <Code className="w-4 h-4 mr-2" />
                    Get Full Embed Code
                  </Button>
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
      <Modal isOpen={isOpen} onClose={onClose}>
        <div className="w-full max-w-6xl mx-auto">
          <div className="bg-white rounded-xl shadow-xl">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">
                  Chatbot Details
                </h2>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Tabs */}
              <div className="mt-4 flex space-x-1 bg-gray-100 rounded-lg p-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-white text-primary-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="p-6 max-h-[70vh] overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner className="w-8 h-8" />
                </div>
              ) : (
                renderTabContent()
              )}
            </div>
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