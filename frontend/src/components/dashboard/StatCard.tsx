import { useEffect, useState, useRef } from 'react'
import { motion, useInView, useSpring } from 'framer-motion'
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number
  suffix?: string
  prefix?: string
  icon: LucideIcon
  trend?: {
    value: number
    isPositive: boolean
  }
  color: 'violet' | 'fuchsia' | 'cyan' | 'emerald' | 'amber' | 'rose'
  delay?: number
  description?: string
}

const colorClasses = {
  violet: {
    bg: 'from-violet-500/20 to-violet-600/10',
    icon: 'bg-violet-500/20 text-violet-400',
    glow: 'shadow-violet-500/20',
    border: 'border-violet-500/20',
    text: 'text-violet-400'
  },
  fuchsia: {
    bg: 'from-fuchsia-500/20 to-fuchsia-600/10',
    icon: 'bg-fuchsia-500/20 text-fuchsia-400',
    glow: 'shadow-fuchsia-500/20',
    border: 'border-fuchsia-500/20',
    text: 'text-fuchsia-400'
  },
  cyan: {
    bg: 'from-cyan-500/20 to-cyan-600/10',
    icon: 'bg-cyan-500/20 text-cyan-400',
    glow: 'shadow-cyan-500/20',
    border: 'border-cyan-500/20',
    text: 'text-cyan-400'
  },
  emerald: {
    bg: 'from-emerald-500/20 to-emerald-600/10',
    icon: 'bg-emerald-500/20 text-emerald-400',
    glow: 'shadow-emerald-500/20',
    border: 'border-emerald-500/20',
    text: 'text-emerald-400'
  },
  amber: {
    bg: 'from-amber-500/20 to-amber-600/10',
    icon: 'bg-amber-500/20 text-amber-400',
    glow: 'shadow-amber-500/20',
    border: 'border-amber-500/20',
    text: 'text-amber-400'
  },
  rose: {
    bg: 'from-rose-500/20 to-rose-600/10',
    icon: 'bg-rose-500/20 text-rose-400',
    glow: 'shadow-rose-500/20',
    border: 'border-rose-500/20',
    text: 'text-rose-400'
  }
}

function AnimatedCounter({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const [displayValue, setDisplayValue] = useState(0)

  const spring = useSpring(0, {
    stiffness: 50,
    damping: 30
  })

  useEffect(() => {
    if (isInView) {
      spring.set(value)
    }
  }, [isInView, value, spring])

  useEffect(() => {
    const unsubscribe = spring.on('change', (latest) => {
      setDisplayValue(Math.round(latest))
    })
    return unsubscribe
  }, [spring])

  return <span ref={ref}>{displayValue.toLocaleString()}</span>
}

export function StatCard({
  title,
  value,
  suffix = '',
  prefix = '',
  icon: Icon,
  trend,
  color,
  delay = 0,
  description
}: StatCardProps) {
  const colors = colorClasses[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`
        relative overflow-hidden rounded-2xl
        bg-gradient-to-br ${colors.bg}
        border ${colors.border}
        backdrop-blur-sm
        p-6 group cursor-default
      `}
    >
      {/* Background glow effect */}
      <div className={`absolute -top-24 -right-24 w-48 h-48 bg-gradient-to-br ${colors.bg} rounded-full blur-3xl opacity-50 group-hover:opacity-75 transition-opacity duration-500`} />

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-xl ${colors.icon}`}>
            <Icon className="w-5 h-5" />
          </div>

          {trend && (
            <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${
              trend.isPositive
                ? 'bg-emerald-500/20 text-emerald-400'
                : trend.value === 0
                  ? 'bg-slate-500/20 text-slate-400'
                  : 'bg-rose-500/20 text-rose-400'
            }`}>
              {trend.isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : trend.value === 0 ? (
                <Minus className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span>{trend.value}%</span>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <h3 className="text-sm font-medium text-slate-400">{title}</h3>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white tracking-tight">
              {prefix}
              <AnimatedCounter value={value} />
              {suffix}
            </span>
          </div>
          {description && (
            <p className="text-xs text-slate-500 mt-2">{description}</p>
          )}
        </div>
      </div>

      {/* Decorative corner */}
      <div className={`absolute bottom-0 right-0 w-24 h-24 bg-gradient-to-tl ${colors.bg} rounded-tl-[80px] opacity-50`} />
    </motion.div>
  )
}

// Skeleton loader for stat cards
export function StatCardSkeleton() {
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-6 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="w-11 h-11 rounded-xl bg-white/10" />
        <div className="w-16 h-6 rounded-lg bg-white/10" />
      </div>
      <div className="space-y-2">
        <div className="w-20 h-4 rounded bg-white/10" />
        <div className="w-32 h-8 rounded bg-white/10" />
      </div>
    </div>
  )
}
