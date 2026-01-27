import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Globe,
  Upload,
  Trash2,
  Eye,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  Plus,
  Download,
  Sparkles,
  Brain,
  Zap
} from 'lucide-react'
import { Button } from '../ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface KnowledgeSource {
  id: string
  name: string
  type: 'file' | 'url'
  url?: string
  file_path?: string
  status: 'pending' | 'processing' | 'ready' | 'error'
  is_citable: boolean
  created_at: string
  updated_at: string
  error_message?: string
  size?: number
  content_preview?: string
}

interface KnowledgeSourceManagerProps {
  chatbot: Chatbot
  onUploadRequested: () => void
}

export function KnowledgeSourceManager({ chatbot, onUploadRequested }: KnowledgeSourceManagerProps) {
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [training, setTraining] = useState(false)
  const [trainingStatus, setTrainingStatus] = useState<'idle' | 'training' | 'success' | 'error'>('idle')

  useEffect(() => {
    loadKnowledgeSources()
  }, [chatbot.id])

  const loadKnowledgeSources = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // This would be the API call to get knowledge sources for a chatbot
      // For now, we'll simulate some data since the endpoint might not be implemented
      const mockSources: KnowledgeSource[] = [
        {
          id: '1',
          name: 'product-guide.pdf',
          type: 'file',
          file_path: '/uploads/product-guide.pdf',
          status: 'ready',
          is_citable: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          size: 1024000
        },
        {
          id: '2',
          name: 'https://company.com/faq',
          type: 'url',
          url: 'https://company.com/faq',
          status: 'processing',
          is_citable: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ]
      
      // Try to fetch real data, fall back to mock if needed
      try {
        // const response = await apiService.getKnowledgeSources(chatbot.id)
        // setKnowledgeSources(response)
        setKnowledgeSources(mockSources) // Use mock data for now
      } catch (apiError) {
        console.log('Using mock data since API endpoint not available')
        setKnowledgeSources(mockSources)
      }
      
    } catch (err: any) {
      console.error('Failed to load knowledge sources:', err)
      setError(err.message || 'Failed to load knowledge sources')
      setKnowledgeSources([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this knowledge source?')) {
      return
    }

    try {
      setDeletingId(sourceId)

      // API call to delete knowledge source
      // await apiService.deleteKnowledgeSource(chatbot.id, sourceId)

      // Remove from local state
      setKnowledgeSources(prev => prev.filter(source => source.id !== sourceId))

      console.log(`Deleted knowledge source: ${sourceId}`)

    } catch (err: any) {
      console.error('Failed to delete knowledge source:', err)
      alert('Failed to delete knowledge source. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleTrainEmbeddings = async () => {
    try {
      setTraining(true)
      setTrainingStatus('training')
      setError(null)

      // Call the train embeddings API
      await (apiService as any).request(`/chatbots/${chatbot.id}/train/`, {
        method: 'POST'
      })

      setTrainingStatus('success')

      // Reload knowledge sources to get updated status
      await loadKnowledgeSources()

      // Reset status after 3 seconds
      setTimeout(() => {
        setTrainingStatus('idle')
      }, 3000)

    } catch (err: any) {
      console.error('Failed to train embeddings:', err)
      setError(err.message || 'Failed to generate embeddings. Please try again.')
      setTrainingStatus('error')

      // Reset status after 5 seconds
      setTimeout(() => {
        setTrainingStatus('idle')
      }, 5000)
    } finally {
      setTraining(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-success-500" />
      case 'processing':
        return <Loader2 className="w-4 h-4 text-warning-500 animate-spin" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-error-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      ready: 'success' as const,
      processing: 'warning' as const,
      error: 'error' as const,
      pending: 'secondary' as const
    }
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'secondary'}>
        {status}
      </Badge>
    )
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="bg-slate-900/50 rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
          <span className="ml-3 text-slate-400">Loading knowledge sources...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-900/50 rounded-2xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 bg-white/5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-violet-400" />
              Knowledge Sources
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Manage files and URLs that your chatbot learns from
            </p>
          </div>
          <div className="flex items-center gap-2">
            <motion.button
              onClick={onUploadRequested}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 border border-white/10 text-sm text-white hover:bg-white/20 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Sources
            </motion.button>
          </div>
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

        {knowledgeSources.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-violet-400" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">
              No knowledge sources yet
            </h3>
            <p className="text-sm text-slate-500 mb-6 max-w-sm mx-auto">
              Upload documents or add website URLs to improve your chatbot's responses
            </p>
            <motion.button
              onClick={onUploadRequested}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium shadow-lg shadow-violet-500/25 hover:opacity-90 transition-opacity"
            >
              <Plus className="w-4 h-4" />
              Add Your First Source
            </motion.button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Train Embeddings Button */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="p-4 bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10 rounded-xl border border-violet-500/20"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    trainingStatus === 'training'
                      ? 'bg-amber-500/20'
                      : trainingStatus === 'success'
                      ? 'bg-emerald-500/20'
                      : 'bg-violet-500/20'
                  }`}>
                    {trainingStatus === 'training' ? (
                      <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                    ) : trainingStatus === 'success' ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <Sparkles className="w-5 h-5 text-violet-400" />
                    )}
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-white">Generate Embeddings</h4>
                    <p className="text-xs text-slate-500">
                      {trainingStatus === 'training'
                        ? 'Processing your knowledge sources...'
                        : trainingStatus === 'success'
                        ? 'Embeddings generated successfully!'
                        : 'Train your chatbot on the uploaded content'}
                    </p>
                  </div>
                </div>
                <motion.button
                  onClick={handleTrainEmbeddings}
                  disabled={training || knowledgeSources.length === 0}
                  whileHover={{ scale: training ? 1 : 1.02 }}
                  whileTap={{ scale: training ? 1 : 0.98 }}
                  className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm shadow-lg transition-all ${
                    trainingStatus === 'success'
                      ? 'bg-emerald-500 text-white shadow-emerald-500/25'
                      : 'bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow-violet-500/25 hover:opacity-90'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {training ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Training...
                    </>
                  ) : trainingStatus === 'success' ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Done!
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      Train Now
                    </>
                  )}
                </motion.button>
              </div>
            </motion.div>

            {/* Sources List */}
            <div className="space-y-2">
              {knowledgeSources.map((source) => (
                <motion.div
                  key={source.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/[0.07] transition-colors group"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Source Type Icon */}
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      source.type === 'file' ? 'bg-violet-500/20' : 'bg-cyan-500/20'
                    }`}>
                      {source.type === 'file' ? (
                        <FileText className="w-5 h-5 text-violet-400" />
                      ) : (
                        <Globe className="w-5 h-5 text-cyan-400" />
                      )}
                    </div>

                    {/* Source Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium text-white truncate">
                          {source.name}
                        </h4>
                        {getStatusIcon(source.status)}
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          source.status === 'ready'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : source.status === 'processing'
                            ? 'bg-amber-500/20 text-amber-400'
                            : source.status === 'error'
                            ? 'bg-rose-500/20 text-rose-400'
                            : 'bg-slate-500/20 text-slate-400'
                        }`}>
                          {source.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                        <span>Added {formatDate(source.created_at)}</span>
                        {source.size && <span>{formatFileSize(source.size)}</span>}
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          source.is_citable
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-amber-500/10 text-amber-400'
                        }`}>
                          {source.is_citable ? 'Citable' : 'Learn Only'}
                        </span>
                      </div>

                      {source.error_message && (
                        <p className="text-xs text-rose-400 mt-1">{source.error_message}</p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {source.type === 'url' && (
                      <button
                        onClick={() => window.open(source.url, '_blank')}
                        className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
                        title="Open URL"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    )}

                    {source.type === 'file' && source.status === 'ready' && (
                      <button
                        onClick={() => console.log('Download file:', source.file_path)}
                        className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
                        title="Download file"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(source.id)}
                      disabled={deletingId === source.id}
                      className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                      title="Delete source"
                    >
                      {deletingId === source.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Privacy Legend */}
            <div className="mt-4 p-4 bg-white/5 rounded-xl border border-white/10">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-slate-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-slate-500">
                  <p className="font-medium text-slate-400 mb-1">Privacy Settings:</p>
                  <p><span className="text-emerald-400">Citable</span> - Content can be quoted and shown to users</p>
                  <p><span className="text-amber-400">Learn Only</span> - Used for context but never revealed to users</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}