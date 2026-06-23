<script setup lang="ts">
import { onMounted, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/ui/PageHeader.vue'
import { authService } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useAsync } from '@/composables/useAsync'
import type { AppLocale } from '@/i18n'
import type { User } from '@/types'

const { t } = useI18n()
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const { loading: savingProfile, run: runProfile } = useAsync()
const { loading: savingPassword, run: runPassword } = useAsync()

const accountForm = reactive({
  name: '',
  language: 'en',
  timezone: '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
})

function syncFromUser(user: User | null) {
  accountForm.name = user?.name ?? ''
  accountForm.language = user?.language || settingsStore.language
  accountForm.timezone = user?.timezone ?? ''
}

watch(() => auth.user, syncFromUser, { immediate: true })

onMounted(async () => {
  if (!auth.user) {
    await runProfile(() => auth.fetchProfile())
  }
})

async function saveAccount() {
  const updated = await runProfile(
    () =>
      authService.updateProfile({
        name: accountForm.name,
        language: accountForm.language,
        timezone: accountForm.timezone,
      }),
    { successMessage: t('common.saved') },
  )
  if (updated) {
    auth.setUser(updated)
    if (updated.language === 'en' || updated.language === 'vi') {
      settingsStore.setLanguage(updated.language as AppLocale)
    }
  }
}

async function changePassword() {
  const ok = await runPassword(
    () =>
      authService.changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password,
      }),
    { successMessage: t('auth.passwordChanged') },
  )
  if (ok !== undefined) {
    passwordForm.old_password = ''
    passwordForm.new_password = ''
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('profile.title')" />

    <div class="space-y-6">
      <div class="card p-6">
        <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('profile.accountInfo') }}
        </h2>
        <form class="space-y-4" @submit.prevent="saveAccount">
          <div>
            <label class="label">{{ t('auth.email') }}</label>
            <input :value="auth.user?.email ?? ''" disabled class="input opacity-60" />
          </div>
          <div>
            <label class="label">{{ t('auth.name') }}</label>
            <input v-model="accountForm.name" class="input" />
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label class="label">{{ t('common.language') }}</label>
              <select v-model="accountForm.language" class="input">
                <option value="en">English</option>
                <option value="vi">Tiếng Việt</option>
              </select>
            </div>
            <div>
              <label class="label">{{ t('settings.timezone') }}</label>
              <input v-model="accountForm.timezone" class="input" />
            </div>
          </div>
          <div class="flex justify-end">
            <button type="submit" class="btn-primary" :disabled="savingProfile">
              {{ t('common.save') }}
            </button>
          </div>
        </form>
      </div>

      <div class="card p-6">
        <h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
          {{ t('profile.security') }}
        </h2>
        <form class="space-y-4" @submit.prevent="changePassword">
          <div>
            <label class="label">{{ t('auth.oldPassword') }}</label>
            <input
              v-model="passwordForm.old_password"
              type="password"
              required
              autocomplete="current-password"
              class="input"
            />
          </div>
          <div>
            <label class="label">{{ t('auth.newPassword') }}</label>
            <input
              v-model="passwordForm.new_password"
              type="password"
              required
              autocomplete="new-password"
              class="input"
            />
          </div>
          <div class="flex justify-end">
            <button type="submit" class="btn-primary" :disabled="savingPassword">
              {{ t('auth.changePassword') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
