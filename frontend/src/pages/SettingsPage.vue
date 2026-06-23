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
import type { AppSettings, ProviderType } from '@/types'

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
  daily_budget: 10,
  retry_count: 3,
  random_delay_seconds: 0,
})

onMounted(async () => {
  const data = await run(() => settingsService.get(), { silentError: true })
  if (data) {
    form.timezone = data.timezone || 'UTC'
    form.default_provider = data.default_provider || 'openai'
    form.default_model = data.default_model || 'gpt-4o-mini'
    form.daily_budget = data.daily_budget ?? 10
    form.retry_count = data.retry_count ?? 3
    form.random_delay_seconds = data.random_delay_seconds ?? 0
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
  const payload: Partial<AppSettings> = {
    ...form,
    theme: settingsStore.theme,
    language: settingsStore.language,
  }
  await run(() => settingsService.update(payload), { successMessage: t('common.saved') })
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

      <div class="flex justify-end">
        <button type="submit" class="btn-primary" :disabled="loading">{{ t('common.save') }}</button>
      </div>
    </form>
  </div>
</template>
