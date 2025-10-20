import { useState, useEffect } from 'react'
import { Plus, Bot, MessageSquare, Upload, Link, Code, LogOut } from 'lucide-react'
import { Button } from '../ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'
import { ChatbotWizard } from '../chatbot/ChatbotWizard'
import { ChatbotDeleteModal } from '../chatbot/ChatbotDeleteModal'
import { ChatTest } from '../chat/ChatTest'
import { EmbedCodeModal } from '../chatbot/EmbedCodeModal'

export function SimpleDashboard() {
  const { user, logout } = useAuth()
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Modal states
  const [showWizard, setShowWizard] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showChatTest, setShowChatTest] = useState(false)
  const [showEmbedCode, setShowEmbedCode] = useState(false)
  const [selectedChatbot, setSelectedChatbot] = useState<Chatbot | null>(null)
  const [editingChatbot, setEditingChatbot] = useState<Chatbot | null>(null)

  useEffect(() => {
    loadChatbots()
  }, [])

  const loadChatbots = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiService.getChatbots()
      const chatbotsData = Array.isArray(response) ? response : response.results || []
      setChatbots(chatbotsData)
    } catch (err: any) {
      console.error('Failed to load chatbots:', err)
      setError('Unable to load your chatbots. Please try refreshing the page.')
      setChatbots([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreateChatbot = () => {
    setEditingChatbot(null)
    setShowWizard(true)
  }

  const handleEditChatbot = (chatbot: Chatbot) => {
    setEditingChatbot(chatbot)
    setShowWizard(true)
  }

  const handleDeleteChatbot = (chatbot: Chatbot) => {
    setSelectedChatbot(chatbot)
    setShowDeleteModal(true)
  }

  const handleWizardSuccess = () => {
    loadChatbots()
    setShowWizard(false)
    setEditingChatbot(null)
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  const getStepIcon = (step: string) => {
    switch (step) {
      case 'upload':
        return <Upload className="w-5 h-5" />
      case 'chat':
        return <MessageSquare className="w-5 h-5" />
      case 'embed':
        return <Code className="w-5 h-5" />
      default:
        return <Bot className="w-5 h-5" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Simple Navigation Header */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 bg-primary-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-semibold text-gray-900">ChatBot Builder</h1>
            </div>

            {/* User info and actions */}
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user?.email}
              </span>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={handleLogout}
                className="text-gray-600 hover:text-gray-900"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Welcome back, {user?.first_name || 'there'}!
          </h2>
          <p className="text-gray-600">
            Create and manage your chatbots. It's simple and takes just a few minutes.
          </p>
        </div>

        {/* Quick Start Card */}
        {chatbots.length === 0 && !loading && (
          <Card className="mb-8 bg-blue-50 border-blue-200">
            <CardContent className="p-6">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Bot className="w-6 h-6 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Get Started in 3 Simple Steps
                  </h3>
                  <ol className="space-y-2 text-sm text-gray-600">
                    <li className="flex items-start">
                      <span className="font-medium mr-2">1.</span>
                      <span>Create your chatbot with a name and description</span>
                    </li>
                    <li className="flex items-start">
                      <span className="font-medium mr-2">2.</span>
                      <span>Upload documents or add website URLs for your chatbot to learn from</span>
                    </li>
                    <li className="flex items-start">
                      <span className="font-medium mr-2">3.</span>
                      <span>Test your chatbot and get the code to add it to your website</span>
                    </li>
                  </ol>
                  <Button 
                    variant="primary"
                    className="mt-4"
                    onClick={handleCreateChatbot}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Your First Chatbot
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Chatbots Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-900">
              Your Chatbots
            </h3>
            {chatbots.length > 0 && (
              <Button 
                variant="primary"
                onClick={handleCreateChatbot}
              >
                <Plus className="w-4 h-4 mr-2" />
                Create New Chatbot
              </Button>
            )}
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner className="w-8 h-8" />
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <Card className="bg-red-50 border-red-200">
              <CardContent className="p-6">
                <p className="text-red-800">{error}</p>
                <Button 
                  variant="ghost" 
                  className="mt-4"
                  onClick={loadChatbots}
                >
                  Try Again
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Chatbots Grid */}
          {!loading && !error && chatbots.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {chatbots.map((chatbot) => (
                <Card key={chatbot.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                          <Bot className="w-5 h-5 text-primary-600" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{chatbot.name}</CardTitle>
                          <p className="text-sm text-gray-500 mt-1">
                            {chatbot.status === 'active' ? 'Active' : 'Setting up'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent className="space-y-4">
                    <p className="text-sm text-gray-600">
                      {chatbot.description || 'No description provided'}
                    </p>
                    
                    {/* Simple Stats */}
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <span className="flex items-center">
                        <MessageSquare className="w-4 h-4 mr-1" />
                        {chatbot.total_conversations || 0} chats
                      </span>
                      <span>
                        Created {new Date(chatbot.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="grid grid-cols-3 gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEditChatbot(chatbot)}
                        className="text-xs"
                      >
                        {getStepIcon('upload')}
                        <span className="ml-1">Content</span>
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => {
                          setSelectedChatbot(chatbot)
                          setShowChatTest(true)
                        }}
                        className="text-xs"
                      >
                        {getStepIcon('chat')}
                        <span className="ml-1">Test</span>
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => {
                          setSelectedChatbot(chatbot)
                          setShowEmbedCode(true)
                        }}
                        className="text-xs"
                      >
                        {getStepIcon('embed')}
                        <span className="ml-1">Embed</span>
                      </Button>
                    </div>
                    
                    {/* Management Actions */}
                    <div className="pt-3 border-t border-gray-100 flex justify-between">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEditChatbot(chatbot)}
                        className="text-primary-600 hover:text-primary-700"
                      >
                        Edit Settings
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleDeleteChatbot(chatbot)}
                        className="text-red-600 hover:text-red-700"
                      >
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Help Section */}
        <div className="mt-12 p-6 bg-gray-100 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-2">Need Help?</h4>
          <p className="text-sm text-gray-600 mb-3">
            Creating a chatbot is easy! Just click "Create New Chatbot" and follow the simple steps.
          </p>
          <div className="flex flex-wrap gap-4 text-sm">
            <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
              Quick Start Guide →
            </a>
            <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
              Video Tutorial →
            </a>
            <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
              Contact Support →
            </a>
          </div>
        </div>
      </main>
      
      {/* Modals */}
      {showWizard && (
        <ChatbotWizard
          isOpen={showWizard}
          onClose={() => {
            setShowWizard(false)
            setEditingChatbot(null)
          }}
          onSuccess={handleWizardSuccess}
          existingChatbot={editingChatbot}
        />
      )}
      
      <ChatbotDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onSuccess={() => {
          loadChatbots()
          setShowDeleteModal(false)
        }}
        chatbot={selectedChatbot}
      />
      
      {selectedChatbot && (
        <>
          <ChatTest
            chatbot={selectedChatbot}
            isOpen={showChatTest}
            onClose={() => {
              setShowChatTest(false)
              setSelectedChatbot(null)
            }}
          />
          
          <EmbedCodeModal
            chatbot={selectedChatbot}
            isOpen={showEmbedCode}
            onClose={() => {
              setShowEmbedCode(false)
              setSelectedChatbot(null)
            }}
          />
        </>
      )}
    </div>
  )
}