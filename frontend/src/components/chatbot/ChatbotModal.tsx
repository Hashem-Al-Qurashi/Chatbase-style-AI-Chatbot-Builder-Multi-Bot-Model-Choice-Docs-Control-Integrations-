import { useState, useEffect } from 'react'
import { X, Bot, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'
import { Modal } from '../ui/Modal'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface ChatbotModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  mode: 'create' | 'edit'
  chatbot?: Chatbot | null
}

export function ChatbotModal({ isOpen, onClose, onSuccess, mode, chatbot }: ChatbotModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    welcome_message: 'Hello! How can I help you today?',
    placeholder_text: 'Type your message...',
    theme_color: '#6366f1',
    temperature: 0.7,
    max_tokens: 150,
    model_name: 'gpt-3.5-turbo',
    enable_citations: true,
    enable_data_collection: false
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load existing chatbot data for edit mode
  useEffect(() => {
    if (mode === 'edit' && chatbot) {
      setFormData({
        name: chatbot.name || '',
        description: chatbot.description || '',
        welcome_message: chatbot.welcome_message || 'Hello! How can I help you today?',
        placeholder_text: chatbot.placeholder_text || 'Type your message...',
        theme_color: chatbot.theme_color || '#6366f1',
        temperature: chatbot.temperature || 0.7,
        max_tokens: chatbot.max_tokens || 150,
        model_name: chatbot.model_name || 'gpt-3.5-turbo',
        enable_citations: chatbot.enable_citations !== undefined ? chatbot.enable_citations : true,
        enable_data_collection: chatbot.enable_data_collection || false
      })
    } else if (mode === 'create') {
      // Reset form for create mode
      setFormData({
        name: '',
        description: '',
        welcome_message: 'Hello! How can I help you today?',
        placeholder_text: 'Type your message...',
        theme_color: '#6366f1',
        temperature: 0.7,
        max_tokens: 150,
        model_name: 'gpt-3.5-turbo',
        enable_citations: true,
        enable_data_collection: false
      })
    }
  }, [mode, chatbot])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (mode === 'create') {
        await apiService.createChatbot(formData)
      } else if (mode === 'edit' && chatbot) {
        await apiService.updateChatbot(chatbot.id, formData)
      }
      
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('Chatbot operation error:', err)
      setError(err.message || `Failed to ${mode} chatbot`)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked
      setFormData(prev => ({ ...prev, [name]: checked }))
    } else if (type === 'number') {
      setFormData(prev => ({ ...prev, [name]: parseFloat(value) }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="w-full max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-xl">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {mode === 'create' ? 'Create New Chatbot' : 'Edit Chatbot'}
                </h2>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {error && (
              <div className="p-4 bg-error-50 border border-error-200 rounded-lg flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-error-500 mt-0.5" />
                <div>
                  <p className="font-medium text-error-900">Error</p>
                  <p className="text-sm text-error-700">{error}</p>
                </div>
              </div>
            )}

            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Basic Information</h3>
              
              <div>
                <Label htmlFor="name">Chatbot Name *</Label>
                <Input
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., Customer Support Bot"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Brief description of your chatbot's purpose..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  rows={3}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Appearance Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Appearance</h3>
              
              <div>
                <Label htmlFor="welcome_message">Welcome Message</Label>
                <Input
                  id="welcome_message"
                  name="welcome_message"
                  value={formData.welcome_message}
                  onChange={handleChange}
                  placeholder="Hello! How can I help you today?"
                  disabled={loading}
                />
              </div>

              <div>
                <Label htmlFor="placeholder_text">Input Placeholder Text</Label>
                <Input
                  id="placeholder_text"
                  name="placeholder_text"
                  value={formData.placeholder_text}
                  onChange={handleChange}
                  placeholder="Type your message..."
                  disabled={loading}
                />
              </div>

              <div>
                <Label htmlFor="theme_color">Theme Color</Label>
                <div className="flex items-center space-x-3">
                  <Input
                    id="theme_color"
                    name="theme_color"
                    type="color"
                    value={formData.theme_color}
                    onChange={handleChange}
                    className="w-20 h-10 cursor-pointer"
                    disabled={loading}
                  />
                  <Input
                    value={formData.theme_color}
                    onChange={handleChange}
                    name="theme_color"
                    placeholder="#6366f1"
                    className="flex-1"
                    disabled={loading}
                  />
                </div>
              </div>
            </div>

            {/* AI Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">AI Configuration</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="model_name">Model</Label>
                  <select
                    id="model_name"
                    name="model_name"
                    value={formData.model_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, model_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={loading}
                  >
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    <option value="gpt-4">GPT-4</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  </select>
                </div>

                <div>
                  <Label htmlFor="temperature">
                    Temperature: {formData.temperature}
                  </Label>
                  <input
                    id="temperature"
                    name="temperature"
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={formData.temperature}
                    onChange={handleChange}
                    className="w-full"
                    disabled={loading}
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Precise</span>
                    <span>Creative</span>
                  </div>
                </div>
              </div>

              <div>
                <Label htmlFor="max_tokens">Max Response Length (tokens)</Label>
                <Input
                  id="max_tokens"
                  name="max_tokens"
                  type="number"
                  min="50"
                  max="500"
                  value={formData.max_tokens}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>

              {/* Feature Toggles */}
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <input
                    id="enable_citations"
                    name="enable_citations"
                    type="checkbox"
                    checked={formData.enable_citations}
                    onChange={handleChange}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                    disabled={loading}
                  />
                  <Label htmlFor="enable_citations" className="cursor-pointer">
                    Enable source citations in responses
                  </Label>
                </div>

                <div className="flex items-center space-x-3">
                  <input
                    id="enable_data_collection"
                    name="enable_data_collection"
                    type="checkbox"
                    checked={formData.enable_data_collection}
                    onChange={handleChange}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                    disabled={loading}
                  />
                  <Label htmlFor="enable_data_collection" className="cursor-pointer">
                    Enable conversation data collection for improvements
                  </Label>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="gradient"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {mode === 'create' ? 'Creating...' : 'Saving...'}
                  </>
                ) : (
                  mode === 'create' ? 'Create Chatbot' : 'Save Changes'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  )
}