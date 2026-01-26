import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Bot, ChevronRight, ChevronLeft, Upload, Link,
  FileText, Globe, Lock, Unlock, Check, AlertCircle,
  Loader2, Trash2, Sparkles, MessageSquare, Brain
} from 'lucide-react'
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
    personality: 'professional',
    system_prompt: ''
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
        personality: 'professional',
        system_prompt: ''
      })
      loadExistingKnowledgeSources(existingChatbot.id)
      loadExistingSettings(existingChatbot.id)
    }
  }, [existingChatbot])

  const loadExistingKnowledgeSources = async (_chatbotId: string) => {
    try {
      // TODO: Load existing knowledge sources from API
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
      const validTypes = ['.pdf', '.docx', '.txt', '.doc']
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()

      if (!validTypes.includes(fileExtension)) {
        setError(`File type ${fileExtension} not supported. Use PDF, DOCX, or TXT.`)
        continue
      }

      if (file.size > 10 * 1024 * 1024) {
        setError(`File "${file.name}" is too large. Max 10MB.`)
        continue
      }

      newSources.push({
        type: 'file',
        name: file.name,
        file: file,
        is_citable: true,
        status: 'pending'
      })
    }

    setKnowledgeSources(prev => [...prev, ...newSources])
    setError(null)
  }

  const handleAddUrls = () => {
    const urls = urlInput.split('\n').filter(url => url.trim())
    const newSources: KnowledgeSource[] = []

    for (const url of urls) {
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

  const toggleSourcePrivacy = (index: number) => {
    setKnowledgeSources(prev => prev.map((source, i) =>
      i === index ? { ...source, is_citable: !source.is_citable } : source
    ))
  }

  const removeSource = (index: number) => {
    setKnowledgeSources(prev => prev.filter((_, i) => i !== index))
  }

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

  const handleSave = async () => {
    setError(null)
    setLoading(true)

    try {
      let chatbotId = existingChatbot?.id

      if (!chatbotId) {
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
        await apiService.updateChatbot(chatbotId, {
          name: chatbotData.name,
          description: chatbotData.description,
          welcome_message: chatbotData.welcome_message,
          temperature: chatbotData.personality === 'casual' ? 0.8 : 0.5
        })
      }

      if (chatbotData.system_prompt.trim()) {
        try {
          await apiService.updateChatbotSettings(chatbotId, {
            system_prompt: chatbotData.system_prompt
          })
        } catch (err) {
          console.error('Failed to save custom instructions:', err)
        }
      }

      for (const source of knowledgeSources) {
        if (source.status === 'ready') continue

        try {
          if (source.type === 'file' && source.file) {
            await apiService.uploadKnowledgeFile(chatbotId, source.file, {
              name: source.name,
              is_citable: source.is_citable
            })
          } else if (source.type === 'url' && source.url) {
            await apiService.addKnowledgeUrl(chatbotId, {
              url: source.url,
              is_citable: source.is_citable,
              name: source.name
            })
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

  const steps = [
    { num: 1, label: 'Basics', icon: Bot },
    { num: 2, label: 'Knowledge', icon: Brain },
    { num: 3, label: 'Review', icon: Sparkles }
  ]

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', duration: 0.5 }}
            className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 rounded-2xl border border-white/10 shadow-2xl shadow-violet-500/10 overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/10 bg-white/5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/25">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">
                      {existingChatbot ? 'Edit Chatbot' : 'Create Chatbot'}
                    </h2>
                    <p className="text-xs text-slate-500">Step {currentStep} of 3</p>
                  </div>
                </div>

                {/* Step Indicators */}
                <div className="hidden sm:flex items-center gap-2">
                  {steps.map((step, idx) => {
                    const StepIcon = step.icon
                    const isActive = currentStep === step.num
                    const isCompleted = currentStep > step.num
                    return (
                      <div key={step.num} className="flex items-center">
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
                          isActive ? 'bg-violet-500/20 border border-violet-500/30' :
                          isCompleted ? 'bg-emerald-500/10' : 'bg-white/5'
                        }`}>
                          <StepIcon className={`w-4 h-4 ${
                            isActive ? 'text-violet-400' :
                            isCompleted ? 'text-emerald-400' : 'text-slate-500'
                          }`} />
                          <span className={`text-xs font-medium ${
                            isActive ? 'text-violet-300' :
                            isCompleted ? 'text-emerald-400' : 'text-slate-500'
                          }`}>{step.label}</span>
                        </div>
                        {idx < steps.length - 1 && (
                          <ChevronRight className="w-4 h-4 text-slate-600 mx-1" />
                        )}
                      </div>
                    )
                  })}
                </div>

                <button
                  onClick={onClose}
                  className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              {/* Error Message */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-2"
                  >
                    <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                    <p className="text-sm text-rose-400">{error}</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Step 1: Basic Information */}
              <AnimatePresence mode="wait">
                {currentStep === 1 && (
                  <motion.div
                    key="step1"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="grid grid-cols-1 lg:grid-cols-2 gap-6"
                  >
                    {/* Left Column */}
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                          Chatbot Name <span className="text-rose-400">*</span>
                        </label>
                        <input
                          value={chatbotData.name}
                          onChange={(e) => setChatbotData(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="e.g., Customer Support Bot"
                          className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                          Description
                        </label>
                        <textarea
                          value={chatbotData.description}
                          onChange={(e) => setChatbotData(prev => ({ ...prev, description: e.target.value }))}
                          placeholder="What does your chatbot help with?"
                          className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all text-sm resize-none"
                          rows={2}
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">
                          Welcome Message
                        </label>
                        <div className="relative">
                          <MessageSquare className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                          <input
                            value={chatbotData.welcome_message}
                            onChange={(e) => setChatbotData(prev => ({ ...prev, welcome_message: e.target.value }))}
                            placeholder="Hello! How can I help you?"
                            className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all text-sm"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Personality
                        </label>
                        <div className="flex gap-3">
                          {[
                            { value: 'professional', label: 'Professional', desc: 'Formal tone' },
                            { value: 'casual', label: 'Casual', desc: 'Friendly tone' }
                          ].map((option) => (
                            <button
                              key={option.value}
                              type="button"
                              onClick={() => setChatbotData(prev => ({ ...prev, personality: option.value }))}
                              className={`flex-1 p-3 rounded-xl border transition-all text-left ${
                                chatbotData.personality === option.value
                                  ? 'bg-violet-500/20 border-violet-500/50 ring-1 ring-violet-500/30'
                                  : 'bg-white/5 border-white/10 hover:border-white/20'
                              }`}
                            >
                              <span className={`block text-sm font-medium ${
                                chatbotData.personality === option.value ? 'text-violet-300' : 'text-white'
                              }`}>{option.label}</span>
                              <span className="text-xs text-slate-500">{option.desc}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Right Column */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1.5">
                        Custom Instructions
                      </label>
                      <textarea
                        value={chatbotData.system_prompt}
                        onChange={(e) => setChatbotData(prev => ({ ...prev, system_prompt: e.target.value }))}
                        placeholder="Add custom instructions for your chatbot...&#10;&#10;Examples:&#10;• You are a helpful support agent for [Company]&#10;• Always be polite and professional&#10;• Focus on helping with [topics]"
                        className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all text-sm resize-none h-[calc(100%-2rem)]"
                        style={{ minHeight: '220px' }}
                      />
                    </div>
                  </motion.div>
                )}

                {/* Step 2: Knowledge Sources */}
                {currentStep === 2 && (
                  <motion.div
                    key="step2"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="grid grid-cols-1 lg:grid-cols-2 gap-6"
                  >
                    {/* Left: Upload Area */}
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Upload Documents
                        </label>
                        <div
                          className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                            dragActive
                              ? 'border-violet-500 bg-violet-500/10'
                              : 'border-white/20 hover:border-white/30 bg-white/5'
                          }`}
                          onDragEnter={handleDrag}
                          onDragLeave={handleDrag}
                          onDragOver={handleDrag}
                          onDrop={handleDrop}
                        >
                          <Upload className={`w-8 h-8 mx-auto mb-2 ${dragActive ? 'text-violet-400' : 'text-slate-500'}`} />
                          <p className="text-sm text-slate-400 mb-1">
                            Drag & drop files here
                          </p>
                          <p className="text-xs text-slate-500 mb-3">
                            PDF, DOCX, TXT (max 10MB)
                          </p>
                          <input
                            type="file"
                            multiple
                            accept=".pdf,.docx,.doc,.txt"
                            onChange={handleFileInput}
                            className="hidden"
                            id="file-upload"
                          />
                          <button
                            onClick={() => document.getElementById('file-upload')?.click()}
                            className="px-4 py-2 rounded-lg bg-white/10 border border-white/10 text-sm text-white hover:bg-white/20 transition-colors"
                          >
                            Browse Files
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                          Add URLs
                        </label>
                        <div className="space-y-2">
                          <textarea
                            value={urlInput}
                            onChange={(e) => setUrlInput(e.target.value)}
                            placeholder="Enter URLs (one per line)&#10;https://example.com/about"
                            className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:border-violet-500/50 text-sm resize-none"
                            rows={3}
                          />
                          <button
                            onClick={handleAddUrls}
                            disabled={!urlInput.trim()}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 border border-white/10 text-sm text-white hover:bg-white/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <Link className="w-4 h-4" />
                            Add URLs
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Right: Sources List */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-slate-300">
                          Knowledge Sources
                        </label>
                        <span className="text-xs text-slate-500">
                          {knowledgeSources.length} source{knowledgeSources.length !== 1 ? 's' : ''}
                        </span>
                      </div>

                      <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden" style={{ height: '280px' }}>
                        {knowledgeSources.length === 0 ? (
                          <div className="h-full flex flex-col items-center justify-center text-center p-6">
                            <Brain className="w-10 h-10 text-slate-600 mb-3" />
                            <p className="text-sm text-slate-500">No sources added yet</p>
                            <p className="text-xs text-slate-600 mt-1">Upload files or add URLs to train your chatbot</p>
                          </div>
                        ) : (
                          <div className="h-full overflow-y-auto p-2 space-y-2">
                            {knowledgeSources.map((source, index) => (
                              <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex items-center justify-between p-2.5 bg-white/5 rounded-lg group"
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  {source.type === 'file' ? (
                                    <FileText className="w-4 h-4 text-violet-400 flex-shrink-0" />
                                  ) : (
                                    <Globe className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                                  )}
                                  <span className="text-sm text-slate-300 truncate">
                                    {source.name}
                                  </span>
                                </div>

                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => toggleSourcePrivacy(index)}
                                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                                      source.is_citable
                                        ? 'text-emerald-400 hover:bg-emerald-500/10'
                                        : 'text-amber-400 hover:bg-amber-500/10'
                                    }`}
                                    title={source.is_citable ? 'Citable' : 'Learn Only'}
                                  >
                                    {source.is_citable ? (
                                      <Unlock className="w-3 h-3" />
                                    ) : (
                                      <Lock className="w-3 h-3" />
                                    )}
                                  </button>
                                  <button
                                    onClick={() => removeSource(index)}
                                    className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </motion.div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Privacy Legend */}
                      <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
                        <div className="flex items-center gap-1">
                          <Unlock className="w-3 h-3 text-emerald-400" />
                          <span>Citable - Can be quoted</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Lock className="w-3 h-3 text-amber-400" />
                          <span>Learn Only - Private</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Step 3: Review */}
                {currentStep === 3 && (
                  <motion.div
                    key="step3"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="grid grid-cols-1 lg:grid-cols-2 gap-6"
                  >
                    {/* Left: Summary */}
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-xl border border-white/10 p-4">
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center">
                            <Bot className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold text-white">{chatbotData.name}</h3>
                            <p className="text-sm text-slate-500">{chatbotData.description || 'No description'}</p>
                          </div>
                        </div>

                        <div className="space-y-3 pt-3 border-t border-white/10">
                          <div className="flex items-start gap-2">
                            <MessageSquare className="w-4 h-4 text-slate-500 mt-0.5" />
                            <div>
                              <p className="text-xs text-slate-500">Welcome Message</p>
                              <p className="text-sm text-slate-300">{chatbotData.welcome_message}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-slate-500" />
                            <div>
                              <p className="text-xs text-slate-500">Personality</p>
                              <p className="text-sm text-slate-300">
                                {chatbotData.personality === 'casual' ? 'Casual' : 'Professional'}
                              </p>
                            </div>
                          </div>

                          {chatbotData.system_prompt && (
                            <div className="flex items-start gap-2">
                              <Brain className="w-4 h-4 text-slate-500 mt-0.5" />
                              <div>
                                <p className="text-xs text-slate-500">Custom Instructions</p>
                                <p className="text-sm text-slate-300 line-clamp-2">{chatbotData.system_prompt}</p>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Knowledge Summary */}
                      <div className="bg-white/5 rounded-xl border border-white/10 p-4">
                        <h4 className="text-sm font-medium text-slate-300 mb-3">Knowledge Sources</h4>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-emerald-400">
                              {knowledgeSources.filter(s => s.is_citable).length}
                            </p>
                            <p className="text-xs text-emerald-400/70">Citable</p>
                          </div>
                          <div className="bg-amber-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-amber-400">
                              {knowledgeSources.filter(s => !s.is_citable).length}
                            </p>
                            <p className="text-xs text-amber-400/70">Private</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Ready State */}
                    <div className="flex flex-col items-center justify-center text-center p-6 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 rounded-xl border border-violet-500/20">
                      <motion.div
                        animate={{ y: [0, -8, 0] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                        className="w-20 h-20 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-2xl flex items-center justify-center mb-4 shadow-xl shadow-violet-500/25"
                      >
                        <Check className="w-10 h-10 text-white" />
                      </motion.div>

                      <h3 className="text-xl font-semibold text-white mb-2">Ready to Launch!</h3>
                      <p className="text-sm text-slate-400 mb-4">
                        Your chatbot is configured and ready to go.
                      </p>

                      <div className="text-left space-y-2 text-sm text-slate-400">
                        <div className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-400" />
                          <span>Test with real conversations</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-400" />
                          <span>Embed on your website</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-emerald-400" />
                          <span>Track usage analytics</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-white/10 bg-white/5 flex justify-between">
              <button
                onClick={handlePrevious}
                disabled={currentStep === 1 || loading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>

              {currentStep < 3 ? (
                <button
                  onClick={handleNext}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      {existingChatbot ? 'Save Changes' : 'Create Chatbot'}
                      <Check className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
