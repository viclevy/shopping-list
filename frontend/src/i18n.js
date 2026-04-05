import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import es from './locales/es.json'
import de from './locales/de.json'
import ja from './locales/ja.json'
import he from './locales/he.json'

const messages = {
  en, es, de, ja, he
}

const savedLanguage = localStorage.getItem('language') || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLanguage,
  fallbackLocale: 'en',
  messages
})

export function setLanguage(lang) {
  localStorage.setItem('language', lang)
  i18n.global.locale.value = lang
}

export default i18n
