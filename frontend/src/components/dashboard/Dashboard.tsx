import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Bot, 
  Plus, 
  MessageSquare, 
  LogOut,
  Search,
  Code
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'
import { ChatbotWizard } from '../chatbot/ChatbotWizard'
import { ChatbotDetailsModal } from '../chatbot/ChatbotDetailsModal'

export function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedChatbot, setSelectedChatbot] = useState<Chatbot | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [userPlan, setUserPlan] = useState<any>(null)
  const [planLoading, setPlanLoading] = useState(true)

  useEffect(() => {
    loadChatbots()
    loadUserPlan()
    
    // Check for pending upgrade after login
    import('../../services/checkout').then(({ checkoutService }) => {
      checkoutService.checkPendingUpgrade()
    })
  }, [])

  const loadUserPlan = async () => {
    try {
      setPlanLoading(true)
      const response = await apiService.get('/billing/current_plan/')
      // API returns data directly, not wrapped in data property
      setUserPlan(response.plan || response.data?.plan)
    } catch (error) {
      console.error('Failed to load user plan:', error)
      // Set default plan info if API fails
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

  const handleChatbotClick = (chatbot: Chatbot) => {
    navigate(`/chat/${chatbot.id}`)
  }

  const handleEmbedClick = (e: React.MouseEvent, chatbot: Chatbot) => {
    e.stopPropagation() // Prevent triggering the main card click
    setSelectedChatbot(chatbot)
    setShowDetailsModal(true)
  }

  const handleCloseDetailsModal = () => {
    setShowDetailsModal(false)
    setSelectedChatbot(null)
  }

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
    <div className="min-h-screen relative overflow-hidden">
      {/* Beautiful Background with Dotted Texture */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-100" />
      <div 
        className="absolute inset-0 bg-dot-pattern opacity-60"
        style={{
          backgroundSize: '24px 24px'
        }}
      />
      
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-gradient-to-br from-primary-400/20 to-accent-400/20 rounded-full blur-3xl animate-float" />
        <div className="absolute -top-20 -right-40 w-96 h-96 bg-gradient-to-br from-accent-400/15 to-primary-400/15 rounded-full blur-3xl animate-float" style={{animationDelay: '2s'}} />
        <div className="absolute -bottom-40 -left-20 w-96 h-96 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-float" style={{animationDelay: '4s'}} />
        <div className="absolute top-1/4 right-1/4 w-32 h-32 bg-gradient-to-br from-accent-300/20 to-primary-300/20 rounded-full blur-2xl animate-pulse-gentle" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen">
        <div className="container mx-auto px-4 py-8">
          {/* Soft Header */}
          <div className="flex items-center justify-between mb-12">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold gradient-text-elegant">Your Chatbots</h1>
                <p className="text-gray-600">Welcome back, {user?.first_name || user?.email}</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Plan and Credit Display */}
              {(userPlan || planLoading) && (
                <div className="bg-white/80 backdrop-blur-sm rounded-xl px-4 py-3 shadow-soft border border-white/20" data-testid="plan-info">
                  <div className="text-center">
                    <div className="text-sm font-medium text-gray-600">Current Plan</div>
                    <div className="text-lg font-bold text-gray-900 capitalize" data-testid="plan-name">
                      {planLoading ? 'Loading...' : (userPlan?.tier || 'free')}
                    </div>
                  </div>
                  <div className="text-center mt-2">
                    <div className="text-sm text-gray-600">Credits</div>
                    <div className="text-lg font-bold text-blue-600" data-testid="credits-remaining">
                      {planLoading ? '...' : (userPlan?.credits_remaining || 50)}
                    </div>
                    <div className="text-xs text-gray-500" data-testid="credits-total">
                      of {planLoading ? '...' : (userPlan?.message_credits || 50)}
                    </div>
                  </div>
                  {userPlan && userPlan.credits_remaining < 10 && (
                    <div className="mt-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => navigate('/#pricing')}
                        className="text-xs"
                      >
                        Upgrade
                      </Button>
                    </div>
                  )}
                </div>
              )}
              
              <button
                onClick={logout}
                className="text-gray-500 hover:text-gray-700 p-2 rounded-lg hover:bg-white/50 transition-colors"
                data-testid="logout-button"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Soft Controls */}
          <div className="max-w-4xl mx-auto mb-8">
            <div className="flex items-center justify-between">
              <div className="flex-1 max-w-md">
                <Input
                  type="text"
                  placeholder="Search chatbots..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-white/50 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 shadow-soft placeholder-gray-500"
                />
              </div>
              
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 text-white px-6 py-3 rounded-xl shadow-lg shadow-primary-500/25 transition-all duration-200 flex items-center space-x-2"
                data-testid="new-chatbot-button"
              >
                <Plus className="w-5 h-5" />
                <span>Create Chatbot</span>
              </button>
            </div>
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

          {/* Beautiful Empty State */}
          {!loading && !error && filteredChatbots.length === 0 && chatbots.length === 0 && (
            <div className="max-w-4xl mx-auto">
              <div className="text-center py-16">
                <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-primary-500/25">
                  <Bot className="w-10 h-10 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Create Your First Chatbot</h3>
                <p className="text-gray-600 mb-8 max-w-md mx-auto">
                  Transform your customer support with an intelligent AI assistant that learns from your content
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 text-white px-8 py-4 rounded-xl shadow-lg shadow-primary-500/25 transition-all duration-200 font-medium"
                  data-testid="new-chatbot-button"
                >
                  Get Started
                </button>
              </div>
            </div>
          )}

          {/* No Search Results */}
          {!loading && !error && filteredChatbots.length === 0 && chatbots.length > 0 && (
            <div className="max-w-4xl mx-auto">
              <div className="text-center py-16">
                <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
                <p className="text-gray-600">Try adjusting your search query</p>
              </div>
            </div>
          )}

          {/* Soft Chatbot Cards */}
          {!loading && filteredChatbots.length > 0 && (
            <div className="max-w-4xl mx-auto">
              <div className="grid gap-6">
                {filteredChatbots.map((chatbot) => (
                  <div
                    key={chatbot.id}
                    onClick={() => handleChatbotClick(chatbot)}
                    className="bg-white/50 backdrop-blur-sm rounded-2xl p-6 shadow-soft hover:shadow-elegant hover:bg-white/70 transition-all duration-300 cursor-pointer group relative"
                  >
                    {/* Embed Button - Top Right */}
                    <button
                      onClick={(e) => handleEmbedClick(e, chatbot)}
                      className="absolute top-4 right-4 p-2 rounded-lg bg-white/80 hover:bg-white shadow-sm hover:shadow-md transition-all duration-200 text-gray-600 hover:text-primary-600 group-hover:opacity-100 opacity-70"
                      title="Get Embed Code"
                    >
                      <Code className="w-4 h-4" />
                    </button>

                    <div className="flex items-center space-x-4 pr-12"> {/* Added right padding for embed button */}
                      <div className="w-14 h-14 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25 group-hover:shadow-primary-500/40 transition-shadow">
                        <Bot className="w-7 h-7 text-white" />
                      </div>
                      
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-lg group-hover:text-primary-700 transition-colors">
                          {chatbot.name}
                        </h3>
                        <p className="text-gray-600">
                          {chatbot.description || 'Ready to chat'}
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <MessageSquare className="w-4 h-4" />
                            <span>{chatbot.total_conversations || 0} conversations</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      <ChatbotWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => {
          setShowCreateModal(false)
          loadChatbots()
        }}
      />

      {/* Chatbot Details Modal */}
      <ChatbotDetailsModal
        isOpen={showDetailsModal}
        onClose={handleCloseDetailsModal}
        chatbot={selectedChatbot}
        onChatbotUpdated={loadChatbots}
      />
    </div>
  )
}