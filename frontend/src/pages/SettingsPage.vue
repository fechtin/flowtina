<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sun, Moon } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { settingsService } from '@/services'
import { useSettingsStore } from '@/stores/settings'
import { useAsync } from '@/composables/useAsync'
import type { AppLocale } from '@/i18n'
import type { AppSettings, AppSettingsUpdate, ProviderType } from '@/types'

const { t } = useI18n()
const settingsStore = useSettingsStore()
const { loading, run } = useAsync()

const initialLoading = ref(true)

const providerOptions: ProviderType[] = [
  'openai',
  'gemini',
  'claude',
  'openrouter',
  'deepseek',
  'ollama',
  'lmstudio',
  'vllm',
  'custom',
]

const form = reactive<AppSettings>({
  theme: settingsStore.theme,
  language: settingsStore.language,
  timezone: 'UTC',
  default_provider: 'openai',
  default_model: 'gpt-4o-mini',
  default_base_url: '',
  daily_budget: 10,
  retry_count: 3,
  random_delay_seconds: 0,
  telegram_chat_id: '',
  telegram_enabled: false,
})

// Whether a secret is already stored server-side (the value itself is never returned).
const apiKeySet = ref(false)
const telegramTokenSet = ref(false)
// New secret values typed in this session; only sent when non-empty.
const apiKeyInput = ref('')
const telegramTokenInput = ref('')

onMounted(async () => {
  const data = await run(() => settingsService.get(), { silentError: true })
  if (data) {
    form.timezone = data.timezone || 'UTC'
    form.default_provider = data.default_provider || 'openai'
    form.default_model = data.default_model || 'gpt-4o-mini'
    form.default_base_url = data.default_base_url || ''
    form.daily_budget = data.daily_budget ?? 10
    form.retry_count = data.retry_count ?? 3
    form.random_delay_seconds = data.random_delay_seconds ?? 0
    form.telegram_chat_id = data.telegram_chat_id || ''
    form.telegram_enabled = data.telegram_enabled ?? false
    apiKeySet.value = data.default_api_key_set ?? false
    telegramTokenSet.value = data.telegram_bot_token_set ?? false
  }
  initialLoading.value = false
})

function setTheme(theme: 'light' | 'dark') {
  if (settingsStore.theme !== theme) settingsStore.toggleTheme()
}

function onLanguageChange(lang: AppLocale) {
  settingsStore.setLanguage(lang)
}

async function save() {
  const payload: AppSettingsUpdate = {
    ...form,
    theme: settingsStore.theme,
    language: settingsStore.language,
  }
  if (apiKeyInput.value.trim()) payload.default_api_key = apiKeyInput.value.trim()
  if (telegramTokenInput.value.trim()) payload.telegram_bot_token = telegramTokenInput.value.trim()
  const data = await run(() => settingsService.update(payload), {
    successMessage: t('common.saved'),
  })
  if (data) {
    apiKeySet.value = data.default_api_key_set ?? false
    telegramTokenSet.value = data.telegram_bot_token_set ?? false
    apiKeyInput.value = ''
    telegramTokenInput.value = ''
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('settings.title')" />

    <LoadingSpinner v-if="initialLoading" />

    <form v-else class="space-y-6" @submit.prevent="save">
      <div class="card p-6">
        <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('settings.appearance') }}
        </h2>
        <div class="space-y-4">
          <div>
            <label class="label">{{ t('settings.theme') }}</label>
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1"
                :class="settingsStore.theme === 'light' ? 'btn-primary' : 'btn-secondary'"
                @click="setTheme('light')"
              >
                <Sun class="h-4 w-4" /> {{ t('settings.light') }}
              </button>
              <button
                type="button"
                class="flex-1"
                :class="settingsStore.theme === 'dark' ? 'btn-primary' : 'btn-secondary'"
                @click="setTheme('dark')"
              >
                <Moon class="h-4 w-4" /> {{ t('settings.dark') }}
              </button>
            </div>
          </div>
          <div>
            <label class="label">{{ t('common.language') }}</label>
            <select
              :value="settingsStore.language"
              class="input"
              @change="onLanguageChange(($event.target as HTMLSelectElement).value as AppLocale)"
            >
              <option value="en">English</option>
              <option value="vi">Tiếng Việt</option>
            </select>
          </div>
        </div>
      </div>

      <div class="card p-6">
        <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('settings.defaults') }}
        </h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="label">{{ t('settings.timezone') }}</label>
            <input v-model="form.timezone" class="input" />
          </div>
          <div>
            <label class="label">{{ t('settings.defaultProvider') }}</label>
            <select v-model="form.default_provider" class="input">
              <option v-for="p in providerOptions" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div>
            <label class="label">{{ t('settings.defaultModel') }}</label>
            <input v-model="form.default_model" class="input" />
          </div>
          <div>
            <label class="label">{{ t('settings.dailyBudget') }}</label>
            <input v-model.number="form.daily_budget" type="number" min="0" step="0.01" class="input" />
          </div>
          <div>
            <label class="label">{{ t('settings.retryCount') }}</label>
            <input v-model.number="form.retry_count" type="number" min="0" class="input" />
          </div>
          <div>
            <label class="label">{{ t('settings.randomDelay') }}</label>
            <input v-model.number="form.random_delay_seconds" type="number" min="0" class="input" />
          </div>
        </div>
      </div>

      <div class="card p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('settings.providerCredentials') }}
        </h2>
        <p class="mb-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ t('settings.fallbackHint') }}
        </p>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="label">{{ t('settings.defaultApiKey') }}</label>
            <input
              v-model="apiKeyInput"
              type="password"
              autocomplete="off"
              class="input"
              :placeholder="apiKeySet ? '••••••••' : t('settings.notConfigured')"
            />
          </div>
          <div>
            <label class="label">{{ t('settings.defaultBaseUrl') }}</label>
            <input
              v-model="form.default_base_url"
              class="input"
              placeholder="https://api.openai.com/v1"
            />
          </div>
        </div>
      </div>

      <div class="card p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('settings.telegramGlobal') }}
        </h2>
        <p class="mb-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ t('settings.fallbackHint') }}
        </p>
        <div class="space-y-4">
          <label class="flex items-center gap-2">
            <input v-model="form.telegram_enabled" type="checkbox" class="h-4 w-4" />
            <span class="text-sm text-gray-700 dark:text-gray-300">
              {{ t('settings.telegramEnabled') }}
            </span>
          </label>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label class="label">{{ t('settings.telegramBotToken') }}</label>
              <input
                v-model="telegramTokenInput"
                type="password"
                autocomplete="off"
                class="input"
                :placeholder="telegramTokenSet ? '••••••••' : t('settings.notConfigured')"
              />
            </div>
            <div>
              <label class="label">{{ t('settings.telegramChatId') }}</label>
              <input v-model="form.telegram_chat_id" class="input" placeholder="-100123456789" />
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <button type="submit" class="btn-primary" :disabled="loading">{{ t('common.save') }}</button>
      </div>
    </form>
  </div>
</template>
