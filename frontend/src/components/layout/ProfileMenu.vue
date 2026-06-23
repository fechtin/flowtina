<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { User, LogOut, Settings } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const projectStore = useProjectStore()
const open = ref(false)

const initials = computed(() => {
  const name = auth.user?.name || auth.user?.email || '?'
  return name.slice(0, 2).toUpperCase()
})

async function logout() {
  open.value = false
  await auth.logout()
  projectStore.reset()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="relative">
    <button
      class="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white"
      @click="open = !open"
    >
      {{ initials }}
    </button>
    <div v-if="open" class="fixed inset-0 z-10" @click="open = false" />
    <div
      v-if="open"
      class="absolute right-0 z-20 mt-2 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
    >
      <div class="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <p class="truncate text-sm font-medium text-gray-900 dark:text-white">{{ auth.user?.name }}</p>
        <p class="truncate text-xs text-gray-500">{{ auth.user?.email }}</p>
      </div>
      <RouterLink
        to="/profile"
        class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
        @click="open = false"
      >
        <User class="h-4 w-4" /> {{ t('nav.profile') }}
      </RouterLink>
      <RouterLink
        to="/settings"
        class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
        @click="open = false"
      >
        <Settings class="h-4 w-4" /> {{ t('nav.settings') }}
      </RouterLink>
      <button
        class="flex w-full items-center gap-2 border-t border-gray-100 px-4 py-2 text-sm text-red-600 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800"
        @click="logout"
      >
        <LogOut class="h-4 w-4" /> {{ t('auth.logout') }}
      </button>
    </div>
  </div>
</template>
