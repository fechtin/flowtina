<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { logService } from '@/services'
import { extractErrorMessage } from '@/services/http'
import { useToastStore } from '@/stores/toast'
import { formatDate } from '@/utils/format'
import type { LogEntry } from '@/types'

const { t } = useI18n()
const toast = useToastStore()

const loading = ref(false)
const logs = ref<LogEntry[]>([])
const filters = reactive({ level: 'all', module: '', limit: 100 })

const levelOptions = ['all', 'debug', 'info', 'warning', 'error', 'critical']

const columns = [
  { key: 'level', label: t('logs.level') },
  { key: 'module', label: t('logs.module') },
  { key: 'message', label: t('logs.message'), class: 'whitespace-normal break-words' },
  { key: 'time', label: t('logs.time'), class: 'whitespace-nowrap' },
]

async function load() {
  loading.value = true
  try {
    const params: { level?: string; module?: string; limit?: number } = { limit: filters.limit }
    if (filters.level !== 'all') params.level = filters.level
    if (filters.module.trim()) params.module = filters.module.trim()
    logs.value = await logService.list(params)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader :title="t('logs.title')" />

    <div class="card mb-6 flex flex-col gap-4 p-4 sm:flex-row sm:items-end">
      <div class="flex-1">
        <label class="label">{{ t('logs.level') }}</label>
        <select v-model="filters.level" class="input">
          <option v-for="opt in levelOptions" :key="opt" :value="opt">
            {{ opt === 'all' ? t('common.all') : opt }}
          </option>
        </select>
      </div>
      <div class="flex-1">
        <label class="label">{{ t('logs.module') }}</label>
        <input v-model="filters.module" class="input" />
      </div>
      <div class="w-full sm:w-32">
        <label class="label">Limit</label>
        <input v-model.number="filters.limit" type="number" min="1" class="input" />
      </div>
      <button class="btn-primary" @click="load">
        <Search class="h-4 w-4" /> {{ t('common.search') }}
      </button>
    </div>

    <LoadingSpinner v-if="loading" :label="t('common.loading')" />
    <EmptyState v-else-if="!logs.length" :message="t('common.noData')" />
    <DataTable v-else :columns="columns" :rows="logs">
      <template #cell-level="{ row }">
        <StatusBadge :status="(row as LogEntry).level" :label="(row as LogEntry).level" />
      </template>
      <template #cell-module="{ row }">
        <span class="font-mono text-xs text-gray-600 dark:text-gray-300">{{ (row as LogEntry).module }}</span>
      </template>
      <template #cell-message="{ row }">
        <span class="text-gray-700 dark:text-gray-200">{{ (row as LogEntry).message }}</span>
      </template>
      <template #cell-time="{ row }">
        <span class="text-gray-500 dark:text-gray-400">{{ formatDate((row as LogEntry).created_at) }}</span>
      </template>
    </DataTable>
  </div>
</template>
