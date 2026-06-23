import { createI18n } from 'vue-i18n'
import en from './en'
import vi from './vi'

export type AppLocale = 'en' | 'vi'

const saved = localStorage.getItem('flowtina_language')
const initialLocale: AppLocale = saved === 'vi' ? 'vi' : 'en'

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: { en, vi },
})
