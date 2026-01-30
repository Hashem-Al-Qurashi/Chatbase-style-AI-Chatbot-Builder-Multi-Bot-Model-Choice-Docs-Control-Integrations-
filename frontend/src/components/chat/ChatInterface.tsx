import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  Send,
  Bot,
  User,
  Loader2,
  X,
  Minimize2,
  Paperclip,
  File,
  CheckCircle2,
  AlertCircle,
  Upload,
  ChevronDown,
  Menu,
  Sparkles
} from 'lucide-react'
import { apiService } from '../../services/api'
import { ChatSidebar } from './ChatSidebar'
import { Chatbot, Conversation, Message as ApiMessage } from '../../types'

// Animation variants for premium micro-interactions
const messageVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 30
    }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: 0.2 }
  }
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: Array<{
    id: string
    title: string
    url?: string
  }>
}

// API response can be array or paginated
interface PaginatedResponse<T> {
  results: T[]
  count?: number
  next?: string | null
  previous?: string | null
}

interface UploadedFile {
  id: string
  name: string
  size: number
  status: 'uploading' | 'success' | 'error'
  progress?: number
  error?: string
}

// ChatInterface can accept either full Chatbot or minimal props
type ChatbotProp = Chatbot | { id: string; name: string; description?: string }

interface ChatInterfaceProps {
  chatbot?: ChatbotProp
  onClose?: () => void
  isMinimized?: boolean
  onToggleMinimize?: () => void
}

export function ChatInterface({
  chatbot,
  onClose,
  isMinimized,
  onToggleMinimize
}: ChatInterfaceProps) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showFileUpload, setShowFileUpload] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set())
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [showSidebar, setShowSidebar] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (chatbot?.id) {
      loadConversationHistory()
    }
  }, [chatbot?.id])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadConversationHistory = async () => {
    if (!chatbot?.id) return

    try {
      setIsLoadingHistory(true)
      setError(null)

      const conversationsResponse = await apiService.getConversations(chatbot.id) as Conversation[] | PaginatedResponse<Conversation>
      const conversations: Conversation[] = Array.isArray(conversationsResponse)
        ? conversationsResponse
        : (conversationsResponse as PaginatedResponse<Conversation>).results || []

      if (conversations && conversations.length > 0) {
        const latestConversation = conversations[0]
        setCurrentConversationId(latestConversation.id)

        const conversationMessages = await apiService.getConversationMessages(latestConversation.id)

        if (conversationMessages && conversationMessages.length > 0) {
          const formattedMessages: ChatMessage[] = conversationMessages.map((msg: ApiMessage & { sources?: string[] }) => ({
            id: msg.id,
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            timestamp: new Date(msg.created_at),
            sources: (msg.sources || []).map((source, idx) => ({
              id: idx.toString(),
              title: typeof source === 'string' ? source : String(source),
              url: undefined
            }))
          }))

          setMessages(formattedMessages)
        } else {
          addWelcomeMessage()
        }
      } else {
        addWelcomeMessage()
      }
    } catch (err: any) {
      console.error('Failed to load conversation history:', err)
      setError('Failed to load conversation history')
      addWelcomeMessage()
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const addWelcomeMessage = () => {
    const welcomeMessage: ChatMessage = {
      id: 'welcome',
      role: 'assistant',
      content: `Hello! I'm ${chatbot?.name || 'your AI assistant'}. How can I help you today?`,
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !chatbot?.id) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiService.sendChatMessage(chatbot.id, {
        message: userMessage.content,
        conversation_id: currentConversationId || undefined
      })

      if (response.conversation_id && !currentConversationId) {
        setCurrentConversationId(response.conversation_id)
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response || 'No response generated',
        timestamp: new Date(),
        sources: response.sources?.map((source: any, index: number) => ({
          id: index.toString(),
          title: typeof source === 'string' ? source : String(source),
          url: undefined
        })) || []
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      console.error('Chat API error:', err)
      setError(err.message || 'Failed to send message. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleFileSelect = useCallback(async (files: FileList) => {
    if (!chatbot?.id) return

    const fileArray = Array.from(files)

    const newFiles: UploadedFile[] = fileArray.map(file => ({
      id: Date.now().toString() + Math.random().toString(36),
      name: file.name,
      size: file.size,
      status: 'uploading',
      progress: 0
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])

    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i]
      const uploadFile = newFiles[i]

      try {
        await apiService.uploadKnowledgeFile(chatbot.id, file, {
          name: file.name,
          is_citable: true
        })

        setUploadedFiles(prev =>
          prev.map(f =>
            f.id === uploadFile.id
              ? { ...f, status: 'success', progress: 100 }
              : f
          )
        )

        const successMessage: ChatMessage = {
          id: (Date.now() + i).toString(),
          role: 'assistant',
          content: t('chat.uploadSuccess', { name: file.name }),
          timestamp: new Date()
        }
        setMessages(prev => [...prev, successMessage])

      } catch (error: any) {
        console.error('File upload error:', error)

        setUploadedFiles(prev =>
          prev.map(f =>
            f.id === uploadFile.id
              ? { ...f, status: 'error', error: error.message || 'Upload failed' }
              : f
          )
        )

        const errorMessage: ChatMessage = {
          id: (Date.now() + i + 1000).toString(),
          role: 'assistant',
          content: t('chat.uploadError', { name: file.name, error: error.message || 'Upload failed' }),
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
      }
    }
  }, [chatbot?.id])

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files)
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files)
    }
  }, [handleFileSelect])

  const toggleSources = (messageId: string) => {
    setExpandedSources(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  if (isMinimized) {
    return (
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        className="fixed bottom-6 right-6 z-50"
      >
        <motion.button
          onClick={onToggleMinimize}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          animate={{
            boxShadow: [
              '0 0 20px rgba(139, 92, 246, 0.3)',
              '0 0 40px rgba(139, 92, 246, 0.5)',
              '0 0 20px rgba(139, 92, 246, 0.3)'
            ]
          }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 text-white shadow-2xl shadow-violet-500/40 flex items-center justify-center group overflow-hidden"
        >
          {/* Shimmer effect */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={{ x: ['-200%', '200%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
          <Bot className="w-7 h-7 relative z-10" />
          {/* Notification dot */}
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-slate-950 flex items-center justify-center">
            <span className="w-2 h-2 bg-emerald-300 rounded-full animate-ping" />
          </span>
        </motion.button>
      </motion.div>
    )
  }

  return (
    <div
      className={`relative flex flex-col h-full bg-slate-950 ${isDragOver ? 'ring-2 ring-violet-500/50' : ''
        }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Ambient Background Effects - Premium layered glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Primary violet glow - top left */}
        <motion.div
          className="absolute -top-20 -left-20 w-[500px] h-[500px] bg-violet-500/8 rounded-full blur-[120px]"
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.8, 1, 0.8],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        {/* Secondary fuchsia glow - bottom right */}
        <motion.div
          className="absolute -bottom-20 -right-20 w-[400px] h-[400px] bg-fuchsia-500/8 rounded-full blur-[100px]"
          animate={{
            scale: [1.1, 1, 1.1],
            opacity: [0.6, 0.9, 0.6],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
        />
        {/* Tertiary cyan accent - center */}
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-cyan-500/5 rounded-full blur-[150px]"
          animate={{
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        />
        {/* Subtle grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '60px 60px'
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 flex h-full">
        {/* Main Chat Area */}
        <div className="flex flex-col flex-1">
          {/* Header - Premium glass morphism */}
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-center justify-between px-5 py-4 border-b border-white/10 bg-gradient-to-r from-white/5 via-white/[0.07] to-white/5 backdrop-blur-xl"
          >
            <div className="flex items-center gap-4">
              {/* Animated bot avatar */}
              <motion.div
                whileHover={{ scale: 1.05, rotate: 5 }}
                className="relative w-12 h-12 bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 rounded-2xl flex items-center justify-center shadow-xl shadow-violet-500/30"
              >
                <Bot className="w-6 h-6 text-white" />
                {/* Status ring */}
                <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-slate-950 rounded-full flex items-center justify-center">
                  <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse" />
                </span>
              </motion.div>
              <div>
                <h2 className="font-semibold text-white text-lg tracking-tight">
                  {chatbot?.name || 'AI Assistant'}
                </h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                    {t('chat.online')}
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-xs text-slate-500">{t('chat.readyToHelp')}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <motion.button
                onClick={() => setShowSidebar(!showSidebar)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`p-2.5 rounded-xl transition-all duration-200 ${showSidebar
                  ? 'bg-violet-500/20 text-violet-400 ring-1 ring-violet-500/30'
                  : 'text-slate-500 hover:text-white hover:bg-white/10'
                  }`}
                title="Quick Actions"
              >
                <Menu className="w-5 h-5" />
              </motion.button>

              {onToggleMinimize && (
                <motion.button
                  onClick={onToggleMinimize}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="p-2.5 text-slate-500 hover:text-white hover:bg-white/10 rounded-xl transition-all duration-200"
                >
                  <Minimize2 className="w-5 h-5" />
                </motion.button>
              )}
              {onClose && (
                <motion.button
                  onClick={onClose}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="p-2.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all duration-200"
                >
                  <X className="w-5 h-5" />
                </motion.button>
              )}
            </div>
          </motion.div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {/* Loading History */}
              {isLoadingHistory && (
                <div className="flex items-center justify-center py-8">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
                    <span className="text-slate-500">{t('chat.loadingConversation')}</span>
                  </div>
                </div>
              )}

              {/* Messages */}
              <AnimatePresence mode="popLayout">
                {!isLoadingHistory && messages.map((message) => (
                  <motion.div
                    key={message.id}
                    variants={messageVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    layout
                    className={`flex items-start gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    {/* Avatar with hover effect */}
                    <motion.div
                      whileHover={{ scale: 1.1 }}
                      className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg ${message.role === 'user'
                        ? 'bg-gradient-to-br from-cyan-500 via-blue-500 to-cyan-600 shadow-cyan-500/25'
                        : 'bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 shadow-violet-500/25'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </motion.div>

                    {/* Message Content */}
                    <div className={`flex-1 max-w-[80%] ${message.role === 'user' ? 'text-right' : ''}`}>
                      <motion.div
                        whileHover={{ scale: 1.01 }}
                        className={`inline-block p-4 rounded-2xl relative overflow-hidden ${message.role === 'user'
                          ? 'bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 text-white shadow-lg shadow-violet-500/20'
                          : 'bg-white/[0.06] border border-white/10 text-slate-200 backdrop-blur-sm'
                        }`}
                      >
                        {/* Subtle inner glow for assistant messages */}
                        {message.role === 'assistant' && (
                          <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 via-transparent to-fuchsia-500/5 pointer-events-none" />
                        )}
                        <p className="whitespace-pre-wrap text-sm leading-relaxed relative z-10">
                          {message.content}
                        </p>
                      </motion.div>

                      {/* Sources - Enhanced */}
                      {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 0.3 }}
                          className="mt-2"
                        >
                          <motion.button
                            onClick={() => toggleSources(message.id)}
                            whileHover={{ scale: 1.02 }}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-violet-500/10 text-xs text-violet-400 hover:bg-violet-500/15 transition-colors"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>{t('chat.sources', { count: message.sources.length })}</span>
                            <motion.span
                              animate={{ rotate: expandedSources.has(message.id) ? 180 : 0 }}
                              transition={{ duration: 0.2 }}
                            >
                              <ChevronDown className="w-3 h-3" />
                            </motion.span>
                          </motion.button>

                          <AnimatePresence>
                            {expandedSources.has(message.id) && (
                              <motion.div
                                initial={{ opacity: 0, height: 0, y: -10 }}
                                animate={{ opacity: 1, height: 'auto', y: 0 }}
                                exit={{ opacity: 0, height: 0, y: -10 }}
                                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                                className="mt-2 p-3 bg-white/5 rounded-xl border border-white/10 backdrop-blur-sm"
                              >
                                <div className="space-y-2">
                                  {message.sources.map((source, idx) => (
                                    <motion.div
                                      key={source.id}
                                      initial={{ opacity: 0, x: -10 }}
                                      animate={{ opacity: 1, x: 0 }}
                                      transition={{ delay: idx * 0.05 }}
                                      className="flex items-start gap-2 text-xs group"
                                    >
                                      <div className="w-1.5 h-1.5 bg-gradient-to-r from-violet-400 to-fuchsia-400 rounded-full mt-1.5 flex-shrink-0 group-hover:scale-125 transition-transform" />
                                      <p className="text-slate-400 group-hover:text-slate-300 transition-colors">{source.title}</p>
                                    </motion.div>
                                  ))}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.div>
                      )}

                      <p className="text-[10px] text-slate-600 mt-2 font-medium">
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Loading Indicator - Premium thinking animation */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                  className="flex items-start gap-3"
                >
                  <motion.div
                    animate={{ rotate: [0, 10, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    className="w-9 h-9 bg-gradient-to-br from-violet-500 via-fuchsia-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/25"
                  >
                    <Bot className="w-4 h-4 text-white" />
                  </motion.div>
                  <div className="p-4 rounded-2xl bg-white/[0.06] border border-white/10 backdrop-blur-sm">
                    <div className="flex items-center gap-3">
                      {/* Animated thinking dots */}
                      <div className="flex gap-1.5">
                        {[0, 1, 2].map((i) => (
                          <motion.div
                            key={i}
                            className="w-2.5 h-2.5 rounded-full bg-gradient-to-r from-violet-400 to-fuchsia-400"
                            animate={{
                              y: [-2, 2, -2],
                              opacity: [0.5, 1, 0.5],
                              scale: [0.9, 1.1, 0.9],
                            }}
                            transition={{
                              duration: 0.8,
                              repeat: Infinity,
                              delay: i * 0.15,
                              ease: 'easeInOut',
                            }}
                          />
                        ))}
                      </div>
                      <span className="text-sm text-slate-400 font-medium">
                        <motion.span
                          animate={{ opacity: [1, 0.5, 1] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        >
                          {t('chat.thinking')}
                        </motion.span>
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* File Upload Area */}
          <AnimatePresence>
            {showFileUpload && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="border-t border-white/10 p-4 bg-white/5"
              >
                <div
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${isDragOver
                      ? 'border-violet-500 bg-violet-500/10'
                      : 'border-white/20 hover:border-violet-500/50 bg-white/5'
                    }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragOver ? 'text-violet-400' : 'text-slate-500'}`} />
                  <p className="text-sm text-slate-400 mb-1">
                    {t('chat.dropFiles')} <span className="text-violet-400 font-medium">{t('chat.browse')}</span>
                  </p>
                  <p className="text-xs text-slate-600">{t('chat.supportedFiles')}</p>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.md"
                  onChange={handleFileInputChange}
                  className="hidden"
                />

                {uploadedFiles.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {uploadedFiles.map((file) => (
                      <div key={file.id} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/10">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${file.status === 'success' ? 'bg-emerald-500/20' :
                              file.status === 'error' ? 'bg-rose-500/20' : 'bg-violet-500/20'
                            }`}>
                            {file.status === 'success' ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            ) : file.status === 'error' ? (
                              <AlertCircle className="w-4 h-4 text-rose-400" />
                            ) : (
                              <File className="w-4 h-4 text-violet-400" />
                            )}
                          </div>

                          <div>
                            <p className="text-sm font-medium text-white">{file.name}</p>
                            <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
                          </div>
                        </div>

                        {file.status === 'uploading' && (
                          <span className="text-xs text-violet-400">{file.progress}%</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Input Area - Premium glass morphism */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="p-4 border-t border-white/10 bg-gradient-to-t from-slate-950 via-slate-950/95 to-transparent backdrop-blur-xl"
          >
            <div className="max-w-3xl mx-auto">
              <form onSubmit={handleSubmit}>
                <div className="flex items-end gap-3">
                  <motion.button
                    type="button"
                    onClick={() => setShowFileUpload(!showFileUpload)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`p-3 rounded-xl transition-all duration-200 ${showFileUpload
                        ? 'bg-violet-500/20 text-violet-400 ring-1 ring-violet-500/30'
                        : 'bg-white/5 text-slate-500 hover:text-white hover:bg-white/10 border border-white/10'
                      }`}
                  >
                    <Paperclip className="w-5 h-5" />
                  </motion.button>

                  <div className="flex-1 relative group">
                    {/* Input glow effect on focus */}
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-500/0 via-violet-500/0 to-fuchsia-500/0 rounded-xl blur opacity-0 group-focus-within:opacity-50 group-focus-within:from-violet-500/30 group-focus-within:to-fuchsia-500/30 transition-all duration-300" />
                    <input
                      type="text"
                      placeholder={t('chat.placeholder')}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      disabled={isLoading}
                      className="relative w-full px-5 py-3.5 pr-14 rtl:pr-5 rtl:pl-14 rounded-xl bg-white/[0.06] border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/[0.08] transition-all duration-200 disabled:opacity-50"
                    />

                    <motion.button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      whileHover={{ scale: input.trim() && !isLoading ? 1.05 : 1 }}
                      whileTap={{ scale: input.trim() && !isLoading ? 0.95 : 1 }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-violet-600 text-white rounded-lg shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 disabled:opacity-30 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </motion.button>
                  </div>
                </div>
              </form>

              <div className="flex items-center justify-center gap-2 mt-3">
                <div className="w-1 h-1 rounded-full bg-slate-700" />
                <p className="text-[10px] text-slate-600 font-medium">
                  {t('chat.aiDisclaimer')}
                </p>
                <div className="w-1 h-1 rounded-full bg-slate-700" />
              </div>
            </div>
          </motion.div>
        </div>

        {/* Sidebar */}
        {chatbot && (
          <ChatSidebar
            isOpen={showSidebar}
            onClose={() => setShowSidebar(false)}
            chatbot={chatbot}
            onChatbotUpdate={() => {
              console.log('Chatbot updated via sidebar')
            }}
          />
        )}
      </div>

      {/* Drag Overlay */}
      <AnimatePresence>
        {isDragOver && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/90 flex items-center justify-center z-50"
          >
            <div className="bg-white/5 rounded-2xl p-8 border-2 border-dashed border-violet-500 text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Upload className="w-8 h-8 text-white" />
              </div>
              <p className="font-semibold text-white mb-1">{t('chat.dropFiles')}</p>
              <p className="text-sm text-slate-400">{t('knowledge.subtitle')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-20 left-4 right-4 z-50"
          >
            <div className="max-w-3xl mx-auto p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400" />
                <p className="text-sm text-rose-400">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="p-1 text-rose-400 hover:text-rose-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
