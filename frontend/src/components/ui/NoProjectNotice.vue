<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { FolderKanban } from 'lucide-vue-next'

const { t } = useI18n()
</script>

<template>
  <div class="card flex flex-col items-center gap-3 py-16 text-center">
    <div class="rounded-full bg-gray-100 p-4 dark:bg-gray-800">
      <FolderKanban class="h-8 w-8 text-gray-400" />
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400">{{ t('errors.noProject') }}</p>
    <RouterLink to="/projects" class="btn-primary">{{ t('projects.newProject') }}</RouterLink>
  </div>
</template>
