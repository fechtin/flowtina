<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Mail, Lock } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const projectStore = useProjectStore()
const toast = useToastStore()
const { loading, run } = useAsync()

const email = ref('')
const password = ref('')

async function submit() {
  const ok = await run(async () => {
    await auth.login(email.value, password.value)
    await projectStore.fetchProjects().catch(() => undefined)
  })
  if (ok !== undefined) {
    toast.success(t('auth.loginSuccess'))
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  }
}
</script>

<template>
  <div class="card p-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('auth.loginTitle') }}</h1>
    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{{ t('auth.loginSubtitle') }}</p>

    <form class="mt-6 space-y-4" @submit.prevent="submit">
      <div>
        <label class="label">{{ t('auth.email') }}</label>
        <div class="relative">
          <Mail class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input v-model="email" type="email" required autocomplete="email" class="input pl-9" placeholder="you@example.com" />
        </div>
      </div>
      <div>
        <label class="label">{{ t('auth.password') }}</label>
        <div class="relative">
          <Lock class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input v-model="password" type="password" required autocomplete="current-password" class="input pl-9" placeholder="••••••••" />
        </div>
      </div>
      <button type="submit" class="btn-primary w-full" :disabled="loading">
        {{ loading ? t('common.loading') : t('auth.signIn') }}
      </button>
    </form>

    <p class="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
      {{ t('auth.noAccount') }}
      <RouterLink to="/register" class="font-medium text-primary-600 hover:underline">{{ t('auth.signUp') }}</RouterLink>
    </p>
  </div>
</template>
