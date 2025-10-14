import React, { useState, useEffect } from 'react'
import { Check, X, AlertTriangle, Info } from 'lucide-react'

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

interface ToastProps extends Omit<Toast, 'id'> {
  onClose: () => void
  isVisible: boolean
}

export function ToastComponent({ 
  type, 
  title, 
  message, 
  duration = 5000, 
  onClose,
  isVisible 
}: ToastProps) {
  useEffect(() => {
    if (isVisible && duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [isVisible, duration, onClose])

  const typeConfig = {
    success: {
      icon: Check,
      bgColor: 'from-success-50 to-success-100',
      borderColor: 'border-success-200',
      textColor: 'text-success-700',
      iconColor: 'text-success-500',
      iconBg: 'bg-success-100'
    },
    error: {
      icon: X,
      bgColor: 'from-error-50 to-error-100',
      borderColor: 'border-error-200',
      textColor: 'text-error-700',
      iconColor: 'text-error-500',
      iconBg: 'bg-error-100'
    },
    warning: {
      icon: AlertTriangle,
      bgColor: 'from-warning-50 to-warning-100',
      borderColor: 'border-warning-200',
      textColor: 'text-warning-700',
      iconColor: 'text-warning-500',
      iconBg: 'bg-warning-100'
    },
    info: {
      icon: Info,
      bgColor: 'from-primary-50 to-primary-100',
      borderColor: 'border-primary-200',
      textColor: 'text-primary-700',
      iconColor: 'text-primary-500',
      iconBg: 'bg-primary-100'
    }
  }

  const config = typeConfig[type]
  const Icon = config.icon

  return (
    <div className={`
      fixed top-4 right-4 z-50 max-w-sm w-full
      transform transition-all duration-300 ease-out
      ${isVisible 
        ? 'translate-x-0 opacity-100 scale-100' 
        : 'translate-x-full opacity-0 scale-95'
      }
    `}>
      <div className={`
        bg-gradient-to-r ${config.bgColor} 
        border ${config.borderColor} 
        rounded-xl shadow-elegant p-4
        backdrop-blur-sm
      `}>
        <div className="flex items-start space-x-3">
          <div className={`${config.iconBg} rounded-lg p-2 flex-shrink-0`}>
            <Icon className={`w-4 h-4 ${config.iconColor}`} />
          </div>
          
          <div className="flex-1 space-y-1">
            <h4 className={`font-semibold ${config.textColor}`}>
              {title}
            </h4>
            {message && (
              <p className={`text-sm ${config.textColor} opacity-90`}>
                {message}
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            className={`${config.textColor} hover:opacity-70 transition-opacity p-1`}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {/* Progress bar */}
        {duration > 0 && (
          <div className="mt-3 w-full bg-white/30 rounded-full h-1">
            <div 
              className={`h-1 rounded-full ${config.iconColor.replace('text-', 'bg-')} transition-all ease-linear`}
              style={{ 
                animation: `shrink ${duration}ms linear forwards`
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

// Toast container and hook for managing toasts
interface ToastContextType {
  showToast: (toast: Omit<Toast, 'id'>) => void
  showSuccess: (title: string, message?: string) => void
  showError: (title: string, message?: string) => void
  showWarning: (title: string, message?: string) => void
  showInfo: (title: string, message?: string) => void
}

const ToastContext = React.createContext<ToastContextType | null>(null)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = (toast: Omit<Toast, 'id'>) => {
    const id = Date.now().toString()
    const newToast = { ...toast, id }
    setToasts(prev => [...prev, newToast])
  }

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }

  const showSuccess = (title: string, message?: string) => {
    showToast({ type: 'success', title, message })
  }

  const showError = (title: string, message?: string) => {
    showToast({ type: 'error', title, message })
  }

  const showWarning = (title: string, message?: string) => {
    showToast({ type: 'warning', title, message })
  }

  const showInfo = (title: string, message?: string) => {
    showToast({ type: 'info', title, message })
  }

  return (
    <ToastContext.Provider value={{ 
      showToast, 
      showSuccess, 
      showError, 
      showWarning, 
      showInfo 
    }}>
      {children}
      
      {/* Toast container */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <ToastComponent
            key={toast.id}
            type={toast.type}
            title={toast.title}
            message={toast.message}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
            isVisible={true}
          />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

// CSS keyframes for progress bar animation
const style = `
@keyframes shrink {
  from { width: 100%; }
  to { width: 0%; }
}
`

// Inject CSS if not already present
if (typeof document !== 'undefined' && !document.querySelector('#toast-styles')) {
  const styleElement = document.createElement('style')
  styleElement.id = 'toast-styles'
  styleElement.innerHTML = style
  document.head.appendChild(styleElement)
}