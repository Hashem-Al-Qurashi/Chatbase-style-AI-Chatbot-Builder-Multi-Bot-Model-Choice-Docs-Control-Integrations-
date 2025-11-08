import React, { useState, useRef, useEffect, useCallback } from 'react'
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  RefreshCw, 
  Copy, 
  ThumbsUp, 
  ThumbsDown,
  Sparkles,
  Clock,
  ExternalLink,
  X,
  Minimize2,
  Paperclip,
  File,
  CheckCircle2,
  AlertCircle,
  Upload,
  Trash2
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
      content: `Hello! I'm ${chatbot?.name || 'your AI assistant'}. ${chatbot?.description || 'How can I help you today?'}`,
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
      // Use real API to send message to RAG backend
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

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
    // Could add toast notification here
  }

  const handleFeedback = (messageId: string, type: 'like' | 'dislike') => {
    console.log(`Feedback: ${type} for message ${messageId}`)
    // Implement feedback API call
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
    
    // Add files to upload queue with initial status
    const newFiles: UploadedFile[] = fileArray.map(file => ({
      id: Date.now().toString() + Math.random().toString(36),
      name: file.name,
      size: file.size,
      status: 'uploading',
      progress: 0
    }))
    
    setUploadedFiles(prev => [...prev, ...newFiles])
    
    // Upload each file
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i]
      const uploadFile = newFiles[i]
      
      try {
        // Simulate progress updates (since the API doesn't provide progress)
        const progressInterval = setInterval(() => {
          setUploadedFiles(prev => 
            prev.map(f => 
              f.id === uploadFile.id && f.status === 'uploading'
                ? { ...f, progress: Math.min((f.progress || 0) + 10, 90) }
                : f
            )
          )
        }, 200)
        
        await apiService.uploadKnowledgeFile(chatbot.id, file, {
          name: file.name,
          is_citable: true
        })
        
        clearInterval(progressInterval)
        
        // Mark as success
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === uploadFile.id 
              ? { ...f, status: 'success', progress: 100 }
              : f
          )
        )
        
        // Add success message to chat
        const successMessage: Message = {
          id: (Date.now() + i).toString(),
          role: 'assistant',
          content: `✅ Successfully uploaded "${file.name}". The document has been processed and is now available for questions!`,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, successMessage])
        
      } catch (error: any) {
        console.error('File upload error:', error)
        
        // Mark as error
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === uploadFile.id 
              ? { ...f, status: 'error', error: error.message || 'Upload failed' }
              : f
          )
        )
        
        // Add error message to chat
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

  const handleRemoveFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId))
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
          variant="gradient"
          size="lg"
          className="w-16 h-16 rounded-full shadow-lg shadow-primary-500/25"
        >
          <Bot className="w-6 h-6" />
        </Button>
      </div>
    )
  }

  return (
    <div 
      className={`relative flex flex-col h-full bg-white rounded-2xl overflow-hidden shadow-soft-xl ${
        isDragOver ? 'ring-2 ring-primary-400 bg-gradient-to-br from-primary-50/80 to-accent-50/60' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div className="bg-chatbase-header px-6 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-11 h-11 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm ring-1 ring-white/30">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-lg">{chatbot?.name || 'AI Assistant'}</h3>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <p className="text-sm text-white/80">Online now</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {onToggleMinimize && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleMinimize}
                className="text-white hover:bg-white/20"
              >
                <Minimize2 className="w-4 h-4" />
              </Button>
            )}
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-white hover:bg-white/20"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-50/50 to-white">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className={`flex items-start space-x-3 max-w-[80%] ${
              message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}>
              {/* Avatar */}
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                message.role === 'user' 
                  ? 'bg-gradient-to-br from-gray-100 to-gray-200 ring-1 ring-gray-300/30'
                  : 'bg-chatbase-primary shadow-chatbase ring-1 ring-primary-300/30'
              }`}>
                {message.role === 'user' ? (
                  <User className="w-4 h-4 text-gray-600" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>

              {/* Message bubble */}
              <div className={`relative group ${
                message.role === 'user' 
                  ? 'bg-chatbase-primary text-white shadow-chatbase' 
                  : 'bg-white border border-gray-100/80 shadow-soft-lg'
              } rounded-2xl px-5 py-4`}>
                {/* Message content */}
                <div className="space-y-2">
                  <p className={`text-sm leading-relaxed ${
                    message.role === 'user' ? 'text-white' : 'text-gray-800'
                  }`}>
                    {message.content}
                  </p>

                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-600">Sources:</p>
                      <div className="space-y-1">
                        {message.sources.map((source) => (
                          <a
                            key={source.id}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center space-x-2 text-xs text-primary-600 hover:text-primary-700 transition-colors"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>{source.title}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center space-x-1">
                      <Clock className={`w-3 h-3 ${
                        message.role === 'user' ? 'text-white/60' : 'text-gray-400'
                      }`} />
                      <span className={`text-xs ${
                        message.role === 'user' ? 'text-white/60' : 'text-gray-400'
                      }`}>
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>

                    {/* Message actions */}
                    {message.role === 'assistant' && (
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopyMessage(message.content)}
                          className="h-6 w-6 p-0"
                        >
                          <Copy className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleFeedback(message.id, 'like')}
                          className="h-6 w-6 p-0"
                        >
                          <ThumbsUp className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleFeedback(message.id, 'dislike')}
                          className="h-6 w-6 p-0"
                        >
                          <ThumbsDown className="w-3 h-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start animate-slide-up">
            <div className="flex items-start space-x-4">
              <div className="w-10 h-10 bg-chatbase-primary rounded-2xl flex items-center justify-center shadow-chatbase ring-1 ring-primary-300/30">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white border border-gray-100/80 shadow-soft-lg rounded-2xl px-5 py-4">
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-accent-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span className="text-sm text-gray-600">AI is thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-gradient-to-r from-error-50 to-error-100 border-t border-error-200">
          <div className="flex items-center justify-between">
            <p className="text-sm text-error-700">{error}</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="text-error-600 hover:text-error-700"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* File Upload Area */}
      {(showFileUpload || uploadedFiles.length > 0) && (
        <div className="border-t border-gray-100/80 p-6 bg-chatbase-soft">
          <div className="space-y-3">
            {/* File Upload Zone */}
            {showFileUpload && (
              <div className="space-y-3">
                <div 
                  className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 cursor-pointer ${
                    isDragOver 
                      ? 'border-primary-400 bg-gradient-to-br from-primary-50 to-accent-50/50 shadow-chatbase' 
                      : 'border-gray-300 hover:border-primary-300 hover:bg-chatbase-glass hover:shadow-soft'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600 mb-1">
                    Drop files here or <span className="text-primary-600 cursor-pointer">browse</span>
                  </p>
                  <p className="text-xs text-gray-500">
                    Supports PDF, DOC, DOCX, TXT, and more
                  </p>
                </div>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.pptx"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
              </div>
            )}

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-700">Uploading Files</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setUploadedFiles([])}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    Clear all
                  </Button>
                </div>
                
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {uploadedFiles.map((file) => (
                    <div 
                      key={file.id} 
                      className="flex items-center space-x-3 p-3 bg-white rounded-lg border border-gray-200"
                    >
                      <div className={`w-8 h-8 rounded flex items-center justify-center ${
                        file.status === 'success' 
                          ? 'bg-green-100' 
                          : file.status === 'error' 
                          ? 'bg-red-100' 
                          : 'bg-blue-100'
                      }`}>
                        {file.status === 'success' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                        ) : file.status === 'error' ? (
                          <AlertCircle className="w-4 h-4 text-red-600" />
                        ) : (
                          <File className="w-4 h-4 text-blue-600" />
                        )}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-gray-500">
                            {formatFileSize(file.size)}
                          </span>
                          {file.status === 'uploading' && (
                            <span className="text-xs text-blue-600">
                              {file.progress}%
                            </span>
                          )}
                          {file.status === 'error' && (
                            <span className="text-xs text-red-600">
                              {file.error}
                            </span>
                          )}
                        </div>
                        
                        {file.status === 'uploading' && (
                          <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                            <div 
                              className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                              style={{ width: `${file.progress || 0}%` }}
                            />
                          </div>
                        )}
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveFile(file.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Drag Overlay */}
      {isDragOver && (
        <div className="absolute inset-0 bg-chatbase-glass backdrop-blur-lg flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 shadow-chatbase-lg text-center ring-1 ring-primary-200/50 max-w-sm mx-4">
            <div className="w-16 h-16 bg-chatbase-primary rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-chatbase">
              <Upload className="w-8 h-8 text-white" />
            </div>
            <p className="text-xl font-semibold text-gray-900 mb-2">Drop files to upload</p>
            <p className="text-sm text-gray-600">Add knowledge to your chatbot instantly</p>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-100/80 p-6 bg-white">
        <form onSubmit={handleSubmit} className="flex items-end space-x-4">
          <div className="flex-1">
            <Input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="resize-none border-0 bg-gray-50/70 rounded-2xl shadow-soft focus:ring-2 focus:ring-primary-400/50 focus:bg-white transition-all duration-200 py-4 px-5"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => setShowFileUpload(!showFileUpload)}
              className={`transition-colors ${
                showFileUpload 
                  ? 'text-primary-600 hover:text-primary-700 bg-primary-50' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="Upload files"
            >
              <Paperclip className="w-4 h-4" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              type="button"
              className="text-gray-500 hover:text-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            
            <Button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="bg-chatbase-primary hover:bg-gradient-to-r hover:from-primary-600 hover:to-accent-500 text-white rounded-2xl px-6 py-3 shadow-chatbase hover:shadow-chatbase-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
        </form>

        {/* Typing indicator placeholder */}
        <div className="mt-4 h-4 flex items-center">
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            <div className="w-4 h-4 bg-gradient-to-r from-primary-400 to-accent-400 rounded-full flex items-center justify-center">
              <Sparkles className="w-2.5 h-2.5 text-white" />
            </div>
            <span>Powered by AI • Real-time RAG responses</span>
          </div>
        </div>
      </div>
    </div>
  )
}