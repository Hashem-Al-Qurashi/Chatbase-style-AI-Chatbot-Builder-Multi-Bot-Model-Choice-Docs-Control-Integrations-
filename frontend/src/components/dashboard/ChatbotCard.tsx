import { motion } from 'framer-motion'
import {
  Bot,
  MessageSquare,
  MoreVertical,
  Play,
  Settings,
  Code,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Zap
} from 'lucide-react'
import { useState } from 'react'
import { Chatbot } from '../../types'

interface ChatbotCardProps {
  chatbot: Chatbot
  onChat?: () => void
  onSettings?: () => void
  onEmbed?: () => void
  onDelete?: () => void
  index?: number
}

const statusConfig = {
  active: {
    color: 'bg-emerald-500',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    label: 'Active',
    icon: CheckCircle
  },
  completed: {
    color: 'bg-emerald-500',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    label: 'Ready',
    icon: CheckCircle
  },
  training: {
    color: 'bg-amber-500',
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
    label: 'Training',
    icon: Zap
  },
  processing: {
    color: 'bg-amber-500',
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
    label: 'Processing',
    icon: Clock
  },
  pending: {
    color: 'bg-slate-500',
    text: 'text-slate-400',
    bg: 'bg-slate-500/10',
    label: 'Pending',
    icon: Clock
  },
  draft: {
    color: 'bg-slate-500',
    text: 'text-slate-400',
    bg: 'bg-slate-500/10',
    label: 'Draft',
    icon: Clock
  },
  error: {
    color: 'bg-rose-500',
    text: 'text-rose-400',
    bg: 'bg-rose-500/10',
    label: 'Error',
    icon: AlertCircle
  }
}

export function ChatbotCard({
  chatbot,
  onChat,
  onSettings,
  onEmbed,
  onDelete,
  index = 0
}: ChatbotCardProps) {
  const [showMenu, setShowMenu] = useState(false)
  const status = statusConfig[chatbot.status] || statusConfig.draft
  const StatusIcon = status.icon

  // Generate consistent gradient based on chatbot name
  const gradients = [
    'from-violet-500 to-fuchsia-500',
    'from-cyan-500 to-blue-500',
    'from-emerald-500 to-teal-500',
    'from-amber-500 to-orange-500',
    'from-rose-500 to-pink-500',
    'from-indigo-500 to-purple-500'
  ]
  const gradientIndex = chatbot.name.length % gradients.length
  const gradient = gradients[gradientIndex]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={{ y: -4 }}
      className="group relative rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 backdrop-blur-sm overflow-hidden transition-all duration-300"
    >
      {/* Top gradient accent */}
      <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${gradient}`} />

      {/* Hover glow effect */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className={`relative w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
              <Bot className="w-6 h-6 text-white" />
              {/* Status indicator */}
              <div className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full ${status.color} border-2 border-slate-900 flex items-center justify-center`}>
                <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
              </div>
            </div>

            <div>
              <h3 className="text-base font-semibold text-white group-hover:text-violet-300 transition-colors">
                {chatbot.name}
              </h3>
              <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md ${status.bg} ${status.text} text-xs font-medium`}>
                <StatusIcon className="w-3 h-3" />
                {status.label}
              </div>
            </div>
          </div>

          {/* Menu */}
          <div className="relative">
            <motion.button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
              whileTap={{ scale: 0.95 }}
            >
              <MoreVertical className="w-4 h-4" />
            </motion.button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute right-0 top-full mt-1 w-48 py-1 bg-slate-800 border border-white/10 rounded-xl shadow-xl z-20"
                >
                  <button
                    onClick={() => { onChat?.(); setShowMenu(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    Start Chat
                  </button>
                  <button
                    onClick={() => { onSettings?.(); setShowMenu(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <button
                    onClick={() => { onEmbed?.(); setShowMenu(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    <Code className="w-4 h-4" />
                    Get Embed Code
                  </button>
                  <div className="border-t border-white/10 my-1" />
                  <button
                    onClick={() => { onDelete?.(); setShowMenu(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </motion.div>
              </>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-500 mb-4 line-clamp-2 min-h-[40px]">
          {chatbot.description || 'No description provided'}
        </p>

        {/* Stats */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-1.5 text-slate-400">
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm">{chatbot.total_conversations || 0}</span>
            <span className="text-xs text-slate-500">chats</span>
          </div>
          {chatbot.total_messages && (
            <div className="flex items-center gap-1.5 text-slate-400">
              <Zap className="w-4 h-4" />
              <span className="text-sm">{chatbot.total_messages}</span>
              <span className="text-xs text-slate-500">messages</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <motion.button
            onClick={onChat}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r ${gradient} text-white text-sm font-medium hover:opacity-90 transition-opacity`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Play className="w-4 h-4" />
            Open Chat
          </motion.button>
          <motion.button
            onClick={onEmbed}
            className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 hover:border-white/20 transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Get Embed Code"
          >
            <Code className="w-4 h-4" />
          </motion.button>
          <motion.button
            onClick={onSettings}
            className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 hover:border-white/20 transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

// Skeleton loader
export function ChatbotCardSkeleton() {
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-5 animate-pulse">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-white/10" />
        <div>
          <div className="w-32 h-5 rounded bg-white/10 mb-2" />
          <div className="w-16 h-4 rounded bg-white/10" />
        </div>
      </div>
      <div className="w-full h-10 rounded bg-white/10 mb-4" />
      <div className="flex gap-4 mb-4">
        <div className="w-20 h-4 rounded bg-white/10" />
        <div className="w-20 h-4 rounded bg-white/10" />
      </div>
      <div className="flex gap-2">
        <div className="flex-1 h-10 rounded-xl bg-white/10" />
        <div className="w-10 h-10 rounded-xl bg-white/10" />
        <div className="w-10 h-10 rounded-xl bg-white/10" />
      </div>
    </div>
  )
}

// Empty state for no chatbots
interface EmptyStateProps {
  onCreateChatbot?: () => void
}

export function ChatbotsEmptyState({ onCreateChatbot }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="col-span-full flex flex-col items-center justify-center py-16 px-8"
    >
      {/* Animated robot illustration */}
      <motion.div
        className="relative mb-6"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-2xl shadow-violet-500/30">
          <Bot className="w-12 h-12 text-white" />
        </div>
        {/* Floating particles */}
        <motion.div
          className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-cyan-400"
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <motion.div
          className="absolute -bottom-1 -left-3 w-3 h-3 rounded-full bg-fuchsia-400"
          animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.5, repeat: Infinity, delay: 0.5 }}
        />
      </motion.div>

      <h3 className="text-xl font-semibold text-white mb-2">
        Create Your First Chatbot
      </h3>
      <p className="text-slate-500 text-center max-w-md mb-6">
        Build intelligent AI assistants that understand your content and provide instant, accurate answers to your customers.
      </p>

      <motion.button
        onClick={onCreateChatbot}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-medium hover:opacity-90 transition-opacity"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Zap className="w-5 h-5" />
        Get Started
      </motion.button>
    </motion.div>
  )
}
