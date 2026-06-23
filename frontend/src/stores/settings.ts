import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { i18n, type AppLocale } from '@/i18n'

type Theme = 'light' | 'dark'

const THEME_KEY = 'flowtina_theme'
const LANG_KEY = 'flowtina_language'

function readTheme(): Theme {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readLanguage(): AppLocale {
  const saved = localStorage.getItem(LANG_KEY)
  return saved === 'vi' ? 'vi' : 'en'
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<Theme>(readTheme())
  const language = ref<AppLocale>(readLanguage())

  applyTheme(theme.value)
  i18n.global.locale.value = language.value

  watch(theme, (value) => {
    localStorage.setItem(THEME_KEY, value)
    applyTheme(value)
  })

  watch(language, (value) => {
    localStorage.setItem(LANG_KEY, value)
    i18n.global.locale.value = value
    document.documentElement.lang = value
  })

  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setLanguage(lang: AppLocale): void {
    language.value = lang
  }

  return { theme, language, toggleTheme, setLanguage }
})
