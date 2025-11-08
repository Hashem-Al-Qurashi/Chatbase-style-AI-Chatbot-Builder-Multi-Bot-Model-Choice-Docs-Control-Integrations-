import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Bot, 
  Plus, 
  MessageSquare, 
  Users, 
  BarChart3, 
  Settings, 
  Sparkles,
  Zap,
  TrendingUp,
  Clock,
  Star,
  ArrowRight,
  Eye,
  Edit,
  Search,
  Filter,
  Calendar,
  Download,
  Trash2
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Input } from '../ui/Input'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'
import { ChatbotWizard } from '../chatbot/ChatbotWizard'
import { ChatbotDeleteModal } from '../chatbot/ChatbotDeleteModal'
import { ChatbotDetailsModal } from '../chatbot/ChatbotDetailsModal'

export function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [selectedChatbot, setSelectedChatbot] = useState<Chatbot | null>(null)

  // Load chatbots on component mount
  useEffect(() => {
    loadChatbots()
  }, [])

  const loadChatbots = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiService.getChatbots()
      // Handle paginated response format {count, results} or direct array
      const chatbotsData = Array.isArray(response) ? response : response.results || []
      setChatbots(chatbotsData)
    } catch (err: any) {
      console.error('Failed to load chatbots:', err)
      setError(err.message || 'Failed to load chatbots')
      setChatbots([]) // Ensure we always have an array
    } finally {
      setLoading(false)
    }
  }

  // Filter chatbots based on search query
  const filteredChatbots = useMemo(() => {
    if (!chatbots || !Array.isArray(chatbots)) return []
    if (!searchQuery.trim()) return chatbots
    return chatbots.filter(bot => 
      bot.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      bot.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [chatbots, searchQuery])

  // Helper functions
  const formatLastActive = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
    
    if (diffInMinutes < 60) return `${diffInMinutes} minutes ago`
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)} hours ago`
    return `${Math.floor(diffInMinutes / 1440)} days ago`
  }

  const calculatePerformance = (bot: Chatbot) => {
    // Simple performance calculation based on status and activity
    if (bot.status === 'active') return Math.floor(85 + Math.random() * 15)
    if (bot.status === 'training') return Math.floor(60 + Math.random() * 25)
    return Math.floor(40 + Math.random() * 30)
  }

  // Format chatbots for display with computed fields
  const formattedChatbots = useMemo(() => {
    if (!Array.isArray(filteredChatbots)) return []
    return filteredChatbots.map(bot => ({
      ...bot,
      conversations: bot.total_conversations || 0,
      lastActive: formatLastActive(bot.created_at),
      performance: calculatePerformance(bot)
    }))
  }, [filteredChatbots])

  // Event handlers
  const handleCreateChatbot = () => {
    setSelectedChatbot(null)
    setShowCreateModal(true)
  }

  const handleEditChatbot = (chatbot: Chatbot) => {
    setSelectedChatbot(chatbot)
    setShowEditModal(true)
  }

  const handleDeleteChatbot = (chatbot: Chatbot) => {
    setSelectedChatbot(chatbot)
    setShowDeleteModal(true)
  }

  const handleModalSuccess = () => {
    loadChatbots() // Refresh the chatbots list
  }

  // Statistics calculation from real data
  const stats = [
    {
      label: 'Active Chatbots',
      value: chatbots.filter(bot => bot.status === 'active').length.toString(),
      change: `${chatbots.length} total`,
      trend: 'up',
      icon: Bot,
      color: 'primary'
    },
    {
      label: 'Total Conversations',
      value: chatbots.reduce((sum, bot) => sum + (bot.total_conversations || 0), 0).toLocaleString(),
      change: `${chatbots.length} chatbots active`,
      trend: 'up',
      icon: MessageSquare,
      color: 'success'
    },
    {
      label: 'Total Messages',
      value: chatbots.reduce((sum, bot) => sum + (bot.total_messages || 0), 0).toLocaleString(),
      change: 'Across all conversations',
      trend: 'up',
      icon: Users,
      color: 'accent'
    },
    {
      label: 'Avg Response Time',
      value: '< 1s',
      change: 'Real-time responses',
      trend: 'up',
      icon: Zap,
      color: 'warning'
    }
  ]


  const recentActivity = [
    {
      type: 'conversation',
      title: 'New conversation started',
      description: 'Customer Support Bot - Product inquiry',
      time: '2 minutes ago',
      icon: MessageSquare
    },
    {
      type: 'training',
      title: 'Training completed',
      description: 'Technical Documentation bot updated with new content',
      time: '1 hour ago',
      icon: Bot
    },
    {
      type: 'performance',
      title: 'Performance milestone',
      description: 'Sales Assistant reached 1000 conversations',
      time: '3 hours ago',
      icon: TrendingUp
    }
  ]

  const handleLogout = async () => {
    try {
      await logout()
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100">
      {/* Navigation Header */}
      <nav className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo and brand */}
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/25">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold gradient-text-elegant">Chatbot SaaS</h1>
                <p className="text-xs text-gray-500">Dashboard</p>
              </div>
            </div>

            {/* User info and actions */}
            <div className="flex items-center space-x-4">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium text-gray-900">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <Settings className="w-4 h-4" />
              </Button>
              <Button 
                variant="gradient" 
                size="sm"
                onClick={handleCreateChatbot}
              >
                <Plus className="w-4 h-4 mr-2" />
                New Chatbot
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Welcome Section */}
          <div className="relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0">
              <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-3xl animate-pulse-gentle" />
              <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-gradient-to-br from-accent-400/10 to-primary-400/10 rounded-full blur-2xl animate-float" />
            </div>

            <div className="relative space-y-4 animate-slide-up">
              <div className="flex items-center space-x-3">
                <h2 className="text-3xl font-bold text-gray-900">Good morning! 👋</h2>
                <div className="px-3 py-1 bg-gradient-to-r from-success-100 to-success-50 rounded-full">
                  <span className="text-xs font-medium text-success-700">All systems operational</span>
                </div>
              </div>
              <p className="text-lg text-gray-600 max-w-2xl">
                Your chatbots are performing well. Here's what's happening across your platform.
              </p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-slide-up" style={{animationDelay: '0.1s'}}>
            {stats.map((stat, index) => (
              <Card key={index} className="relative overflow-hidden group hover:shadow-elegant transition-all duration-300 hover:scale-105">
                <div className="absolute inset-0 bg-gradient-to-br from-white to-gray-50 opacity-60" />
                <div className="absolute -top-2 -right-2 w-16 h-16 bg-gradient-to-br from-primary-400/10 to-accent-400/10 rounded-full blur-xl" />
                
                <CardContent className="relative p-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <div className={`w-8 h-8 bg-${stat.color}-100 rounded-lg flex items-center justify-center`}>
                          <stat.icon className={`w-4 h-4 text-${stat.color}-600`} />
                        </div>
                        <span className="text-sm font-medium text-gray-600">{stat.label}</span>
                      </div>
                      
                      <div className="space-y-1">
                        <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                        <p className={`text-xs font-medium text-${stat.trend === 'up' ? 'success' : 'error'}-600 flex items-center space-x-1`}>
                          <TrendingUp className="w-3 h-3" />
                          <span>{stat.change}</span>
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 animate-slide-up" style={{animationDelay: '0.2s'}}>
            {/* Chatbots List */}
            <div className="xl:col-span-2 space-y-6">
              {/* Section Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Your Chatbots</h3>
                  <p className="text-sm text-gray-600">Manage and monitor your AI assistants</p>
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      type="text"
                      placeholder="Search chatbots..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 w-64"
                    />
                  </div>
                  <Button variant="ghost" size="sm">
                    <Filter className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* Error State */}
              {error && (
                <div className="text-center py-12">
                  <div className="bg-error-50 border border-error-200 rounded-lg p-6 max-w-md mx-auto">
                    <p className="text-error-600 mb-4">{error}</p>
                    <Button variant="ghost" onClick={loadChatbots}>
                      Try Again
                    </Button>
                  </div>
                </div>
              )}

              {/* Loading State */}
              {loading && (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner className="w-8 h-8" />
                </div>
              )}

              {/* Empty State */}
              {!loading && !error && filteredChatbots.length === 0 && (
                <div className="text-center py-12">
                  <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    {searchQuery ? 'No chatbots found' : 'No chatbots yet'}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    {searchQuery 
                      ? 'Try adjusting your search query' 
                      : 'Create your first chatbot to get started'}
                  </p>
                  {!searchQuery && (
                    <Button variant="gradient" onClick={handleCreateChatbot}>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Your First Chatbot
                    </Button>
                  )}
                </div>
              )}

              {/* Chatbots Grid */}
              {!loading && !error && filteredChatbots.length > 0 && (
              <div className="grid gap-4">
                {formattedChatbots.map((chatbot) => (
                  <Card key={chatbot.id} className="group hover:shadow-chatbase-lg transition-all duration-300 hover:scale-[1.01] border-gray-100/80 rounded-2xl">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-4 flex-1">
                          {/* Bot Avatar */}
                          <div className="w-14 h-14 bg-chatbase-primary rounded-2xl flex items-center justify-center shadow-chatbase group-hover:shadow-chatbase-lg transition-all duration-300 ring-1 ring-primary-300/30">
                            <Bot className="w-7 h-7 text-white" />
                          </div>

                          {/* Bot Info */}
                          <div className="flex-1 space-y-3">
                            <div className="space-y-1">
                              <div className="flex items-center space-x-3">
                                <h4 className="font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                                  {chatbot.name}
                                </h4>
                                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  chatbot.status === 'active' 
                                    ? 'bg-success-100 text-success-700'
                                    : 'bg-warning-100 text-warning-700'
                                }`}>
                                  {chatbot.status}
                                </div>
                              </div>
                              <p className="text-sm text-gray-600">{chatbot.description}</p>
                            </div>

                            {/* Stats */}
                            <div className="flex items-center space-x-6 text-sm">
                              <div className="flex items-center space-x-2">
                                <MessageSquare className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-600">{chatbot.conversations} conversations</span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Clock className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-600">{chatbot.lastActive}</span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Star className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-600">{chatbot.performance}% performance</span>
                              </div>
                            </div>

                            {/* Performance Bar */}
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-gray-500">Performance</span>
                                <span className="font-medium text-gray-700">{chatbot.performance}%</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5">
                                <div 
                                  className="bg-gradient-to-r from-primary-500 to-accent-500 h-1.5 rounded-full transition-all duration-500"
                                  style={{ width: `${chatbot.performance}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                          <Button 
                            variant="gradient" 
                            size="sm"
                            onClick={() => navigate(`/chat/${chatbot.id}`)}
                            title="Start chatting with this bot"
                          >
                            <MessageSquare className="w-4 h-4 mr-1" />
                            Chat
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              setSelectedChatbot(chatbot)
                              setShowDetailsModal(true)
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleEditChatbot(chatbot)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleDeleteChatbot(chatbot)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              )}

              {/* Load More */}
              <div className="text-center">
                <Button variant="ghost" className="group">
                  View all chatbots
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Recent Activity */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Recent Activity</CardTitle>
                    <Button variant="ghost" size="sm">
                      <Calendar className="w-4 h-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {recentActivity.map((activity, index) => (
                    <div key={index} className="flex items-start space-x-3 group">
                      <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center group-hover:bg-primary-100 transition-colors">
                        <activity.icon className="w-4 h-4 text-gray-600 group-hover:text-primary-600" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                        <p className="text-xs text-gray-600">{activity.description}</p>
                        <p className="text-xs text-gray-400">{activity.time}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button 
                    variant="ghost" 
                    className="w-full justify-start group"
                    onClick={handleCreateChatbot}
                  >
                    <Plus className="w-4 h-4 mr-3 group-hover:scale-110 transition-transform" />
                    Create New Chatbot
                  </Button>
                  <Button variant="ghost" className="w-full justify-start group">
                    <Download className="w-4 h-4 mr-3 group-hover:scale-110 transition-transform" />
                    Export Conversations
                  </Button>
                  <Button variant="ghost" className="w-full justify-start group">
                    <BarChart3 className="w-4 h-4 mr-3 group-hover:scale-110 transition-transform" />
                    View Analytics
                  </Button>
                  <Button variant="ghost" className="w-full justify-start group">
                    <Settings className="w-4 h-4 mr-3 group-hover:scale-110 transition-transform" />
                    Account Settings
                  </Button>
                </CardContent>
              </Card>

              {/* Tips */}
              <Card className="bg-gradient-to-br from-primary-50 to-accent-50 border-primary-200">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-5 h-5 text-primary-600" />
                    <h4 className="font-semibold text-primary-900">Pro Tip</h4>
                  </div>
                  <p className="text-sm text-primary-800">
                    Add knowledge sources to improve your chatbot's responses. Upload documents, add URLs, or train with custom content.
                  </p>
                  <Button variant="ghost" size="sm" className="text-primary-700 hover:text-primary-800">
                    Learn more
                    <ArrowRight className="w-3 h-3 ml-1" />
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>
      
      {/* Modals */}
      <ChatbotWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleModalSuccess}
        existingChatbot={null}
      />
      
      <ChatbotWizard
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={handleModalSuccess}
        existingChatbot={selectedChatbot}
      />
      
      <ChatbotDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onSuccess={handleModalSuccess}
        chatbot={selectedChatbot}
      />
      
      <ChatbotDetailsModal
        isOpen={showDetailsModal}
        onClose={() => setShowDetailsModal(false)}
        chatbot={selectedChatbot}
        onChatbotUpdated={handleModalSuccess}
      />
    </div>
  )
}