import { useState, useEffect } from 'react'
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
  Download
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
      <Card>
        <CardContent className="p-6 text-center">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading knowledge sources...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Knowledge Sources</CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Manage files and URLs that your chatbot learns from
            </p>
          </div>
          <Button onClick={onUploadRequested} size="sm" variant="gradient">
            <Plus className="w-4 h-4 mr-2" />
            Add Sources
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-lg flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-error-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-error-900">Error</p>
              <p className="text-sm text-error-700">{error}</p>
            </div>
          </div>
        )}

        {knowledgeSources.length === 0 ? (
          <div className="text-center py-8">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No knowledge sources yet
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Upload documents or add website URLs to improve your chatbot's responses
            </p>
            <Button onClick={onUploadRequested} variant="gradient">
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Source
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {knowledgeSources.map((source) => (
              <div 
                key={source.id} 
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-3 flex-1">
                  {/* Source Type Icon */}
                  <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border">
                    {source.type === 'file' ? (
                      <FileText className="w-5 h-5 text-gray-600" />
                    ) : (
                      <Globe className="w-5 h-5 text-gray-600" />
                    )}
                  </div>

                  {/* Source Info */}
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-900 truncate max-w-xs">
                        {source.name}
                      </h4>
                      {getStatusIcon(source.status)}
                      {getStatusBadge(source.status)}
                    </div>
                    
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>Added {formatDate(source.created_at)}</span>
                      {source.size && <span>{formatFileSize(source.size)}</span>}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        source.is_citable 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-orange-100 text-orange-700'
                      }`}>
                        {source.is_citable ? 'Citable' : 'Learn Only'}
                      </span>
                    </div>

                    {source.error_message && (
                      <p className="text-xs text-error-600">{source.error_message}</p>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  {source.type === 'url' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(source.url, '_blank')}
                      title="Open URL"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  )}
                  
                  {source.type === 'file' && source.status === 'ready' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        // Download file
                        console.log('Download file:', source.file_path)
                      }}
                      title="Download file"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(source.id)}
                    disabled={deletingId === source.id}
                    className="text-error-600 hover:text-error-700"
                    title="Delete source"
                  >
                    {deletingId === source.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {knowledgeSources.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5" />
              <div className="text-xs text-blue-800">
                <p className="font-medium mb-1">Privacy Settings:</p>
                <p>• <strong>Citable:</strong> Content can be quoted and shown to users</p>
                <p>• <strong>Learn Only:</strong> Used for context but never revealed to users</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}