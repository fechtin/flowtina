<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
</script>

<template>
  <button
    class="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
    :title="settings.theme === 'dark' ? 'Light' : 'Dark'"
    @click="settings.toggleTheme()"
  >
    <Sun v-if="settings.theme === 'dark'" class="h-5 w-5" />
    <Moon v-else class="h-5 w-5" />
  </button>
</template>
