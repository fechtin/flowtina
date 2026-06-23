<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Trash2, Facebook } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { facebookService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { extractErrorMessage } from '@/services/http'
import { useToastStore } from '@/stores/toast'
import type { FacebookPage } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { run } = useAsync()

const loading = ref(false)
const pages = ref<FacebookPage[]>([])

const showForm = ref(false)
const showConfirm = ref(false)
const deleteId = ref<string | null>(null)
const form = reactive({ page_name: '', page_id: '', access_token: '' })

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    pages.value = await facebookService.listPages(projectId.value)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)

function openConnect() {
  form.page_name = ''
  form.page_id = ''
  form.access_token = ''
  showForm.value = true
}

async function save() {
  if (!projectId.value) return
  const ok = await run(
    () => facebookService.addPage(projectId.value!, { ...form }),
    { successMessage: t('facebook.connected') },
  )
  if (ok !== undefined) {
    showForm.value = false
    await load()
  }
}

function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  const ok = await run(
    () => facebookService.removePage(deleteId.value!),
    { successMessage: t('common.deleted') },
  )
  if (ok !== undefined) await load()
}
</script>

<template>
  <div>
    <PageHeader :title="t('facebook.title')">
      <template #actions>
        <button class="btn-primary" @click="openConnect">
          <Plus class="h-4 w-4" /> {{ t('facebook.connectPage') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <EmptyState v-else-if="!pages.length" :message="t('common.noData')">
      <button class="btn-primary" @click="openConnect">{{ t('facebook.connectPage') }}</button>
    </EmptyState>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="p in pages" :key="p.id" class="card flex flex-col p-5">
        <div class="flex items-start justify-between">
          <div class="flex min-w-0 items-center gap-3">
            <div class="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950 dark:text-blue-300">
              <Facebook class="h-5 w-5" />
            </div>
            <div class="min-w-0">
              <h3 class="truncate font-semibold text-gray-900 dark:text-white">{{ p.page_name }}</h3>
              <p class="truncate text-xs text-gray-400">{{ p.page_id }}</p>
            </div>
          </div>
          <button class="btn-ghost text-red-600" @click="confirmDelete(p.id)">
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>

    <BaseModal v-model="showForm" :title="t('facebook.connectPage')">
      <form class="space-y-4" @submit.prevent="save">
        <div>
          <label class="label">{{ t('facebook.pageName') }}</label>
          <input v-model="form.page_name" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('facebook.pageId') }}</label>
          <input v-model="form.page_id" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('facebook.accessToken') }}</label>
          <input v-model="form.access_token" type="password" required class="input" />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showForm = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
