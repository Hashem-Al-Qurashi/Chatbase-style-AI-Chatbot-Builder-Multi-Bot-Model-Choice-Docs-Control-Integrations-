import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import { Languages, Check } from 'lucide-react'

interface Language {
  code: string
  name: string
  nativeName: string
  flag: string
}

const languages: Language[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦' }
]

interface LanguageToggleProps {
  variant?: 'default' | 'compact'
  className?: string
}

export function LanguageToggle({ variant = 'default', className = '' }: LanguageToggleProps) {
  const { i18n } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0]

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode)
    setIsOpen(false)
  }

  if (variant === 'compact') {
    // Simple toggle button for AR/EN
    return (
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => handleLanguageChange(i18n.language === 'en' ? 'ar' : 'en')}
        className={`flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.06] border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white transition-all ${className}`}
      >
        <Languages className="w-4 h-4" />
        <span className="text-sm font-medium">
          {i18n.language === 'en' ? 'العربية' : 'English'}
        </span>
      </motion.button>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.06] border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white transition-all"
      >
        <span className="text-lg">{currentLanguage.flag}</span>
        <span className="text-sm font-medium hidden sm:inline">{currentLanguage.nativeName}</span>
        <Languages className="w-4 h-4" />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              className="absolute top-full mt-2 right-0 rtl:right-auto rtl:left-0 z-50 min-w-[180px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl shadow-slate-950/50 overflow-hidden"
            >
              {languages.map((lang) => (
                <motion.button
                  key={lang.code}
                  whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
                  onClick={() => handleLanguageChange(lang.code)}
                  className={`w-full flex items-center justify-between gap-3 px-4 py-3 text-left rtl:text-right transition-colors ${
                    i18n.language === lang.code ? 'bg-violet-500/20' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{lang.flag}</span>
                    <div>
                      <p className="text-sm font-medium text-white">{lang.nativeName}</p>
                      <p className="text-xs text-slate-500">{lang.name}</p>
                    </div>
                  </div>
                  {i18n.language === lang.code && (
                    <Check className="w-4 h-4 text-violet-400" />
                  )}
                </motion.button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
