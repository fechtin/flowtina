<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Trash2, Facebook, DownloadCloud, ExternalLink } from 'lucide-vue-next'
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

// Same action either way; label reflects intent: first run = import, re-run = sync new/updated pages.
const importLabel = computed(() => (pages.value.length ? t('facebook.syncPages') : t('facebook.importPages')))

const showForm = ref(false)
const showImport = ref(false)
const showConfirm = ref(false)
const deleteId = ref<string | null>(null)
const form = reactive({ page_name: '', page_id: '', access_token: '' })
const importToken = ref('')
const { loading: importing, run: runImport } = useAsync()

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

function openImport() {
  importToken.value = ''
  showImport.value = true
}

async function importPages() {
  if (!projectId.value) return
  const pages = await runImport(() => facebookService.importPages(projectId.value!, importToken.value.trim()))
  if (pages !== undefined) {
    toast.success(t('facebook.imported', { count: Array.isArray(pages) ? pages.length : 0 }))
    showImport.value = false
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
        <button class="btn-primary" @click="openImport">
          <DownloadCloud class="h-4 w-4" /> {{ importLabel }}
        </button>
        <button class="btn-secondary" @click="openConnect">
          <Plus class="h-4 w-4" /> {{ t('facebook.connectPage') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <EmptyState v-else-if="!pages.length" :message="t('common.noData')">
      <button class="btn-primary" @click="openImport">{{ t('facebook.importPages') }}</button>
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

    <!-- Import from a single token -->
    <BaseModal v-model="showImport" :title="t('facebook.importTitle')">
      <div class="space-y-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ t('facebook.importHint') }}</p>
        <div>
          <label class="label">{{ t('facebook.importToken') }}</label>
          <textarea
            v-model="importToken"
            rows="3"
            class="input font-mono text-xs"
            :placeholder="t('facebook.importTokenPlaceholder')"
          />
          <p class="mt-1 text-xs text-gray-400">{{ t('facebook.importTokenOptional') }}</p>
        </div>

        <details class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" open>
          <summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
            {{ t('facebook.howToTitle') }}
          </summary>
          <ol class="mt-2 list-decimal space-y-1 pl-5 text-xs text-gray-500 dark:text-gray-400">
            <li>{{ t('facebook.howToStep0') }}</li>
            <li>{{ t('facebook.howToStep1') }}</li>
            <li>{{ t('facebook.howToStep2') }}</li>
            <li>{{ t('facebook.howToStep3') }}</li>
          </ol>
          <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">{{ t('facebook.howToScopes') }}</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <a
              href="https://developers.facebook.com/apps"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-secondary text-xs"
            >
              <ExternalLink class="h-3.5 w-3.5" /> {{ t('facebook.openDevelopers') }}
            </a>
            <a
              href="https://business.facebook.com/settings/system-users"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-secondary text-xs"
            >
              <ExternalLink class="h-3.5 w-3.5" /> {{ t('facebook.openSystemUsers') }}
            </a>
            <a
              href="https://developers.facebook.com/tools/explorer/"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-secondary text-xs"
            >
              <ExternalLink class="h-3.5 w-3.5" /> {{ t('facebook.openExplorer') }}
            </a>
          </div>
        </details>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showImport = false">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="importing" @click="importPages">
            <DownloadCloud class="h-4 w-4" />
            {{ importing ? t('common.loading') : importLabel }}
          </button>
        </div>
      </div>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
