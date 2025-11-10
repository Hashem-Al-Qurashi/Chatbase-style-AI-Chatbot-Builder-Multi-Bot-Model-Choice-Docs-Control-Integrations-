import React, { useState, useRef, useEffect, useCallback } from 'react'
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  Copy, 
  ThumbsUp, 
  ThumbsDown,
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
      {/* Header - Minimal & Clean */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">{chatbot?.name || 'AI Assistant'}</h3>
              <p className="text-xs text-gray-500">Online</p>
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

      {/* Messages - Spacious */}
      <div className="flex-1 overflow-y-auto py-8 px-6 space-y-8">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className={`flex items-start space-x-3 max-w-[80%] ${
              message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}>
              {/* Avatar - Minimal */}
              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === 'user' 
                  ? 'bg-blue-500'
                  : 'bg-gray-800'
              }`}>
                {message.role === 'user' ? (
                  <User className="w-3 h-3 text-white" />
                ) : (
                  <Bot className="w-3 h-3 text-white" />
                )}
              </div>

              {/* Message bubble - Clean */}
              <div className={`relative group ${
                message.role === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100'
              } rounded-lg px-4 py-3 max-w-md`}>
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

        {/* Loading indicator - Minimal */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-3">
              <div className="w-7 h-7 bg-gray-800 rounded-full flex items-center justify-center">
                <Bot className="w-3 h-3 text-white" />
              </div>
              <div className="bg-gray-100 rounded-lg px-4 py-3">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                  </div>
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

      {/* Input - Clean & Simple */}
      <div className="border-t border-gray-200 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex items-center space-x-3">
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => setShowFileUpload(!showFileUpload)}
            className="text-gray-400 hover:text-gray-600 p-2"
            title="Upload files"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
          
          <div className="flex-1">
            <Input
              type="text"
              placeholder="Message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="border border-gray-300 rounded-lg px-4 py-3 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            />
          </div>
          
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-blue-500 hover:bg-blue-600 text-white rounded-lg px-4 py-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
        
        {/* Minimal footer */}
        <div className="mt-3 text-center">
          <span className="text-xs text-gray-400">Powered by AI</span>
        </div>
      </div>
    </div>
  )
}