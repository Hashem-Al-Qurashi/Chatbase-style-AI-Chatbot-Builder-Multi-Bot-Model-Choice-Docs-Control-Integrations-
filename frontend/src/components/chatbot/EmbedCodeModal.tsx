import { useState } from 'react'
import { X, Code, Copy, Check, Globe, MessageSquare } from 'lucide-react'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { Card } from '../ui/Card'
import { Chatbot } from '../../types'

interface EmbedCodeModalProps {
  chatbot: Chatbot
  isOpen: boolean
  onClose: () => void
}

export function EmbedCodeModal({ chatbot, isOpen, onClose }: EmbedCodeModalProps) {
  const [copied, setCopied] = useState(false)
  const [embedType, setEmbedType] = useState<'bubble' | 'inline'>('bubble')

  // Generate embed code based on type
  const getEmbedCode = () => {
    const baseUrl = window.location.origin
    const chatbotId = chatbot.id
    
    if (embedType === 'bubble') {
      return `<!-- Chatbot Widget - ${chatbot.name} -->
<script>
  (function() {
    var script = document.createElement('script');
    script.src = '${baseUrl}/widget/chatbot-widget.js';
    script.setAttribute('data-chatbot-id', '${chatbotId}');
    script.setAttribute('data-position', 'bottom-right');
    script.async = true;
    document.head.appendChild(script);
  })();
</script>
<!-- End Chatbot Widget -->`
    } else {
      return `<!-- Inline Chatbot - ${chatbot.name} -->
<iframe
  src="${baseUrl}/embed/${chatbotId}"
  width="100%"
  height="600"
  frameborder="0"
  style="border: 1px solid #e5e7eb; border-radius: 8px;"
></iframe>
<!-- End Inline Chatbot -->`
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(getEmbedCode())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="w-full max-w-3xl mx-auto">
        <div className="bg-white rounded-xl shadow-xl">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <Code className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Embed Your Chatbot
                  </h2>
                  <p className="text-sm text-gray-500">{chatbot.name}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Embed Type Selection */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Choose Embed Type
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <Card 
                  className={`cursor-pointer transition-all ${
                    embedType === 'bubble' 
                      ? 'ring-2 ring-primary-500 bg-primary-50' 
                      : 'hover:shadow-md'
                  }`}
                  onClick={() => setEmbedType('bubble')}
                >
                  <div className="p-4 text-center">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 text-primary-600" />
                    <h4 className="font-medium text-gray-900">Chat Bubble</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Floating bubble in corner of your website
                    </p>
                  </div>
                </Card>
                
                <Card 
                  className={`cursor-pointer transition-all ${
                    embedType === 'inline' 
                      ? 'ring-2 ring-primary-500 bg-primary-50' 
                      : 'hover:shadow-md'
                  }`}
                  onClick={() => setEmbedType('inline')}
                >
                  <div className="p-4 text-center">
                    <Globe className="w-8 h-8 mx-auto mb-2 text-primary-600" />
                    <h4 className="font-medium text-gray-900">Inline Frame</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Embedded directly in your page
                    </p>
                  </div>
                </Card>
              </div>
            </div>

            {/* Instructions */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Installation Instructions
              </h3>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <ol className="text-sm text-blue-900 space-y-2">
                  <li>
                    <span className="font-medium">1.</span> Copy the code below
                  </li>
                  <li>
                    <span className="font-medium">2.</span> Paste it into your website's HTML
                    {embedType === 'bubble' 
                      ? ' (preferably before the closing </body> tag)'
                      : ' where you want the chat to appear'
                    }
                  </li>
                  <li>
                    <span className="font-medium">3.</span> Save and publish your changes
                  </li>
                  <li>
                    <span className="font-medium">4.</span> Your chatbot is now live! 🎉
                  </li>
                </ol>
              </div>
            </div>

            {/* Embed Code */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-700">
                  Embed Code
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="text-primary-600 hover:text-primary-700"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copy Code
                    </>
                  )}
                </Button>
              </div>
              
              <div className="relative">
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm">
                  <code>{getEmbedCode()}</code>
                </pre>
              </div>
            </div>

            {/* Preview Note */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                Preview & Customization
              </h4>
              <p className="text-sm text-gray-600">
                {embedType === 'bubble' 
                  ? 'The chat bubble will appear in the bottom-right corner of your website. Users can click it to start chatting.'
                  : 'The chat interface will be embedded directly into your page. You can adjust the width and height values in the code.'
                }
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  Mobile Responsive ✓
                </span>
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  Secure Connection ✓
                </span>
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  No Setup Required ✓
                </span>
              </div>
            </div>

            {/* Support Link */}
            <div className="text-center pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                Need help with integration?{' '}
                <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
                  View documentation
                </a>
                {' or '}
                <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
                  contact support
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}