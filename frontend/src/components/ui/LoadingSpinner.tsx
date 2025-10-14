import { Loader2, Bot, Sparkles } from 'lucide-react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  variant?: 'default' | 'elegant' | 'minimal' | 'branded'
  message?: string
  className?: string
}

export function LoadingSpinner({ 
  size = 'md', 
  variant = 'default',
  message,
  className = ''
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  }

  const messageSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
    xl: 'text-lg'
  }

  if (variant === 'minimal') {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <Loader2 className={`${sizeClasses[size]} animate-spin text-primary-600`} />
      </div>
    )
  }

  if (variant === 'branded') {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="text-center space-y-4 animate-fade-in">
          <div className="relative">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/25 animate-pulse-gentle">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <div className="absolute -top-2 -right-2 w-6 h-6 bg-gradient-to-br from-accent-400 to-primary-400 rounded-full flex items-center justify-center animate-bounce-gentle">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
          </div>
          
          {message && (
            <div className="space-y-2">
              <p className="text-lg font-semibold text-gray-800">{message}</p>
              <div className="flex items-center justify-center space-x-1">
                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}} />
                <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}} />
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (variant === 'elegant') {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="text-center space-y-4 animate-fade-in">
          <div className="relative">
            <div className="w-12 h-12 mx-auto rounded-full border-2 border-gray-200">
              <div className="w-12 h-12 rounded-full border-2 border-primary-500 border-t-transparent animate-spin" />
            </div>
            <div className="absolute inset-0 w-12 h-12 mx-auto bg-gradient-to-br from-primary-500/10 to-accent-500/10 rounded-full blur animate-pulse" />
          </div>
          
          {message && (
            <p className={`font-medium text-gray-700 ${messageSizes[size]}`}>
              {message}
            </p>
          )}
        </div>
      </div>
    )
  }

  // Default variant
  return (
    <div className={`flex items-center justify-center space-x-3 ${className}`}>
      <Loader2 className={`${sizeClasses[size]} animate-spin text-primary-600`} />
      {message && (
        <span className={`font-medium text-gray-700 ${messageSizes[size]}`}>
          {message}
        </span>
      )}
    </div>
  )
}

// Full screen loading overlay
export function LoadingOverlay({ 
  isLoading, 
  message = 'Loading...',
  variant = 'branded'
}: {
  isLoading: boolean
  message?: string
  variant?: 'default' | 'elegant' | 'minimal' | 'branded'
}) {
  if (!isLoading) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm animate-fade-in">
      <LoadingSpinner 
        size="xl" 
        variant={variant}
        message={message}
      />
    </div>
  )
}

// Skeleton loading for content
export function SkeletonLoader({ 
  lines = 3,
  className = ''
}: {
  lines?: number
  className?: string
}) {
  return (
    <div className={`animate-pulse space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div key={index} className="space-y-2">
          <div className={`h-4 bg-gray-200 rounded ${
            index === 0 ? 'w-3/4' : 
            index === 1 ? 'w-full' :
            'w-2/3'
          }`} />
        </div>
      ))}
    </div>
  )
}

// Card skeleton
export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-6 animate-pulse ${className}`}>
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gray-200 rounded-lg" />
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-gray-200 rounded w-1/3" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded w-full" />
          <div className="h-3 bg-gray-200 rounded w-4/5" />
          <div className="h-3 bg-gray-200 rounded w-2/3" />
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="h-8 bg-gray-200 rounded w-20" />
          <div className="h-8 bg-gray-200 rounded w-16" />
        </div>
      </div>
    </div>
  )
}