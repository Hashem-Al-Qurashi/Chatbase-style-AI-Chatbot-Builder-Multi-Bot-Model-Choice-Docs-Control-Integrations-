import { motion } from 'framer-motion'
import {
  MessageSquare,
  Bot,
  FileText,
  UserPlus,
  Zap,
  CheckCircle,
  AlertCircle,
  Clock,
  ArrowRight
} from 'lucide-react'

interface Activity {
  id: string
  type: 'conversation' | 'chatbot' | 'knowledge' | 'user' | 'system'
  title: string
  description: string
  time: string
  status?: 'success' | 'warning' | 'error' | 'pending'
  metadata?: {
    chatbotName?: string
    messageCount?: number
    source?: string
  }
}

const mockActivities: Activity[] = [
  {
    id: '1',
    type: 'conversation',
    title: 'New conversation started',
    description: 'Customer inquiry about pricing plans',
    time: '2 minutes ago',
    status: 'success',
    metadata: { chatbotName: 'Support Bot', messageCount: 5 }
  },
  {
    id: '2',
    type: 'knowledge',
    title: 'Knowledge base updated',
    description: 'Added 3 new documents to FAQ sources',
    time: '15 minutes ago',
    status: 'success',
    metadata: { source: 'Manual upload' }
  },
  {
    id: '3',
    type: 'chatbot',
    title: 'Chatbot training completed',
    description: 'Sales Assistant is now ready to use',
    time: '1 hour ago',
    status: 'success',
    metadata: { chatbotName: 'Sales Assistant' }
  },
  {
    id: '4',
    type: 'system',
    title: 'Credits running low',
    description: 'You have 12 credits remaining this month',
    time: '2 hours ago',
    status: 'warning'
  },
  {
    id: '5',
    type: 'conversation',
    title: 'High satisfaction rating',
    description: 'User rated conversation 5 stars',
    time: '3 hours ago',
    status: 'success',
    metadata: { chatbotName: 'Support Bot' }
  }
]

const typeIcons = {
  conversation: MessageSquare,
  chatbot: Bot,
  knowledge: FileText,
  user: UserPlus,
  system: Zap
}

const statusColors = {
  success: {
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-400',
    icon: CheckCircle
  },
  warning: {
    bg: 'bg-amber-500/20',
    text: 'text-amber-400',
    icon: AlertCircle
  },
  error: {
    bg: 'bg-rose-500/20',
    text: 'text-rose-400',
    icon: AlertCircle
  },
  pending: {
    bg: 'bg-slate-500/20',
    text: 'text-slate-400',
    icon: Clock
  }
}

const typeColors = {
  conversation: 'bg-violet-500/20 text-violet-400',
  chatbot: 'bg-fuchsia-500/20 text-fuchsia-400',
  knowledge: 'bg-cyan-500/20 text-cyan-400',
  user: 'bg-emerald-500/20 text-emerald-400',
  system: 'bg-amber-500/20 text-amber-400'
}

interface ActivityFeedProps {
  activities?: Activity[]
  maxItems?: number
  showViewAll?: boolean
  onViewAll?: () => void
}

export function ActivityFeed({
  activities = mockActivities,
  maxItems = 5,
  showViewAll = true,
  onViewAll
}: ActivityFeedProps) {
  const displayedActivities = activities.slice(0, maxItems)

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0 }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
          <p className="text-sm text-slate-500">Your latest actions and events</p>
        </div>
        {showViewAll && (
          <motion.button
            onClick={onViewAll}
            className="flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300 transition-colors"
            whileHover={{ x: 4 }}
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        )}
      </div>

      {/* Activity List */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="divide-y divide-white/5"
      >
        {displayedActivities.map((activity) => {
          const TypeIcon = typeIcons[activity.type]
          const StatusIcon = activity.status ? statusColors[activity.status].icon : null

          return (
            <motion.div
              key={activity.id}
              variants={itemVariants}
              className="px-6 py-4 hover:bg-white/5 transition-colors cursor-pointer group"
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`p-2.5 rounded-xl ${typeColors[activity.type]} shrink-0`}>
                  <TypeIcon className="w-4 h-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-medium text-white truncate">
                      {activity.title}
                    </h4>
                    {activity.status && StatusIcon && (
                      <StatusIcon className={`w-3.5 h-3.5 ${statusColors[activity.status].text}`} />
                    )}
                  </div>
                  <p className="text-sm text-slate-500 truncate">
                    {activity.description}
                  </p>
                  {activity.metadata && (
                    <div className="flex items-center gap-3 mt-2">
                      {activity.metadata.chatbotName && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-white/5 text-slate-400">
                          {activity.metadata.chatbotName}
                        </span>
                      )}
                      {activity.metadata.messageCount && (
                        <span className="text-xs text-slate-500">
                          {activity.metadata.messageCount} messages
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Time */}
                <span className="text-xs text-slate-500 shrink-0">
                  {activity.time}
                </span>
              </div>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Empty State */}
      {displayedActivities.length === 0 && (
        <div className="px-6 py-12 text-center">
          <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mx-auto mb-4">
            <Clock className="w-6 h-6 text-slate-500" />
          </div>
          <h4 className="text-sm font-medium text-white mb-1">No recent activity</h4>
          <p className="text-sm text-slate-500">
            Your recent actions will appear here
          </p>
        </div>
      )}
    </motion.div>
  )
}

// Skeleton loader
export function ActivityFeedSkeleton() {
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
      <div className="px-6 py-4 border-b border-white/10">
        <div className="w-32 h-5 rounded bg-white/10 animate-pulse mb-2" />
        <div className="w-48 h-4 rounded bg-white/10 animate-pulse" />
      </div>
      <div className="divide-y divide-white/5">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="px-6 py-4 flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-white/10 animate-pulse" />
            <div className="flex-1">
              <div className="w-40 h-4 rounded bg-white/10 animate-pulse mb-2" />
              <div className="w-64 h-3 rounded bg-white/10 animate-pulse" />
            </div>
            <div className="w-20 h-3 rounded bg-white/10 animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}
