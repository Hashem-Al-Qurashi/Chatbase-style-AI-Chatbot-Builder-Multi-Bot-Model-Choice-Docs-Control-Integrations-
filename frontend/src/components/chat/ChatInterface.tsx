import React, { useState, useRef, useEffect, useCallback } from 'react'
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
  Plus
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { apiService } from '../../services/api'

interface Message {
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

interface UploadedFile {
  id: string
  name: string
  size: number
  status: 'uploading' | 'success' | 'error'
  progress?: number
  error?: string
}

interface ChatInterfaceProps {
  chatbot?: {
    id: string
    name: string
    description?: string
  }
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
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello! I'm ${chatbot?.name || 'your AI assistant'}. How can I help you today?`,
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showFileUpload, setShowFileUpload] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !chatbot?.id) return

    const userMessage: Message = {
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
        message: userMessage.content
      })
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response || 'No response generated',
        timestamp: new Date(),
        sources: response.sources?.map((source, index) => ({
          id: index.toString(),
          title: source,
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
        
        const successMessage: Message = {
          id: (Date.now() + i).toString(),
          role: 'assistant',
          content: `✅ Successfully uploaded "${file.name}". The document has been processed and is now available for questions!`,
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
        
        const errorMessage: Message = {
          id: (Date.now() + i + 1000).toString(),
          role: 'assistant', 
          content: `❌ Failed to upload "${file.name}": ${error.message || 'Upload failed'}`,
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

  if (isMinimized) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={onToggleMinimize}
          className="w-14 h-14 rounded-full bg-gray-900 hover:bg-gray-800 text-white shadow-lg"
        >
          <Bot className="w-6 h-6" />
        </Button>
      </div>
    )
  }

  return (
    <div 
      className={`relative flex flex-col h-full ${
        isDragOver ? 'bg-blue-50/30' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Modern Background with Journal Texture */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-gray-100" />
      <div 
        className="absolute inset-0 bg-dot-pattern opacity-50"
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
      <div className="relative z-10 flex flex-col h-full">
        {/* Chatbase-style Header - Very Minimal */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <span className="font-medium text-gray-900">
            {chatbot?.name || 'AI Assistant'}
          </span>
        </div>
        
        <div className="flex items-center space-x-1">
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Minimize2 className="w-4 h-4 text-gray-500" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          )}
        </div>
        </div>

        {/* Messages - ChatGPT-like Layout */}
        <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={`flex items-start space-x-4 ${
                message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === 'user' 
                  ? 'bg-blue-500'
                  : 'bg-gray-900'
              }`}>
                {message.role === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>

              {/* Message Content */}
              <div className="flex-1 max-w-2xl">
                <div className={`p-4 rounded-lg ${
                  message.role === 'user' 
                    ? 'bg-blue-50 ml-12' 
                    : 'bg-gray-50'
                }`}>
                  <p className="text-gray-800 whitespace-pre-wrap">
                    {message.content}
                  </p>
                  
                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-600 mb-1">Sources:</p>
                      {message.sources.map((source) => (
                        <div key={source.id} className="text-xs text-gray-500 mb-1">
                          {source.title}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                
                <div className="text-xs text-gray-400 mt-1 px-4">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1 max-w-2xl">
                <div className="p-4 rounded-lg bg-gray-50">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                    <span className="text-gray-600 text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
        </div>

        {/* File Upload Area */}
        {showFileUpload && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div 
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragOver 
                ? 'border-blue-300 bg-blue-50' 
                : 'border-gray-300 hover:border-blue-300'
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
            <p className="text-sm text-gray-600 mb-1">
              Drop files here or <span className="text-blue-500 cursor-pointer font-medium">browse</span>
            </p>
            <p className="text-xs text-gray-500">PDF, DOC, TXT files supported</p>
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
                <div key={file.id} className="flex items-center justify-between p-3 bg-white rounded-lg border">
                  <div className="flex items-center space-x-3">
                    <div className={`w-6 h-6 rounded flex items-center justify-center ${
                      file.status === 'success' ? 'bg-green-100' : 
                      file.status === 'error' ? 'bg-red-100' : 'bg-blue-100'
                    }`}>
                      {file.status === 'success' ? (
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                      ) : file.status === 'error' ? (
                        <AlertCircle className="w-4 h-4 text-red-600" />
                      ) : (
                        <File className="w-4 h-4 text-blue-600" />
                      )}
                    </div>
                    
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  
                  {file.status === 'uploading' && (
                    <div className="text-xs text-blue-600">{file.progress}%</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        )}

        {/* Input Area - ChatGPT Style */}
        <div className="p-4 border-t border-gray-200">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit}>
            <div className="flex items-end space-x-3">
              <button
                type="button"
                onClick={() => setShowFileUpload(!showFileUpload)}
                className={`p-3 rounded-lg transition-colors ${
                  showFileUpload 
                    ? 'bg-gray-200 text-gray-700' 
                    : 'hover:bg-gray-100 text-gray-500'
                }`}
              >
                <Paperclip className="w-5 h-5" />
              </button>
              
              <div className="flex-1 relative">
                <Input
                  type="text"
                  placeholder="Message"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isLoading}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
                
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </form>
          
          <p className="text-xs text-gray-500 text-center mt-2">
            AI can make mistakes. Check important info.
          </p>
        </div>
        </div>

        {/* Drag Overlay */}
        {isDragOver && (
        <div className="absolute inset-0 bg-blue-50/80 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 shadow-lg border text-center">
            <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center mx-auto mb-3">
              <Upload className="w-6 h-6 text-white" />
            </div>
            <p className="font-medium text-gray-900 mb-1">Drop files to upload</p>
            <p className="text-sm text-gray-600">Add knowledge to your chatbot</p>
          </div>
        </div>
        )}
        
        {/* Error message */}
        {error && (
        <div className="p-4 bg-red-50 border-t border-red-200">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-700 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        )}
      </div>
    </div>
  )
}