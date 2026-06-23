<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, Check, FolderKanban } from 'lucide-vue-next'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const projectStore = useProjectStore()
const open = ref(false)

function pick(id: string) {
  projectStore.select(id)
  open.value = false
}
</script>

<template>
  <div class="relative">
    <button
      class="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
      @click="open = !open"
    >
      <FolderKanban class="h-4 w-4 text-primary-600" />
      <span class="max-w-[140px] truncate">
        {{ projectStore.currentProject?.name ?? t('projects.selectProject') }}
      </span>
      <ChevronDown class="h-4 w-4 text-gray-400" />
    </button>
    <div v-if="open" class="fixed inset-0 z-10" @click="open = false" />
    <div
      v-if="open"
      class="absolute left-0 z-20 mt-2 max-h-72 w-64 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
    >
      <p v-if="!projectStore.projects.length" class="px-3 py-2 text-sm text-gray-400">
        {{ t('projects.noProjects') }}
      </p>
      <button
        v-for="p in projectStore.projects"
        :key="p.id"
        class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
        @click="pick(p.id)"
      >
        <span class="truncate">{{ p.name }}</span>
        <Check v-if="p.id === projectStore.currentProjectId" class="h-4 w-4 text-primary-600" />
      </button>
    </div>
  </div>
</template>
