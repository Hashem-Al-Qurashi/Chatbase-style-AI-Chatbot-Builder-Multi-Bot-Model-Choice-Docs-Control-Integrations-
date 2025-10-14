import { useState } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { apiService } from '../../services/api'
import { Chatbot } from '../../types'

interface ChatbotDeleteModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  chatbot: Chatbot | null
}

export function ChatbotDeleteModal({ isOpen, onClose, onSuccess, chatbot }: ChatbotDeleteModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!chatbot) return
    
    setError(null)
    setLoading(true)

    try {
      await apiService.deleteChatbot(chatbot.id)
      onSuccess()
      onClose()
    } catch (err: any) {
      console.error('Delete chatbot error:', err)
      setError(err.message || 'Failed to delete chatbot')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !chatbot) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-xl p-6">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-error-100 rounded-full flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-error-600" />
            </div>
            <div className="flex-1 space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Delete Chatbot</h3>
                <p className="mt-2 text-sm text-gray-600">
                  Are you sure you want to delete <strong>{chatbot.name}</strong>? This action cannot be undone.
                </p>
                <p className="mt-2 text-sm text-gray-500">
                  All conversations, analytics, and settings associated with this chatbot will be permanently deleted.
                </p>
              </div>

              {error && (
                <div className="p-3 bg-error-50 border border-error-200 rounded-lg">
                  <p className="text-sm text-error-700">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDelete}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    'Delete Chatbot'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}