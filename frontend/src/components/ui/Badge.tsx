import React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const badgeVariants = cva(
  'inline-flex items-center justify-center rounded-full px-2 py-1 text-xs font-medium transition-all duration-200',
  {
    variants: {
      variant: {
        default: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
        primary: 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-sm',
        secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
        success: 'bg-gradient-to-r from-success-500 to-success-600 text-white shadow-sm',
        warning: 'bg-gradient-to-r from-warning-500 to-warning-600 text-white shadow-sm',
        error: 'bg-gradient-to-r from-error-500 to-error-600 text-white shadow-sm',
        accent: 'bg-gradient-to-r from-accent-500 to-accent-600 text-white shadow-sm',
        outline: 'border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50',
        'outline-primary': 'border border-primary-300 bg-transparent text-primary-700 hover:bg-primary-50',
        'outline-success': 'border border-success-300 bg-transparent text-success-700 hover:bg-success-50',
        'outline-warning': 'border border-warning-300 bg-transparent text-warning-700 hover:bg-warning-50',
        'outline-error': 'border border-error-300 bg-transparent text-error-700 hover:bg-error-50',
        ghost: 'bg-transparent text-gray-600 hover:bg-gray-100',
        elegant: 'bg-gradient-to-r from-white to-gray-50 text-gray-700 border border-gray-200 shadow-sm hover:shadow-md'
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2 py-1 text-xs',
        lg: 'px-3 py-1.5 text-sm'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'md'
    }
  }
)

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {
  children: React.ReactNode
  icon?: React.ReactNode
  pulse?: boolean
}

export function Badge({ 
  className, 
  variant, 
  size, 
  children, 
  icon,
  pulse = false,
  ...props 
}: BadgeProps) {
  return (
    <div 
      className={cn(
        badgeVariants({ variant, size }), 
        pulse && 'animate-pulse-gentle',
        className
      )} 
      {...props}
    >
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </div>
  )
}

// Status badge variants
export function StatusBadge({ 
  status,
  className = ''
}: { 
  status: 'active' | 'inactive' | 'pending' | 'error' | 'training' | 'completed'
  className?: string
}) {
  const statusConfig = {
    active: {
      variant: 'success' as const,
      label: 'Active',
      pulse: true
    },
    inactive: {
      variant: 'default' as const,
      label: 'Inactive',
      pulse: false
    },
    pending: {
      variant: 'warning' as const,
      label: 'Pending',
      pulse: true
    },
    error: {
      variant: 'error' as const,
      label: 'Error',
      pulse: false
    },
    training: {
      variant: 'accent' as const,
      label: 'Training',
      pulse: true
    },
    completed: {
      variant: 'primary' as const,
      label: 'Completed',
      pulse: false
    }
  }

  const config = statusConfig[status] || statusConfig.inactive

  return (
    <Badge
      variant={config.variant}
      pulse={config.pulse}
      className={className}
    >
      {config.label}
    </Badge>
  )
}

// Plan badge for subscription tiers
export function PlanBadge({ 
  plan,
  className = ''
}: { 
  plan: 'free' | 'pro' | 'enterprise'
  className?: string
}) {
  const planConfig = {
    free: {
      variant: 'outline' as const,
      label: 'Free',
      icon: null
    },
    pro: {
      variant: 'primary' as const,
      label: 'Pro',
      icon: <span className="text-xs">⭐</span>
    },
    enterprise: {
      variant: 'elegant' as const,
      label: 'Enterprise',
      icon: <span className="text-xs">💎</span>
    }
  }

  const config = planConfig[plan] || planConfig.free

  return (
    <Badge
      variant={config.variant}
      icon={config.icon}
      className={className}
    >
      {config.label}
    </Badge>
  )
}

// Notification badge with count
export function NotificationBadge({ 
  count,
  max = 99,
  className = ''
}: { 
  count: number
  max?: number
  className?: string
}) {
  if (count === 0) return null

  const displayCount = count > max ? `${max}+` : count.toString()

  return (
    <Badge
      variant="error"
      size="sm"
      className={`animate-bounce-gentle ${className}`}
    >
      {displayCount}
    </Badge>
  )
}

// Performance badge with color coding
export function PerformanceBadge({ 
  score,
  className = ''
}: { 
  score: number
  className?: string
}) {
  const getVariant = (score: number) => {
    if (score >= 95) return 'success'
    if (score >= 80) return 'primary' 
    if (score >= 60) return 'warning'
    return 'error'
  }

  const getLabel = (score: number) => {
    if (score >= 95) return 'Excellent'
    if (score >= 80) return 'Good'
    if (score >= 60) return 'Fair'
    return 'Needs Improvement'
  }

  return (
    <Badge
      variant={getVariant(score)}
      className={className}
    >
      {score}% {getLabel(score)}
    </Badge>
  )
}