<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import LanguageSwitcher from '@/components/layout/LanguageSwitcher.vue'

const { t } = useI18n()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-950">
    <div class="flex items-center justify-between p-4">
      <div class="flex items-center gap-2">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 font-bold text-white">F</div>
        <div>
          <p class="text-sm font-bold text-gray-900 dark:text-white">{{ t('app.name') }}</p>
          <p class="text-[10px] text-gray-400">{{ t('app.tagline') }}</p>
        </div>
      </div>
      <div class="flex items-center gap-1">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
    </div>
    <div class="flex flex-1 items-center justify-center p-4">
      <div class="w-full max-w-md">
        <RouterView />
      </div>
    </div>
  </div>
</template>
