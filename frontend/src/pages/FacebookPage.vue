<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Plus,
  Trash2,
  Facebook,
  DownloadCloud,
  ExternalLink,
  CheckCircle2,
  MessageCircle,
  RefreshCw,
  ThumbsUp,
} from 'lucide-vue-next'
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
import type { FacebookPage, FacebookDiscoveredPage, FacebookComment } from '@/types'

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

// Two-step sync: 'token' collects the token, 'select' lets the operator pick
// which discovered pages to import (only shown when the token manages >1 page).
const importStep = ref<'token' | 'select'>('token')
const discovered = ref<FacebookDiscoveredPage[]>([])
const selectedIds = reactive<Record<string, boolean>>({})
const allSelected = computed(() => discovered.value.length > 0 && discovered.value.every((p) => selectedIds[p.page_id]))

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
  importStep.value = 'token'
  discovered.value = []
  showImport.value = true
}

// Step 1: discover the pages the token can manage. One page (or none to choose
// from) imports straight away; multiple pages move to the selection step.
async function discoverPages() {
  if (!projectId.value) return
  const found = await runImport(() => facebookService.discoverPages(projectId.value!, importToken.value.trim()))
  if (found === undefined) return
  if (found.length <= 1) {
    await doImport(found.map((p) => p.page_id))
    return
  }
  discovered.value = found
  for (const p of found) selectedIds[p.page_id] = true
  importStep.value = 'select'
}

function toggleSelectAll() {
  const next = !allSelected.value
  for (const p of discovered.value) selectedIds[p.page_id] = next
}

// Step 2: import the chosen pages.
async function importSelected() {
  const ids = discovered.value.filter((p) => selectedIds[p.page_id]).map((p) => p.page_id)
  if (!ids.length) {
    toast.error(t('facebook.selectAtLeastOne'))
    return
  }
  await doImport(ids)
}

async function doImport(pageIds: string[]) {
  if (!projectId.value) return
  const result = await runImport(() =>
    facebookService.importPages(projectId.value!, importToken.value.trim(), pageIds),
  )
  if (result !== undefined) {
    toast.success(t('facebook.imported', { count: Array.isArray(result) ? result.length : 0 }))
    showImport.value = false
    await load()
  }
}

// --- Comment auto-engagement ---
const showEngage = ref(false)
const engagePage = ref<FacebookPage | null>(null)
const engageForm = reactive({ auto_like_comments: false, auto_reply_comments: false, reply_persona: '' })
const comments = ref<FacebookComment[]>([])
const { loading: savingEngage, run: runEngage } = useAsync()
const { loading: engagingNow, run: runEngageNow } = useAsync()

async function openEngage(page: FacebookPage) {
  engagePage.value = page
  engageForm.auto_like_comments = !!page.auto_like_comments
  engageForm.auto_reply_comments = !!page.auto_reply_comments
  engageForm.reply_persona = page.reply_persona ?? ''
  comments.value = []
  showEngage.value = true
  await loadComments(page.id)
}

async function loadComments(id: string) {
  try {
    comments.value = await facebookService.listComments(id)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  }
}

async function saveEngage() {
  if (!engagePage.value) return
  const updated = await runEngage(
    () => facebookService.updateEngagement(engagePage.value!.id, { ...engageForm }),
    { successMessage: t('facebook.engagementSaved') },
  )
  if (updated !== undefined) {
    showEngage.value = false
    await load()
  }
}

async function engageNow() {
  if (!engagePage.value) return
  const result = await runEngageNow(() => facebookService.engageNow(engagePage.value!.id))
  if (result !== undefined) {
    // Every scanned post unreadable => the page token is almost certainly
    // missing the engagement scopes; warn instead of a misleading success.
    if (result.scanned > 0 && result.skipped === result.scanned) {
      toast.error(t('facebook.engageNoPermission'))
    } else {
      toast.success(t('facebook.engaged', { count: result?.processed ?? 0 }))
    }
    await loadComments(engagePage.value.id)
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

        <div class="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-800">
          <div class="flex flex-wrap gap-1.5">
            <span
              v-if="p.auto_like_comments"
              class="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600 dark:bg-blue-950 dark:text-blue-300"
            >
              <ThumbsUp class="h-3 w-3" /> {{ t('facebook.autoLike') }}
            </span>
            <span
              v-if="p.auto_reply_comments"
              class="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-600 dark:bg-green-950 dark:text-green-300"
            >
              <MessageCircle class="h-3 w-3" /> {{ t('facebook.autoReply') }}
            </span>
          </div>
          <button class="btn-secondary text-xs" @click="openEngage(p)">
            <MessageCircle class="h-3.5 w-3.5" /> {{ t('facebook.engagement') }}
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
    <BaseModal
      v-model="showImport"
      :title="importStep === 'select' ? t('facebook.selectTitle') : t('facebook.importTitle')"
    >
      <!-- Step 1: token entry -->
      <div v-if="importStep === 'token'" class="space-y-4">
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
          <button type="button" class="btn-primary" :disabled="importing" @click="discoverPages">
            <DownloadCloud class="h-4 w-4" />
            {{ importing ? t('common.loading') : importLabel }}
          </button>
        </div>
      </div>

      <!-- Step 2: choose which pages to import -->
      <div v-else class="space-y-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ t('facebook.selectHint') }}</p>

        <label class="flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          <input type="checkbox" class="h-4 w-4" :checked="allSelected" @change="toggleSelectAll" />
          {{ t('facebook.selectAll') }}
        </label>

        <div class="max-h-72 space-y-2 overflow-y-auto">
          <label
            v-for="p in discovered"
            :key="p.page_id"
            class="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700"
          >
            <input v-model="selectedIds[p.page_id]" type="checkbox" class="h-4 w-4" />
            <div class="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950 dark:text-blue-300">
              <Facebook class="h-4 w-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium text-gray-900 dark:text-white">{{ p.page_name }}</p>
              <p class="truncate text-xs text-gray-400">{{ p.page_id }}</p>
            </div>
            <span
              v-if="p.already_connected"
              class="inline-flex items-center gap-1 whitespace-nowrap text-xs text-green-600 dark:text-green-400"
            >
              <CheckCircle2 class="h-3.5 w-3.5" /> {{ t('facebook.alreadyConnected') }}
            </span>
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="importStep = 'token'">{{ t('common.back') }}</button>
          <button type="button" class="btn-primary" :disabled="importing" @click="importSelected">
            <DownloadCloud class="h-4 w-4" />
            {{ importing ? t('common.loading') : t('facebook.importSelected') }}
          </button>
        </div>
      </div>
    </BaseModal>

    <!-- Comment auto-engagement -->
    <BaseModal v-model="showEngage" :title="t('facebook.engagementTitle')">
      <div class="space-y-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ t('facebook.engagementHint') }}</p>

        <label class="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          <input v-model="engageForm.auto_like_comments" type="checkbox" class="mt-0.5 h-4 w-4" />
          <span class="min-w-0">
            <span class="block text-sm font-medium text-gray-900 dark:text-white">{{ t('facebook.autoLike') }}</span>
            <span class="block text-xs text-gray-400">{{ t('facebook.autoLikeHint') }}</span>
          </span>
        </label>

        <label class="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          <input v-model="engageForm.auto_reply_comments" type="checkbox" class="mt-0.5 h-4 w-4" />
          <span class="min-w-0">
            <span class="block text-sm font-medium text-gray-900 dark:text-white">{{ t('facebook.autoReply') }}</span>
            <span class="block text-xs text-gray-400">{{ t('facebook.autoReplyHint') }}</span>
          </span>
        </label>

        <div v-if="engageForm.auto_reply_comments">
          <label class="label">{{ t('facebook.replyPersona') }}</label>
          <textarea
            v-model="engageForm.reply_persona"
            rows="3"
            class="input text-sm"
            :placeholder="t('facebook.replyPersonaPlaceholder')"
          />
        </div>

        <p class="rounded-lg bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
          {{ t('facebook.engagementScopes') }}
        </p>

        <!-- Recent processed comments -->
        <div>
          <div class="mb-2 flex items-center justify-between">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('facebook.recentComments') }}</span>
            <button class="btn-ghost text-xs" :disabled="engagingNow" @click="engageNow">
              <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': engagingNow }" />
              {{ t('facebook.engageNow') }}
            </button>
          </div>
          <p v-if="!comments.length" class="text-xs text-gray-400">{{ t('facebook.noComments') }}</p>
          <div v-else class="max-h-56 space-y-2 overflow-y-auto">
            <div
              v-for="c in comments"
              :key="c.id"
              class="rounded-lg border border-gray-200 p-2 text-xs dark:border-gray-700"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="truncate font-medium text-gray-900 dark:text-white">{{ c.commenter_name || '—' }}</span>
                <span class="flex shrink-0 gap-1.5">
                  <span v-if="c.liked" class="inline-flex items-center gap-0.5 text-blue-600 dark:text-blue-300">
                    <ThumbsUp class="h-3 w-3" /> {{ t('facebook.liked') }}
                  </span>
                  <span v-if="c.replied" class="inline-flex items-center gap-0.5 text-green-600 dark:text-green-300">
                    <MessageCircle class="h-3 w-3" /> {{ t('facebook.replied') }}
                  </span>
                </span>
              </div>
              <p class="mt-0.5 truncate text-gray-500 dark:text-gray-400">{{ c.message || '—' }}</p>
              <p v-if="c.reply_text" class="mt-1 truncate italic text-gray-400">↳ {{ c.reply_text }}</p>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showEngage = false">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="savingEngage" @click="saveEngage">
            {{ savingEngage ? t('common.loading') : t('common.save') }}
          </button>
        </div>
      </div>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
