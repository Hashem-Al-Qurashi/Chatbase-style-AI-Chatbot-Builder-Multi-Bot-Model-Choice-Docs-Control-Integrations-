import { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const [embedType, setEmbedType] = useState<'bubble' | 'inline'>('bubble')

  // Generate embed code based on type
  const getEmbedCode = () => {
    const baseUrl = window.location.origin
    const chatbotSlug = chatbot.public_url_slug || chatbot.id
    
    if (embedType === 'bubble') {
      return `<!-- Chatbot Widget - ${chatbot.name} -->
<script>
  (function() {
    var script = document.createElement('script');
    script.src = '${baseUrl}/widget/chatbot-widget.js';
    script.setAttribute('data-chatbot-slug', '${chatbotSlug}');
    script.setAttribute('data-position', 'bottom-right');
    script.setAttribute('data-primary-color', '#007bff');
    script.async = true;
    document.head.appendChild(script);
  })();
</script>
<!-- End Chatbot Widget -->`
    } else {
      return `<!-- Inline Chatbot - ${chatbot.name} -->
<iframe
  src="${baseUrl}/widget/${chatbotSlug}"
  width="100%"
  height="600"
  frameborder="0"
  style="border: 1px solid #e5e7eb; border-radius: 8px;"
  title="${chatbot.name} - AI Assistant"
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
              <div className="flex items-center space-x-3 rtl:space-x-reverse">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <Code className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {t('embedModal.title')}
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
                {t('embedModal.chooseType')}
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
                    <h4 className="font-medium text-gray-900">{t('embedModal.chatBubble')}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {t('embedModal.chatBubbleDesc')}
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
                    <h4 className="font-medium text-gray-900">{t('embedModal.inlineFrame')}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {t('embedModal.inlineFrameDesc')}
                    </p>
                  </div>
                </Card>
              </div>
            </div>

            {/* Instructions */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                {t('embedModal.instructions')}
              </h3>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <ol className="text-sm text-blue-900 space-y-2">
                  <li>
                    <span className="font-medium">1.</span> {t('embedModal.step1')}
                  </li>
                  <li>
                    <span className="font-medium">2.</span> {embedType === 'bubble'
                      ? t('embedModal.step2bubble')
                      : t('embedModal.step2inline')
                    }
                  </li>
                  <li>
                    <span className="font-medium">3.</span> {t('embedModal.step3')}
                  </li>
                  <li>
                    <span className="font-medium">4.</span> {t('embedModal.step4')}
                  </li>
                </ol>
              </div>
            </div>

            {/* Embed Code */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-700">
                  {t('embedModal.embedCode')}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="text-primary-600 hover:text-primary-700"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2" />
                      {t('embedModal.copied')}
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2 rtl:mr-0 rtl:ml-2" />
                      {t('embedModal.copyCode')}
                    </>
                  )}
                </Button>
              </div>

              <div className="relative">
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm" dir="ltr">
                  <code>{getEmbedCode()}</code>
                </pre>
              </div>
            </div>

            {/* Preview Note */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                {t('embedModal.previewTitle')}
              </h4>
              <p className="text-sm text-gray-600">
                {embedType === 'bubble'
                  ? t('embedModal.previewBubble')
                  : t('embedModal.previewInline')
                }
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  {t('embedModal.mobileResponsive')}
                </span>
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  {t('embedModal.secureConnection')}
                </span>
                <span className="px-2 py-1 bg-white rounded text-xs text-gray-600">
                  {t('embedModal.noSetup')}
                </span>
              </div>
            </div>

            {/* Support Link */}
            <div className="text-center pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                {t('embedModal.needHelp')}{' '}
                <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
                  {t('embedModal.viewDocs')}
                </a>
                {' '}{t('common.or')}{' '}
                <a href="#" className="text-primary-600 hover:text-primary-700 font-medium">
                  {t('embedModal.contactSupport')}
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}