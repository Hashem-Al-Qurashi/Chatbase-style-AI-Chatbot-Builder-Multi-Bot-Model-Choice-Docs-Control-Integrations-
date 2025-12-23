import { useState, useEffect, useCallback } from 'react'
import { 
  X, Bot, ChevronRight, ChevronLeft, Upload, Link, 
  FileText, Globe, Lock, Unlock, Check, AlertCircle,
  Loader2, Trash2
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'
import { Modal } from '../ui/Modal'
import { Card } from '../ui/Card'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface ChatbotWizardProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  existingChatbot?: Chatbot | null
}

interface KnowledgeSource {
  id?: string
  type: 'file' | 'url'
  name: string
  content?: string
  file?: File
  url?: string
  is_citable: boolean
  status: 'pending' | 'processing' | 'ready' | 'error'
  error?: string
}

export function ChatbotWizard({ isOpen, onClose, onSuccess, existingChatbot }: ChatbotWizardProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Step 1: Basic Info
  const [chatbotData, setChatbotData] = useState({
    name: '',
    description: '',
    welcome_message: 'Hello! How can I help you today?',
    personality: 'professional', // 'professional' or 'casual'
    system_prompt: '' // Custom instructions for the AI
  })

  // Step 2: Knowledge Sources
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [urlInput, setUrlInput] = useState('')

  // Load existing chatbot data if editing
  useEffect(() => {
    if (existingChatbot) {
      setChatbotData({
        name: existingChatbot.name || '',
        description: existingChatbot.description || '',
        welcome_message: existingChatbot.welcome_message || 'Hello! How can I help you today?',
        personality: 'professional', // Default since this is a new field
        system_prompt: '' // Will be loaded from settings
      })
      // Load existing knowledge sources if available
      loadExistingKnowledgeSources(existingChatbot.id)
      // Load existing settings (including system_prompt)
      loadExistingSettings(existingChatbot.id)
    }
  }, [existingChatbot])

  const loadExistingKnowledgeSources = async (chatbotId: string) => {
    try {
      // This would load existing knowledge sources from the API
      // For now, we'll just initialize empty
      setKnowledgeSources([])
    } catch (err) {
      console.error('Failed to load knowledge sources:', err)
    }
  }

  const loadExistingSettings = async (chatbotId: string) => {
    try {
      const settings = await apiService.getChatbotSettings(chatbotId)
      if (settings?.system_prompt) {
        setChatbotData(prev => ({ ...prev, system_prompt: settings.system_prompt }))
      }
    } catch (err) {
      console.error('Failed to load chatbot settings:', err)
    }
  }

  // File Upload Handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files)
    }
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files)
    }
  }

  const handleFiles = (files: FileList) => {
    const newSources: KnowledgeSource[] = []
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      // Validate file type
      const validTypes = ['.pdf', '.docx', '.txt', '.doc']
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      
      if (!validTypes.includes(fileExtension)) {
        setError(`File type ${fileExtension} not supported. Please use PDF, DOCX, or TXT files.`)
        continue
      }

      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        setError(`File "${file.name}" is too large. Maximum size is 10MB.`)
        continue
      }

      newSources.push({
        type: 'file',
        name: file.name,
        file: file,
        is_citable: true, // Default to citable
        status: 'pending'
      })
    }

    setKnowledgeSources(prev => [...prev, ...newSources])
    setError(null)
  }

  // URL Processing
  const handleAddUrls = () => {
    const urls = urlInput.split('\n').filter(url => url.trim())
    const newSources: KnowledgeSource[] = []

    for (const url of urls) {
      // Basic URL validation
      try {
        new URL(url.trim())
        newSources.push({
          type: 'url',
          name: url.trim(),
          url: url.trim(),
          is_citable: true,
          status: 'pending'
        })
      } catch {
        setError(`Invalid URL: ${url}`)
        return
      }
    }

    if (newSources.length > 0) {
      setKnowledgeSources(prev => [...prev, ...newSources])
      setUrlInput('')
      setError(null)
    }
  }

  // Toggle privacy for a source
  const toggleSourcePrivacy = (index: number) => {
    setKnowledgeSources(prev => prev.map((source, i) => 
      i === index ? { ...source, is_citable: !source.is_citable } : source
    ))
  }

  // Remove a source
  const removeSource = (index: number) => {
    setKnowledgeSources(prev => prev.filter((_, i) => i !== index))
  }

  // Navigation
  const handleNext = () => {
    if (currentStep === 1) {
      if (!chatbotData.name.trim()) {
        setError('Please enter a name for your chatbot')
        return
      }
    }
    setError(null)
    setCurrentStep(prev => Math.min(prev + 1, 3))
  }

  const handlePrevious = () => {
    setError(null)
    setCurrentStep(prev => Math.max(prev - 1, 1))
  }

  // Save chatbot
  const handleSave = async () => {
    setError(null)
    setLoading(true)

    try {
      // Step 1: Create or update the chatbot
      let chatbotId = existingChatbot?.id
      
      if (!chatbotId) {
        // Create new chatbot
        const chatbotPayload = {
          name: chatbotData.name,
          description: chatbotData.description,
          welcome_message: chatbotData.welcome_message,
          model_name: 'gpt-3.5-turbo',
          temperature: chatbotData.personality === 'casual' ? 0.8 : 0.5,
          max_tokens: 150,
          enable_citations: true
        }
        
        const newChatbot = await apiService.createChatbot(chatbotPayload)
        chatbotId = newChatbot.id
      } else {
        // Update existing chatbot
        await apiService.updateChatbot(chatbotId, {
          name: chatbotData.name,
          description: chatbotData.description,
          welcome_message: chatbotData.welcome_message,
          temperature: chatbotData.personality === 'casual' ? 0.8 : 0.5
        })
      }

      // Step 2: Save custom instructions (system prompt) if provided
      if (chatbotData.system_prompt.trim()) {
        try {
          await apiService.updateChatbotSettings(chatbotId, {
            system_prompt: chatbotData.system_prompt
          })
          console.log('Saved custom instructions')
        } catch (err) {
          console.error('Failed to save custom instructions:', err)
        }
      }

      // Step 3: Upload knowledge sources
      for (const source of knowledgeSources) {
        if (source.status === 'ready') continue // Skip already processed sources

        try {
          if (source.type === 'file' && source.file) {
            // Upload file using the correct API method signature
            await apiService.uploadKnowledgeFile(chatbotId, source.file, {
              name: source.name,
              is_citable: source.is_citable
            })
            console.log('Uploaded file:', source.name)
          } else if (source.type === 'url' && source.url) {
            // Process URL
            await apiService.addKnowledgeUrl(chatbotId, {
              url: source.url,
              is_citable: source.is_citable,
              name: source.name
            })
            console.log('Processing URL:', source.url)
          }
        } catch (err) {
          console.error(`Failed to process ${source.name}:`, err)
        }
      }

      onSuccess()
    } catch (err: any) {
      console.error('Failed to save chatbot:', err)
      setError(err.message || 'Failed to save chatbot. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="w-full max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-xl">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {existingChatbot ? 'Edit Chatbot' : 'Create Your Chatbot'}
                  </h2>
                  <p className="text-sm text-gray-500">Step {currentStep} of 3</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Progress Bar */}
            <div className="mt-4 flex items-center space-x-2">
              <div className={`flex-1 h-2 rounded-full ${currentStep >= 1 ? 'bg-primary-600' : 'bg-gray-200'}`} />
              <div className={`flex-1 h-2 rounded-full ${currentStep >= 2 ? 'bg-primary-600' : 'bg-gray-200'}`} />
              <div className={`flex-1 h-2 rounded-full ${currentStep >= 3 ? 'bg-primary-600' : 'bg-gray-200'}`} />
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Step 1: Basic Information */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Let's start with the basics
                  </h3>
                  <p className="text-sm text-gray-600 mb-6">
                    Give your chatbot a name and describe what it will help with.
                  </p>
                </div>

                <div>
                  <Label htmlFor="name">Chatbot Name *</Label>
                  <Input
                    id="name"
                    value={chatbotData.name}
                    onChange={(e) => setChatbotData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Customer Support Bot"
                    className="mt-1"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Choose a clear name that describes your chatbot's purpose
                  </p>
                </div>

                <div>
                  <Label htmlFor="description">Description (Optional)</Label>
                  <textarea
                    id="description"
                    value={chatbotData.description}
                    onChange={(e) => setChatbotData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="This chatbot helps customers with product questions and support issues..."
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="welcome">Welcome Message</Label>
                  <Input
                    id="welcome"
                    value={chatbotData.welcome_message}
                    onChange={(e) => setChatbotData(prev => ({ ...prev, welcome_message: e.target.value }))}
                    placeholder="Hello! How can I help you today?"
                    className="mt-1"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    The first message your visitors will see
                  </p>
                </div>

                <div>
                  <Label>Personality</Label>
                  <div className="mt-2 space-y-2">
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="personality"
                        value="professional"
                        checked={chatbotData.personality === 'professional'}
                        onChange={(e) => setChatbotData(prev => ({ ...prev, personality: e.target.value }))}
                        className="w-4 h-4 text-primary-600"
                      />
                      <span className="text-sm text-gray-700">
                        <span className="font-medium">Professional</span> - Formal and business-like
                      </span>
                    </label>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="personality"
                        value="casual"
                        checked={chatbotData.personality === 'casual'}
                        onChange={(e) => setChatbotData(prev => ({ ...prev, personality: e.target.value }))}
                        className="w-4 h-4 text-primary-600"
                      />
                      <span className="text-sm text-gray-700">
                        <span className="font-medium">Casual</span> - Friendly and conversational
                      </span>
                    </label>
                  </div>
                </div>

                <div>
                  <Label htmlFor="system_prompt">Custom Instructions (Optional)</Label>
                  <textarea
                    id="system_prompt"
                    value={chatbotData.system_prompt}
                    onChange={(e) => setChatbotData(prev => ({ ...prev, system_prompt: e.target.value }))}
                    placeholder="Add custom instructions for your chatbot. For example:&#10;- You are a helpful customer support agent for [Company Name]&#10;- Always be polite and professional&#10;- If you don't know the answer, say so&#10;- Focus on helping users with [specific topics]"
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={5}
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    These instructions tell the AI how to behave and respond. Leave empty to use default behavior.
                  </p>
                </div>
              </div>
            )}

            {/* Step 2: Knowledge Sources */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Add Knowledge Sources
                  </h3>
                  <p className="text-sm text-gray-600 mb-6">
                    Upload documents or add website URLs for your chatbot to learn from.
                    You can control what information is shown to users.
                  </p>
                </div>

                {/* File Upload Area */}
                <div>
                  <Label>Upload Documents</Label>
                  <div
                    className={`mt-2 border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                      dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-gray-400'
                    }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                  >
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                    <p className="text-sm text-gray-600 mb-2">
                      Drag and drop files here, or click to browse
                    </p>
                    <p className="text-xs text-gray-500 mb-3">
                      Supports PDF, DOCX, and TXT files (max 10MB each)
                    </p>
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.docx,.doc,.txt"
                      onChange={handleFileInput}
                      className="hidden"
                      id="file-upload"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => document.getElementById('file-upload')?.click()}
                    >
                      Choose Files
                    </Button>
                  </div>
                </div>

                {/* URL Input */}
                <div>
                  <Label>Add Website URLs</Label>
                  <div className="mt-2 space-y-2">
                    <textarea
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      placeholder="Enter URLs (one per line)&#10;https://example.com/about&#10;https://example.com/faq"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      rows={3}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleAddUrls}
                      disabled={!urlInput.trim()}
                    >
                      <Link className="w-4 h-4 mr-2" />
                      Add URLs
                    </Button>
                  </div>
                </div>

                {/* Knowledge Sources List */}
                {knowledgeSources.length > 0 && (
                  <div>
                    <Label>Knowledge Sources ({knowledgeSources.length})</Label>
                    <div className="mt-2 space-y-2 max-h-64 overflow-y-auto">
                      {knowledgeSources.map((source, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center space-x-3 flex-1">
                            {source.type === 'file' ? (
                              <FileText className="w-4 h-4 text-gray-400" />
                            ) : (
                              <Globe className="w-4 h-4 text-gray-400" />
                            )}
                            <span className="text-sm text-gray-700 truncate flex-1">
                              {source.name}
                            </span>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => toggleSourcePrivacy(index)}
                              className="flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium transition-colors"
                              title={source.is_citable ? 'Content can be shown to users' : 'Content is private (learning only)'}
                            >
                              {source.is_citable ? (
                                <>
                                  <Unlock className="w-3 h-3 text-green-600" />
                                  <span className="text-green-700">Citable</span>
                                </>
                              ) : (
                                <>
                                  <Lock className="w-3 h-3 text-orange-600" />
                                  <span className="text-orange-700">Learn Only</span>
                                </>
                              )}
                            </button>
                            <button
                              onClick={() => removeSource(index)}
                              className="text-red-500 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-800">
                        <strong>Privacy Settings:</strong><br />
                        • <strong>Citable:</strong> Content can be quoted and shown to users<br />
                        • <strong>Learn Only:</strong> Used for context but never revealed to users
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Review */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Review Your Chatbot
                  </h3>
                  <p className="text-sm text-gray-600 mb-6">
                    Everything looks good? Let's create your chatbot!
                  </p>
                </div>

                <Card className="p-4 space-y-3">
                  <div className="flex items-center space-x-3">
                    <Bot className="w-5 h-5 text-primary-600" />
                    <div>
                      <p className="font-medium text-gray-900">{chatbotData.name}</p>
                      <p className="text-sm text-gray-500">{chatbotData.description || 'No description'}</p>
                    </div>
                  </div>
                  
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-gray-600">
                      <strong>Welcome Message:</strong> {chatbotData.welcome_message}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      <strong>Personality:</strong> {chatbotData.personality === 'casual' ? 'Casual' : 'Professional'}
                    </p>
                    {chatbotData.system_prompt && (
                      <p className="text-sm text-gray-600 mt-1">
                        <strong>Custom Instructions:</strong> {chatbotData.system_prompt.length > 100
                          ? chatbotData.system_prompt.substring(0, 100) + '...'
                          : chatbotData.system_prompt}
                      </p>
                    )}
                  </div>

                  {knowledgeSources.length > 0 && (
                    <div className="pt-3 border-t border-gray-100">
                      <p className="text-sm font-medium text-gray-700 mb-2">
                        Knowledge Sources ({knowledgeSources.length})
                      </p>
                      <div className="space-y-1">
                        <p className="text-sm text-gray-600">
                          • {knowledgeSources.filter(s => s.is_citable).length} citable sources
                        </p>
                        <p className="text-sm text-gray-600">
                          • {knowledgeSources.filter(s => !s.is_citable).length} private sources (learn only)
                        </p>
                      </div>
                    </div>
                  )}
                </Card>

                <div className="flex items-start space-x-2">
                  <Check className="w-5 h-5 text-green-600 mt-0.5" />
                  <div className="text-sm text-gray-600">
                    <p className="font-medium text-gray-900 mb-1">Ready to go!</p>
                    <p>Your chatbot will be created and you can start testing it immediately.</p>
                    <p className="mt-2">After creation, you'll be able to:</p>
                    <ul className="mt-1 space-y-1 ml-4">
                      <li>• Test your chatbot with real conversations</li>
                      <li>• Get the embed code for your website</li>
                      <li>• Add more knowledge sources anytime</li>
                      <li>• Track usage and conversations</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
            <Button
              variant="ghost"
              onClick={handlePrevious}
              disabled={currentStep === 1 || loading}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>
            
            {currentStep < 3 ? (
              <Button
                variant="primary"
                onClick={handleNext}
                disabled={loading}
              >
                Next
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    {existingChatbot ? 'Save Changes' : 'Create Chatbot'}
                    <Check className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}