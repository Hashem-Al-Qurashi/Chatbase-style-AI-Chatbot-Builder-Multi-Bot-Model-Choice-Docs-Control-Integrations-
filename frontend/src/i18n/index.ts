import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ar from './locales/ar.json'

// Get saved language or default to English
const savedLanguage = localStorage.getItem('language') || 'en'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar }
    },
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  })

// Update document direction when language changes
i18n.on('languageChanged', (lng) => {
  document.documentElement.dir = lng === 'ar' ? 'rtl' : 'ltr'
  document.documentElement.lang = lng
  localStorage.setItem('language', lng)
})

// Set initial direction
document.documentElement.dir = savedLanguage === 'ar' ? 'rtl' : 'ltr'
document.documentElement.lang = savedLanguage

export default i18n
