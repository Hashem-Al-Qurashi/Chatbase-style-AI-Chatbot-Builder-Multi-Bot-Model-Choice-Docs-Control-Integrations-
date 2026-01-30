import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Bot,
  MessageSquare,
  Database,
  BarChart3,
  Plug,
  Settings,
  CreditCard,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Search,
  Bell,
  Moon,
  Sun,
  Sparkles,
  User,
  HelpCircle,
  ExternalLink
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { LanguageToggle } from '../ui/LanguageToggle'

interface NavItem {
  id: string
  labelKey: string
  icon: React.ElementType
  path: string
  badge?: number | string
  isNew?: boolean
}

const navItemsConfig: NavItem[] = [
  { id: 'dashboard', labelKey: 'sidebar.dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'chatbots', labelKey: 'sidebar.chatbots', icon: Bot, path: '/dashboard/chatbots' },
  { id: 'conversations', labelKey: 'sidebar.conversations', icon: MessageSquare, path: '/dashboard/conversations', badge: 5 },
  { id: 'knowledge', labelKey: 'sidebar.knowledgeBase', icon: Database, path: '/dashboard/knowledge' },
  { id: 'analytics', labelKey: 'sidebar.analytics', icon: BarChart3, path: '/dashboard/analytics', isNew: true },
  { id: 'integrations', labelKey: 'sidebar.integrations', icon: Plug, path: '/dashboard/integrations' },
]

const bottomNavItemsConfig: NavItem[] = [
  { id: 'settings', labelKey: 'sidebar.settings', icon: Settings, path: '/dashboard/settings' },
  { id: 'billing', labelKey: 'sidebar.billing', icon: CreditCard, path: '/dashboard/billing' },
]

interface DashboardLayoutProps {
  children: React.ReactNode
  activeSection?: string
}

export function DashboardLayout({ children, activeSection = 'dashboard' }: DashboardLayoutProps) {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [darkMode, setDarkMode] = useState(true)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [searchFocused, setSearchFocused] = useState(false)

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchFocused(true)
      }
      if (e.key === 'Escape') {
        setSearchFocused(false)
        setShowUserMenu(false)
        setShowNotifications(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const sidebarVariants = {
    expanded: { width: 260 },
    collapsed: { width: 72 }
  }

  const NavLink = ({ item, isActive }: { item: NavItem; isActive: boolean }) => (
    <motion.button
      onClick={() => navigate(item.path)}
      className={`
        relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
        transition-all duration-200 group
        ${isActive
          ? 'bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 text-white'
          : 'text-slate-400 hover:text-white hover:bg-white/5'
        }
      `}
      whileHover={{ x: 4 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Active indicator */}
      {isActive && (
        <motion.div
          layoutId="activeNav"
          className="absolute left-0 rtl:left-auto rtl:right-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-gradient-to-b from-violet-400 to-fuchsia-400 rounded-full"
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        />
      )}

      <item.icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-violet-400' : ''}`} />

      <AnimatePresence>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 'auto' }}
            exit={{ opacity: 0, width: 0 }}
            className="text-sm font-medium whitespace-nowrap overflow-hidden"
          >
            {t(item.labelKey)}
          </motion.span>
        )}
      </AnimatePresence>

      {/* Badge */}
      {item.badge && !collapsed && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="ml-auto rtl:ml-0 rtl:mr-auto px-2 py-0.5 text-xs font-semibold bg-violet-500/20 text-violet-300 rounded-full"
        >
          {item.badge}
        </motion.span>
      )}

      {/* New badge */}
      {item.isNew && !collapsed && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="ml-auto rtl:ml-0 rtl:mr-auto px-2 py-0.5 text-[10px] font-bold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-full uppercase tracking-wide"
        >
          {t('sidebar.new')}
        </motion.span>
      )}

      {/* Tooltip for collapsed state */}
      {collapsed && (
        <div className="absolute left-full rtl:left-auto rtl:right-full ml-2 rtl:ml-0 rtl:mr-2 px-2 py-1 bg-slate-800 text-white text-sm rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
          {t(item.labelKey)}
        </div>
      )}
    </motion.button>
  )

  return (
    <div className={`min-h-screen flex ${darkMode ? 'bg-slate-950' : 'bg-slate-50'}`}>
      {/* Ambient background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] bg-violet-500/10 rounded-full blur-[120px]" />
        <div className="absolute -bottom-[40%] -right-[20%] w-[80%] h-[80%] bg-fuchsia-500/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] bg-cyan-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Sidebar */}
      <motion.aside
        variants={sidebarVariants}
        animate={collapsed ? 'collapsed' : 'expanded'}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="fixed left-0 top-0 h-screen z-40 flex flex-col border-r border-white/5 bg-slate-900/50 backdrop-blur-xl"
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-white/5">
          <AnimatePresence mode="wait">
            {!collapsed ? (
              <motion.div
                key="full-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-bold text-white">Chatava</span>
              </motion.div>
            ) : (
              <motion.div
                key="icon-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center mx-auto"
              >
                <Sparkles className="w-4 h-4 text-white" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Main Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItemsConfig.map((item) => (
            <NavLink
              key={item.id}
              item={item}
              isActive={activeSection === item.id || location.pathname === item.path}
            />
          ))}
        </nav>

        {/* Bottom Navigation */}
        <div className="p-3 space-y-1 border-t border-white/5">
          {bottomNavItemsConfig.map((item) => (
            <NavLink
              key={item.id}
              item={item}
              isActive={activeSection === item.id || location.pathname === item.path}
            />
          ))}

          {/* Logout Button */}
          <motion.button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.98 }}
          >
            <LogOut className="w-5 h-5 shrink-0" />
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-sm font-medium"
                >
                  {t('sidebar.logout')}
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-20 w-6 h-6 bg-slate-800 border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </motion.aside>

      {/* Main Content Area */}
      <motion.main
        animate={{ marginLeft: collapsed ? 72 : 260 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="flex-1 min-h-screen"
      >
        {/* Top Header */}
        <header className="sticky top-0 z-30 h-16 px-6 flex items-center justify-between border-b border-white/5 bg-slate-950/80 backdrop-blur-xl">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder={t('sidebar.searchPlaceholder')}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              className={`
                w-full pl-10 pr-4 rtl:pl-4 rtl:pr-10 py-2 rounded-xl text-sm
                bg-white/5 border transition-all duration-200
                placeholder:text-slate-500 text-white
                ${searchFocused
                  ? 'border-violet-500/50 ring-2 ring-violet-500/20'
                  : 'border-white/10 hover:border-white/20'
                }
                focus:outline-none
              `}
            />
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Language Toggle */}
            <LanguageToggle variant="compact" />

            {/* Theme Toggle */}
            <motion.button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              whileTap={{ scale: 0.95 }}
            >
              {darkMode ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </motion.button>

            {/* Help */}
            <motion.button
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              whileTap={{ scale: 0.95 }}
            >
              <HelpCircle className="w-5 h-5" />
            </motion.button>

            {/* Notifications */}
            <div className="relative">
              <motion.button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                whileTap={{ scale: 0.95 }}
              >
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-violet-500 rounded-full" />
              </motion.button>

              <AnimatePresence>
                {showNotifications && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 rtl:right-auto rtl:left-0 top-full mt-2 w-80 p-4 bg-slate-900 border border-white/10 rounded-xl shadow-2xl"
                  >
                    <h3 className="text-sm font-semibold text-white mb-3">{t('sidebar.notifications')}</h3>
                    <div className="space-y-3">
                      <div className="flex gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                          <MessageSquare className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-white">{t('sidebar.newConversation')}</p>
                          <p className="text-xs text-slate-500">{t('sidebar.minutesAgo', { count: 2 })}</p>
                        </div>
                      </div>
                      <div className="flex gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
                        <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                          <Bot className="w-4 h-4 text-violet-400" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-white">{t('sidebar.trainingComplete')}</p>
                          <p className="text-xs text-slate-500">{t('sidebar.hourAgo')}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Separator */}
            <div className="w-px h-6 bg-white/10 mx-2" />

            {/* User Menu */}
            <div className="relative">
              <motion.button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-3 p-1.5 pr-3 rtl:pr-1.5 rtl:pl-3 rounded-xl hover:bg-white/5 transition-colors"
                whileTap={{ scale: 0.98 }}
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="text-left rtl:text-right hidden sm:block">
                  <p className="text-sm font-medium text-white">
                    {user?.first_name || user?.email?.split('@')[0] || 'User'}
                  </p>
                  <p className="text-xs text-slate-500">{t('sidebar.freePlan')}</p>
                </div>
              </motion.button>

              <AnimatePresence>
                {showUserMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 rtl:right-auto rtl:left-0 top-full mt-2 w-56 p-2 bg-slate-900 border border-white/10 rounded-xl shadow-2xl"
                  >
                    <div className="px-3 py-2 border-b border-white/10 mb-2">
                      <p className="text-sm font-medium text-white">{user?.email}</p>
                      <p className="text-xs text-slate-500">{t('sidebar.freePlan')} · {t('sidebar.credits', { count: 50 })}</p>
                    </div>
                    <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                      <User className="w-4 h-4" />
                      {t('sidebar.profile')}
                    </button>
                    <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                      <Settings className="w-4 h-4" />
                      {t('sidebar.settings')}
                    </button>
                    <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                      <ExternalLink className="w-4 h-4" />
                      {t('sidebar.documentation')}
                    </button>
                    <div className="border-t border-white/10 mt-2 pt-2">
                      <button
                        onClick={logout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        {t('sidebar.logout')}
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="relative p-6">
          {children}
        </div>
      </motion.main>

      {/* Click outside to close menus */}
      {(showUserMenu || showNotifications) && (
        <div
          className="fixed inset-0 z-20"
          onClick={() => {
            setShowUserMenu(false)
            setShowNotifications(false)
          }}
        />
      )}
    </div>
  )
}
