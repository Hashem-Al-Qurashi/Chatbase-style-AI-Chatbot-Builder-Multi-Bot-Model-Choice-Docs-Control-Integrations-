import React, { useEffect } from 'react'
import { X } from 'lucide-react'
import { Button } from './Button'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  className?: string
  showCloseButton?: boolean
  closeOnOverlayClick?: boolean
}

export function Modal({ 
  isOpen, 
  onClose, 
  title,
  description,
  children, 
  size = 'md',
  className = '',
  showCloseButton = true,
  closeOnOverlayClick = true
}: ModalProps) {
  // Handle ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4'
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && closeOnOverlayClick) {
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop with blur */}
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-md animate-fade-in"
        onClick={handleOverlayClick}
      />

      {/* Modal */}
      <div className={`relative w-full ${sizeClasses[size]} mx-4 animate-scale-in ${className}`}>
        {/* Ambient glow effects */}
        <div className="absolute -inset-4 pointer-events-none overflow-hidden">
          <div className="absolute -top-20 -left-20 w-40 h-40 bg-violet-500/20 rounded-full blur-[80px]" />
          <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-fuchsia-500/20 rounded-full blur-[80px]" />
        </div>

        <div className="relative bg-slate-900/95 backdrop-blur-xl rounded-2xl shadow-2xl shadow-slate-950/50 border border-white/10 overflow-hidden">
          {/* Header */}
          {(title || showCloseButton) && (
            <div className="px-6 py-4 border-b border-white/10 bg-gradient-to-r from-white/5 via-white/[0.07] to-white/5">
              <div className="flex items-center justify-between">
                <div>
                  {title && (
                    <h3 className="text-lg font-semibold text-white">{title}</h3>
                  )}
                  {description && (
                    <p className="text-sm text-slate-400 mt-1">{description}</p>
                  )}
                </div>

                {showCloseButton && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Content */}
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

// Modal variants for common use cases
export function ConfirmationModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = 'Confirm Action',
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'danger'
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  type?: 'danger' | 'warning' | 'info'
}) {
  const buttonVariant = type === 'danger' ? 'primary' : 'primary'

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
    >
      <div className="space-y-6">
        <p className="text-gray-700">{message}</p>
        
        <div className="flex items-center justify-end space-x-3">
          <Button variant="ghost" onClick={onClose}>
            {cancelText}
          </Button>
          <Button variant={buttonVariant} onClick={onConfirm}>
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export function LoadingModal({ 
  isOpen, 
  title = 'Processing',
  message = 'Please wait...'
}: {
  isOpen: boolean
  title?: string
  message?: string
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {}}
      title={title}
      size="sm"
      showCloseButton={false}
      closeOnOverlayClick={false}
    >
      <div className="flex items-center justify-center space-x-3 py-4">
        <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>
        <span className="text-gray-700">{message}</span>
      </div>
    </Modal>
  )
}