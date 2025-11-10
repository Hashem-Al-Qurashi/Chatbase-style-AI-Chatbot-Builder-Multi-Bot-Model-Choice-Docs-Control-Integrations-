import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Bot, 
  Plus, 
  MessageSquare, 
  LogOut,
  Search
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'
import { ChatbotWizard } from '../chatbot/ChatbotWizard'

export function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

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
      setError(err.message || 'Failed to load chatbots')
      setChatbots([])
    } finally {
      setLoading(false)
    }
  }

  const filteredChatbots = chatbots.filter(bot => 
    searchQuery ? (
      bot.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      bot.description.toLowerCase().includes(searchQuery.toLowerCase())
    ) : true
  )

  const handleCreateSuccess = () => {
    setShowCreateModal(false)
    loadChatbots()
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header - Chatbase Style */}
      <div className="border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-xl font-semibold text-gray-900">Chatbots</h1>
            </div>
            
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600">
                {user?.email}
              </span>
              <Button
                onClick={logout}
                variant="ghost"
                size="sm"
                className="text-gray-500 hover:text-gray-700"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Search and Create */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search chatbots..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          
          <Button
            onClick={() => setShowCreateModal(true)}
            className="bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-lg flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create Chatbot</span>
          </Button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center mx-auto mb-3">
                <Bot className="w-4 h-4 text-white animate-pulse" />
              </div>
              <p className="text-gray-600">Loading chatbots...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">{error}</p>
            <Button
              onClick={loadChatbots}
              variant="ghost"
              className="text-gray-600 hover:text-gray-800"
            >
              Try again
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredChatbots.length === 0 && chatbots.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Bot className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No chatbots yet</h3>
            <p className="text-gray-600 mb-6">Create your first chatbot to get started</p>
            <Button
              onClick={() => setShowCreateModal(true)}
              className="bg-gray-900 hover:bg-gray-800 text-white px-6 py-2 rounded-lg"
            >
              Create your first chatbot
            </Button>
          </div>
        )}

        {/* No Search Results */}
        {!loading && !error && filteredChatbots.length === 0 && chatbots.length > 0 && (
          <div className="text-center py-16">
            <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
            <p className="text-gray-600">Try adjusting your search query</p>
          </div>
        )}

        {/* Chatbots List - Minimal Style */}
        {!loading && filteredChatbots.length > 0 && (
          <div className="space-y-4">
            {filteredChatbots.map((chatbot) => (
              <div
                key={chatbot.id}
                className="border border-gray-200 rounded-lg p-6 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center">
                      <Bot className="w-6 h-6 text-white" />
                    </div>
                    
                    <div>
                      <h3 className="font-medium text-gray-900 text-lg">
                        {chatbot.name}
                      </h3>
                      <p className="text-gray-600 text-sm">
                        {chatbot.description || 'No description'}
                      </p>
                      <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                        <div className="flex items-center space-x-1">
                          <MessageSquare className="w-4 h-4" />
                          <span>{chatbot.total_conversations || 0} conversations</span>
                        </div>
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                          chatbot.status === 'active' 
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {chatbot.status}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Button
                      onClick={() => navigate(`/chat/${chatbot.id}`)}
                      className="bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-lg"
                    >
                      Chat
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      <ChatbotWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}