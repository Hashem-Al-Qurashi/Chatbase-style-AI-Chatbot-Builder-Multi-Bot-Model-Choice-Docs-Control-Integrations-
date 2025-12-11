import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Bot } from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { LoadingSpinner } from '../ui/LoadingSpinner'

interface Message {
  id: string
  content: string
  sender: 'user' | 'bot'
  timestamp: Date
  citations?: string[]
}

interface WidgetConfig {
  id: string
  name: string
  description: string
  welcome_message?: string
  theme?: {
    primary_color?: string
    background_color?: string
    text_color?: string
  }
}

export function StandaloneWidget() {
  const { slug } = useParams<{ slug: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [config, setConfig] = useState<WidgetConfig | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load widget configuration
  useEffect(() => {
    if (!slug) {
      setError('Chatbot slug is required')
      setIsLoading(false)
      return
    }

    loadWidgetConfig()
  }, [slug])

  // Add welcome message when config loads
  useEffect(() => {
    if (config && messages.length === 0) {
      const welcomeMessage = config.welcome_message || `Hi! I'm ${config.name}. How can I help you today?`
      setMessages([{
        id: 'welcome',
        content: welcomeMessage,
        sender: 'bot',
        timestamp: new Date()
      }])
    }
  }, [config])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const loadWidgetConfig = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`/api/v1/widget/config/${slug}/`)
      
      if (!response.ok) {
        throw new Error(`Failed to load chatbot configuration: ${response.status}`)
      }
      
      const configData = await response.json()
      setConfig(configData)
      setError(null)
    } catch (err: any) {
      console.error('Failed to load widget config:', err)
      setError(err.message || 'Failed to load chatbot configuration')
    } finally {
      setIsLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || isSending || !slug) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsSending(true)
    setIsTyping(true)

    try {
      const response = await fetch(`/api/v1/widget/chat/${slug}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.status}`)
      }

      const data = await response.json()
      
      // Update conversation ID if provided
      if (data.conversation_id) {
        setConversationId(data.conversation_id)
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response || data.message || 'Sorry, I could not process your request.',
        sender: 'bot',
        timestamp: new Date(),
        citations: data.sources || data.citations
      }

      setMessages(prev => [...prev, botMessage])
      setError(null)
    } catch (err: any) {
      console.error('Failed to send message:', err)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsSending(false)
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="flex flex-col items-center space-y-4">
          <LoadingSpinner />
          <p className="text-gray-600">Loading chatbot...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center p-8">
          <div className="text-red-500 mb-4">
            <Bot size={48} className="mx-auto" />
          </div>
          <h1 className="text-xl font-semibold text-gray-800 mb-2">Chatbot Unavailable</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    )
  }

  const primaryColor = config?.theme?.primary_color || '#007bff'
  const backgroundColor = config?.theme?.background_color || '#ffffff'
  const textColor = config?.theme?.text_color || '#333333'

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor, color: textColor }}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 text-white shadow-sm"
        style={{ backgroundColor: primaryColor }}
      >
        <div className="flex items-center space-x-3">
          <Bot size={24} />
          <div>
            <h1 className="font-semibold">{config?.name || 'Chatbot'}</h1>
            <p className="text-sm opacity-90">Online</p>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.sender === 'user'
                  ? 'text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
              style={
                message.sender === 'user'
                  ? { backgroundColor: primaryColor }
                  : undefined
              }
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {message.citations && message.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 border-opacity-30">
                  <p className="text-xs opacity-75">
                    Sources: {message.citations.join(', ')}
                  </p>
                </div>
              )}
              <p className="text-xs mt-1 opacity-75">
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                </div>
                <span className="text-sm text-gray-500">AI is typing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <Input
            type="text"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isSending}
            className="flex-1"
          />
          <Button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isSending}
            style={{ backgroundColor: primaryColor }}
            className="px-4 py-2 text-white rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {isSending ? <LoadingSpinner className="w-4 h-4" /> : <Send size={16} />}
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-2 text-xs text-gray-500 border-t border-gray-200">
        Powered by Chatbot SaaS
      </div>
    </div>
  )
}