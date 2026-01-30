import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  Plus,
  Upload,
  Link,
  Code,
  Sparkles,
  ArrowUpRight
} from 'lucide-react'

interface QuickAction {
  id: string
  title: string
  description: string
  icon: React.ElementType
  color: 'violet' | 'fuchsia' | 'cyan' | 'emerald' | 'amber'
  onClick?: () => void
  isNew?: boolean
}

const getDefaultActions = (t: (key: string) => string): QuickAction[] => [
  {
    id: 'create-chatbot',
    title: t('dashboard.quickActions.createChatbot'),
    description: t('dashboard.quickActions.createChatbotDesc'),
    icon: Plus,
    color: 'violet'
  },
  {
    id: 'upload-docs',
    title: t('dashboard.quickActions.uploadDocs'),
    description: t('dashboard.quickActions.uploadDocsDesc'),
    icon: Upload,
    color: 'fuchsia'
  },
  {
    id: 'add-url',
    title: t('dashboard.quickActions.addUrl'),
    description: t('dashboard.quickActions.addUrlDesc'),
    icon: Link,
    color: 'cyan'
  },
  {
    id: 'get-embed',
    title: t('dashboard.quickActions.getEmbed'),
    description: t('dashboard.quickActions.getEmbedDesc'),
    icon: Code,
    color: 'emerald'
  }
]

const colorClasses = {
  violet: {
    bg: 'bg-violet-500/10 hover:bg-violet-500/20',
    icon: 'bg-violet-500/20 text-violet-400 group-hover:bg-violet-500/30',
    border: 'border-violet-500/20 hover:border-violet-500/40'
  },
  fuchsia: {
    bg: 'bg-fuchsia-500/10 hover:bg-fuchsia-500/20',
    icon: 'bg-fuchsia-500/20 text-fuchsia-400 group-hover:bg-fuchsia-500/30',
    border: 'border-fuchsia-500/20 hover:border-fuchsia-500/40'
  },
  cyan: {
    bg: 'bg-cyan-500/10 hover:bg-cyan-500/20',
    icon: 'bg-cyan-500/20 text-cyan-400 group-hover:bg-cyan-500/30',
    border: 'border-cyan-500/20 hover:border-cyan-500/40'
  },
  emerald: {
    bg: 'bg-emerald-500/10 hover:bg-emerald-500/20',
    icon: 'bg-emerald-500/20 text-emerald-400 group-hover:bg-emerald-500/30',
    border: 'border-emerald-500/20 hover:border-emerald-500/40'
  },
  amber: {
    bg: 'bg-amber-500/10 hover:bg-amber-500/20',
    icon: 'bg-amber-500/20 text-amber-400 group-hover:bg-amber-500/30',
    border: 'border-amber-500/20 hover:border-amber-500/40'
  }
}

interface QuickActionsProps {
  actions?: QuickAction[]
  onCreateChatbot?: () => void
  onUploadDocs?: () => void
  onAddUrl?: () => void
  onGetEmbed?: () => void
}

export function QuickActions({
  actions,
  onCreateChatbot,
  onUploadDocs,
  onAddUrl,
  onGetEmbed
}: QuickActionsProps) {
  const { t } = useTranslation()
  const defaultActions = getDefaultActions(t)
  const displayActions = actions || defaultActions
  const handleClick = (actionId: string) => {
    switch (actionId) {
      case 'create-chatbot':
        onCreateChatbot?.()
        break
      case 'upload-docs':
        onUploadDocs?.()
        break
      case 'add-url':
        onAddUrl?.()
        break
      case 'get-embed':
        onGetEmbed?.()
        break
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1 }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold text-white">{t('dashboard.quickActions.title')}</h3>
          <p className="text-sm text-slate-500">{t('dashboard.quickActions.subtitle')}</p>
        </div>
        <div className="p-2 rounded-lg bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20">
          <Sparkles className="w-4 h-4 text-violet-400" />
        </div>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 gap-3"
      >
        {displayActions.map((action) => {
          const colors = colorClasses[action.color]
          const Icon = action.icon

          return (
            <motion.button
              key={action.id}
              variants={itemVariants}
              onClick={() => handleClick(action.id)}
              className={`
                group relative p-4 rounded-xl text-left
                border ${colors.border}
                ${colors.bg}
                transition-all duration-200
              `}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${colors.icon} transition-colors duration-200`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-white truncate">
                      {action.title}
                    </h4>
                    {action.isNew && (
                      <span className="px-1.5 py-0.5 text-[10px] font-bold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded uppercase">
                        New
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-0.5">
                    {action.description}
                  </p>
                </div>
              </div>

              {/* Hover arrow */}
              <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <ArrowUpRight className="w-4 h-4 text-slate-500" />
              </div>
            </motion.button>
          )
        })}
      </motion.div>
    </motion.div>
  )
}

// Larger action card for featured actions
interface FeaturedActionProps {
  title: string
  description: string
  icon: React.ElementType
  buttonText: string
  onClick?: () => void
  gradient?: string
}

export function FeaturedAction({
  title,
  description,
  icon: Icon,
  buttonText,
  onClick,
  gradient = 'from-violet-500 to-fuchsia-500'
}: FeaturedActionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 p-6"
    >
      {/* Background decoration */}
      <div className={`absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br ${gradient} rounded-full blur-3xl opacity-30`} />

      <div className="relative z-10 flex items-start justify-between">
        <div className="flex-1">
          <div className={`inline-flex p-3 rounded-xl bg-gradient-to-br ${gradient} mb-4`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
          <p className="text-sm text-slate-400 mb-4 max-w-sm">{description}</p>
          <motion.button
            onClick={onClick}
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-lg
              bg-gradient-to-r ${gradient} text-white text-sm font-medium
              hover:opacity-90 transition-opacity
            `}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {buttonText}
            <ArrowUpRight className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}
