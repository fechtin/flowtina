<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Sparkles, Pencil, Trash2, Send, RefreshCw, Bot } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { postService, facebookService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { extractErrorMessage } from '@/services/http'
import { useToastStore } from '@/stores/toast'
import { formatDate, truncate } from '@/utils/format'
import type { FacebookPage, Post, PostStatus } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { loading: mutating, run } = useAsync()

const STATUS_TABS: PostStatus[] = ['draft', 'pending_approval', 'scheduled', 'published', 'failed']

const activeStatus = ref<PostStatus>('draft')
const loading = ref(false)
const posts = ref<Post[]>([])
const pages = ref<FacebookPage[]>([])

// Create / edit modal
const showForm = ref(false)
const editing = ref<Post | null>(null)
const form = reactive({
  title: '',
  content: '',
  hashtags: '',
  language: 'en',
  status: 'draft' as PostStatus,
})

// Generate modal
const showGenerate = ref(false)
const generateForm = reactive({
  topic: '',
  content_type: 'post',
  language: 'en',
  auto_publish: false,
})

// Publish / retry modal
const showPublish = ref(false)
const publishTarget = ref<Post | null>(null)
const publishMode = ref<'publish' | 'retry'>('publish')
const selectedPageId = ref('')

// Delete confirm
const showConfirm = ref(false)
const deleteId = ref<string | null>(null)

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    posts.value = await postService.list(projectId.value, { status: activeStatus.value })
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

async function loadPages() {
  if (!projectId.value) return
  try {
    pages.value = await facebookService.listPages(projectId.value)
  } catch {
    pages.value = []
  }
}

function selectStatus(status: PostStatus) {
  activeStatus.value = status
  load()
}

// ---------- Create / Edit ----------
function openCreate() {
  editing.value = null
  form.title = ''
  form.content = ''
  form.hashtags = ''
  form.language = 'en'
  form.status = 'draft'
  showForm.value = true
}

/** Split a stored hashtags string (space- or comma-separated) into normalized "#tag" tokens. */
function hashtagList(raw: string | null | undefined): string[] {
  return (raw ?? '')
    .split(/[\s,]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => (t.startsWith('#') ? t : `#${t}`))
}

function openEdit(p: Post) {
  editing.value = p
  form.title = p.title
  form.content = p.content
  form.hashtags = hashtagList(p.hashtags).join(', ')
  form.language = p.language
  form.status = p.status
  showForm.value = true
}

async function save() {
  if (!projectId.value) return
  const pid = projectId.value
  const hashtags = hashtagList(form.hashtags).join(' ')
  const action = editing.value
    ? () =>
        postService.update(editing.value!.id, {
          title: form.title,
          content: form.content,
          hashtags,
          language: form.language,
          status: form.status,
        })
    : () =>
        postService.create(pid, {
          title: form.title,
          content: form.content,
          hashtags,
          language: form.language,
          status: form.status,
        })
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok !== undefined) {
    showForm.value = false
    await load()
  }
}

// ---------- Generate ----------
function openGenerate() {
  generateForm.topic = ''
  generateForm.content_type = 'post'
  generateForm.language = 'en'
  generateForm.auto_publish = false
  showGenerate.value = true
}

async function generate() {
  if (!projectId.value) return
  const result = await run(
    () =>
      postService.generate(projectId.value!, {
        topic: generateForm.topic || undefined,
        content_type: generateForm.content_type,
        language: generateForm.language,
        auto_publish: generateForm.auto_publish,
      }),
  )
  if (result !== undefined) {
    toast.success(t('posts.generated', { count: result.length }))
    showGenerate.value = false
    await load()
  }
}

// ---------- Publish / Retry ----------
function openPublish(p: Post, mode: 'publish' | 'retry') {
  publishTarget.value = p
  publishMode.value = mode
  selectedPageId.value = pages.value[0]?.page_id ?? ''
  showPublish.value = true
}

async function doPublish() {
  if (!publishTarget.value) return
  const id = publishTarget.value.id
  const pageId = selectedPageId.value || undefined
  const action =
    publishMode.value === 'retry'
      ? () => postService.retry(id, pageId)
      : () => postService.publish(id, pageId)
  const ok = await run(action, { successMessage: t('posts.publishedMsg') })
  if (ok !== undefined) {
    showPublish.value = false
    await load()
  }
}

// ---------- Delete ----------
function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  const ok = await run(() => postService.remove(deleteId.value!), {
    successMessage: t('common.deleted'),
  })
  if (ok !== undefined) await load()
}

onMounted(() => {
  load()
  loadPages()
})
watch(projectId, () => {
  load()
  loadPages()
})
</script>

<template>
  <div>
    <PageHeader :title="t('posts.title')">
      <template #actions>
        <button class="btn-secondary" @click="openGenerate">
          <Sparkles class="h-4 w-4" /> {{ t('posts.generatePosts') }}
        </button>
        <button class="btn-primary" @click="openCreate">
          <Plus class="h-4 w-4" /> {{ t('posts.newPost') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <template v-else>
      <div class="mb-4 flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-800">
        <button
          v-for="status in STATUS_TABS"
          :key="status"
          class="-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="
            status === activeStatus
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          "
          @click="selectStatus(status)"
        >
          {{ t(`posts.${status}`) }}
        </button>
      </div>

      <LoadingSpinner v-if="loading" :label="t('common.loading')" />
      <EmptyState v-else-if="!posts.length" :message="t('common.noData')" />

      <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div v-for="p in posts" :key="p.id" class="card flex flex-col p-5">
          <div class="flex items-start justify-between gap-2">
            <h3 class="min-w-0 flex-1 truncate font-semibold text-gray-900 dark:text-white">
              {{ p.title || truncate(p.content, 60) }}
            </h3>
            <StatusBadge :status="p.status" :label="t(`posts.${p.status}`)" />
          </div>

          <p class="mt-2 line-clamp-3 text-sm text-gray-500 dark:text-gray-400">
            {{ truncate(p.content, 200) }}
          </p>

          <div v-if="hashtagList(p.hashtags).length" class="mt-3 flex flex-wrap gap-1">
            <span
              v-for="tag in hashtagList(p.hashtags)"
              :key="tag"
              class="badge bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
            >
              {{ tag }}
            </span>
          </div>

          <div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-400">
            <span>{{ t('posts.qualityScore') }}: {{ p.quality_score }}</span>
            <span
              v-if="p.created_by_ai"
              class="badge inline-flex items-center gap-1 bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300"
            >
              <Bot class="h-3 w-3" /> {{ t('posts.aiGenerated') }}
            </span>
            <span v-if="p.published_at">{{ formatDate(p.published_at) }}</span>
          </div>

          <p v-if="p.status === 'failed' && p.error_message" class="mt-2 text-sm text-red-600 dark:text-red-400">
            {{ p.error_message }}
          </p>

          <div class="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
            <button
              v-if="p.status === 'draft' || p.status === 'scheduled'"
              class="btn-ghost text-sm text-primary-600"
              @click="openPublish(p, 'publish')"
            >
              <Send class="h-4 w-4" /> {{ t('common.publish') }}
            </button>
            <button
              v-if="p.status === 'failed'"
              class="btn-ghost text-sm text-amber-600"
              @click="openPublish(p, 'retry')"
            >
              <RefreshCw class="h-4 w-4" /> {{ t('common.retry') }}
            </button>
            <span class="flex-1"></span>
            <button class="btn-ghost" @click="openEdit(p)"><Pencil class="h-4 w-4" /></button>
            <button class="btn-ghost text-red-600" @click="confirmDelete(p.id)"><Trash2 class="h-4 w-4" /></button>
          </div>
        </div>
      </div>
    </template>

    <!-- Create / Edit modal -->
    <BaseModal v-model="showForm" :title="editing ? t('posts.editPost') : t('posts.newPost')">
      <form class="space-y-4" @submit.prevent="save">
        <div>
          <label class="label">{{ t('common.name') }} <span class="text-gray-400">({{ t('common.optional') }})</span></label>
          <input v-model="form.title" class="input" />
        </div>
        <div>
          <label class="label">{{ t('posts.content') }}</label>
          <textarea v-model="form.content" rows="5" required class="input"></textarea>
        </div>
        <div>
          <label class="label">{{ t('posts.hashtags') }}</label>
          <input v-model="form.hashtags" class="input" placeholder="#ai, #content" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">{{ t('common.language') }}</label>
            <select v-model="form.language" class="input">
              <option value="en">en</option>
              <option value="vi">vi</option>
            </select>
          </div>
          <div>
            <label class="label">{{ t('common.status') }}</label>
            <select v-model="form.status" class="input">
              <option value="draft">{{ t('posts.draft') }}</option>
              <option value="scheduled">{{ t('posts.scheduled') }}</option>
              <option value="published">{{ t('posts.published') }}</option>
              <option value="failed">{{ t('posts.failed') }}</option>
              <option value="archived">{{ t('posts.archived') }}</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showForm = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary" :disabled="mutating">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <!-- Generate modal -->
    <BaseModal v-model="showGenerate" :title="t('posts.generatePosts')">
      <form class="space-y-4" @submit.prevent="generate">
        <div>
          <label class="label">{{ t('sources.topic') }} <span class="text-gray-400">({{ t('common.optional') }})</span></label>
          <input v-model="generateForm.topic" class="input" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">{{ t('posts.contentType') }}</label>
            <select v-model="generateForm.content_type" class="input">
              <option value="post">post</option>
              <option value="article">article</option>
              <option value="caption">caption</option>
            </select>
          </div>
          <div>
            <label class="label">{{ t('common.language') }}</label>
            <select v-model="generateForm.language" class="input">
              <option value="en">en</option>
              <option value="vi">vi</option>
            </select>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <label class="label mb-0">{{ t('posts.autoPublish') }}</label>
          <ToggleSwitch v-model="generateForm.auto_publish" />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showGenerate = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary" :disabled="mutating">{{ t('common.generate') }}</button>
        </div>
      </form>
    </BaseModal>

    <!-- Publish / Retry modal -->
    <BaseModal
      v-model="showPublish"
      :title="publishMode === 'retry' ? t('common.retry') : t('common.publish')"
    >
      <div class="space-y-4">
        <div v-if="pages.length">
          <label class="label">{{ t('facebook.pageName') }}</label>
          <select v-model="selectedPageId" class="input">
            <option v-for="pg in pages" :key="pg.id" :value="pg.page_id">{{ pg.page_name }}</option>
          </select>
        </div>
        <p v-else class="text-sm text-gray-500 dark:text-gray-400">
          {{ t('common.noData') }}
        </p>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showPublish = false">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="mutating" @click="doPublish">
            {{ publishMode === 'retry' ? t('common.retry') : t('common.publish') }}
          </button>
        </div>
      </div>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
