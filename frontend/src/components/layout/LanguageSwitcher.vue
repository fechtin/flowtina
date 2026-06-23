<script setup lang="ts">
import { ref } from 'vue'
import { Languages, Check } from 'lucide-vue-next'
import { useSettingsStore } from '@/stores/settings'
import type { AppLocale } from '@/i18n'

const settings = useSettingsStore()
const open = ref(false)

const options: { code: AppLocale; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'vi', label: 'Tiếng Việt' },
]

function pick(code: AppLocale) {
  settings.setLanguage(code)
  open.value = false
}
</script>

<template>
  <div class="relative">
    <button
      class="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
      @click="open = !open"
    >
      <Languages class="h-5 w-5" />
    </button>
    <div v-if="open" class="fixed inset-0 z-10" @click="open = false" />
    <div
      v-if="open"
      class="absolute right-0 z-20 mt-2 w-40 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
    >
      <button
        v-for="opt in options"
        :key="opt.code"
        class="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
        @click="pick(opt.code)"
      >
        {{ opt.label }}
        <Check v-if="settings.language === opt.code" class="h-4 w-4 text-primary-600" />
      </button>
    </div>
  </div>
</template>
