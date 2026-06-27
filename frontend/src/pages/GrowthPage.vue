<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  TrendingUp, FileText, Settings, BarChart2,
  RefreshCw, CheckCircle2, XCircle, Zap, ChevronRight,
} from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { growthService, facebookService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import type { FacebookPage, TrendTopic, ContentDraft, GrowthConfig } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()

type Tab = 'trends' | 'drafts' | 'config' | 'insights'
const activeTab = ref<Tab>('trends')

const pages = ref<FacebookPage[]>([])
const selectedPageId = ref('')
const topics = ref<TrendTopic[]>([])
const drafts = ref<ContentDraft[]>([])
const config = ref<GrowthConfig | null>(null)
const insights = ref<Record<string, unknown> | null>(null)

const discovering = ref(false)
const generatingDraftId = ref<string | null>(null)
const savingConfig = ref(false)

const showDraftModal = ref(false)
const activeDraft = ref<ContentDraft | null>(null)

const configForm = ref({
  enabled: true,
  brand_name: '',
  language: 'vi',
  tone: 'friendly',
  content_categories: '',
  posts_per_day: 2,
  blocked_keywords: '',
  quality_threshold: 60,
})

async function loadPages() {
  if (!projectId.value) return
  try {
    pages.value = await facebookService.listPages(projectId.value)
    if (pages.value.length && !selectedPageId.value) {
      selectedPageId.value = pages.value[0].id
    }
  } catch {
    // ignore
  }
}

async function loadData() {
  if (!selectedPageId.value) return
  try {
    topics.value = await growthService.listTopics(selectedPageId.value)
  } catch {
    topics.value = []
  }
  try {
    drafts.value = await growthService.listDrafts(selectedPageId.value)
  } catch {
    drafts.value = []
  }
  try {
    config.value = await growthService.getConfig(selectedPageId.value)
    if (config.value) {
      configForm.value = {
        enabled: config.value.enabled,
        brand_name: config.value.brand_name,
        language: config.value.language,
        tone: config.value.tone,
        content_categories: config.value.content_categories,
        posts_per_day: config.value.posts_per_day,
        blocked_keywords: config.value.blocked_keywords,
        quality_threshold: config.value.quality_threshold,
      }
    }
  } catch {
    config.value = null
  }
  try {
    insights.value = (await growthService.getInsights(selectedPageId.value)) as unknown as Record<string, unknown>
  } catch {
    insights.value = null
  }
}

async function runDiscovery() {
  if (!selectedPageId.value) return
  discovering.value = true
  try {
    const found = await growthService.discover(selectedPageId.value, 10)
    topics.value = found
    toast.success(t('growth.discovered', { count: found.length }))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    discovering.value = false
  }
}

async function generateDraft(topic: TrendTopic) {
  generatingDraftId.value = topic.id
  try {
    const draft = await growthService.generateDraft(selectedPageId.value, topic.id)
    drafts.value.unshift(draft)
    toast.success(t('growth.draftGenerated'))
    activeTab.value = 'drafts'
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    generatingDraftId.value = null
  }
}

function openDraft(draft: ContentDraft) {
  activeDraft.value = draft
  showDraftModal.value = true
}

async function approveDraft(draft: ContentDraft) {
  try {
    const updated = await growthService.approveDraft(selectedPageId.value, draft.id)
    const idx = drafts.value.findIndex(d => d.id === draft.id)
    if (idx !== -1) drafts.value[idx] = updated
    showDraftModal.value = false
    toast.success(t('growth.draftApproved'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  }
}

async function rejectDraft(draft: ContentDraft) {
  try {
    const updated = await growthService.rejectDraft(selectedPageId.value, draft.id)
    const idx = drafts.value.findIndex(d => d.id === draft.id)
    if (idx !== -1) drafts.value[idx] = updated
    showDraftModal.value = false
    toast.success(t('growth.draftRejected'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  }
}

async function saveConfig() {
  if (!selectedPageId.value) return
  savingConfig.value = true
  try {
    config.value = await growthService.upsertConfig(selectedPageId.value, configForm.value)
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    savingConfig.value = false
  }
}

function scoreColor(score: number) {
  if (score >= 70) return 'text-green-600 dark:text-green-400'
  if (score >= 50) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-500'
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    new: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    used: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    skipped: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    draft: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    approved: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    pending_review: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

const tabs: { key: Tab; label: string; icon: unknown }[] = [
  { key: 'trends', label: 'growth.tabs.trends', icon: TrendingUp },
  { key: 'drafts', label: 'growth.tabs.drafts', icon: FileText },
  { key: 'config', label: 'growth.tabs.config', icon: Settings },
  { key: 'insights', label: 'growth.tabs.insights', icon: BarChart2 },
]

onMounted(loadPages)
watch(selectedPageId, loadData)
watch(projectId, () => { selectedPageId.value = ''; loadPages() })
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <PageHeader :title="t('growth.title')" :subtitle="t('growth.subtitle')" />

    <NoProjectNotice v-if="!hasProject" />

    <template v-else>
      <!-- Page selector -->
      <div class="flex items-center gap-3">
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.page') }}</label>
        <select
          v-model="selectedPageId"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
        >
          <option value="" disabled>{{ t('growth.selectPage') }}</option>
          <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.page_name }}</option>
        </select>
      </div>

      <div v-if="!selectedPageId" class="rounded-xl border border-dashed border-gray-300 p-12 text-center text-gray-400 dark:border-gray-700">
        {{ t('growth.selectPageFirst') }}
      </div>

      <template v-else>
        <!-- Tabs -->
        <div class="flex gap-1 border-b border-gray-200 dark:border-gray-800">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors"
            :class="activeTab === tab.key
              ? 'border-b-2 border-primary-600 text-primary-700 dark:text-primary-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'"
            @click="activeTab = tab.key"
          >
            <component :is="tab.icon" class="h-4 w-4" />
            {{ t(tab.label) }}
          </button>
        </div>

        <!-- TRENDS TAB -->
        <div v-if="activeTab === 'trends'" class="flex flex-col gap-4">
          <div class="flex justify-end">
            <button
              class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              :disabled="discovering"
              @click="runDiscovery"
            >
              <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': discovering }" />
              {{ discovering ? t('growth.discovering') : t('growth.discover') }}
            </button>
          </div>

          <EmptyState v-if="!topics.length" :title="t('growth.noTopics')" :description="t('growth.noTopicsHint')" />

          <div v-else class="flex flex-col gap-3">
            <div
              v-for="topic in topics"
              :key="topic.id"
              class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusBadge(topic.status)]">{{ topic.status }}</span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">{{ topic.content_format }}</span>
                    <span class="text-xs text-gray-400">{{ topic.source_name }}</span>
                  </div>
                  <p class="mt-1 font-medium text-gray-900 dark:text-white line-clamp-2">{{ topic.title }}</p>
                  <p class="mt-0.5 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{{ topic.summary }}</p>
                  <div class="mt-2 flex items-center gap-4 text-xs text-gray-400">
                    <span>Freshness: <span :class="scoreColor(topic.freshness_score)">{{ topic.freshness_score }}</span></span>
                    <span>Trend: <span :class="scoreColor(topic.trend_score)">{{ topic.trend_score }}</span></span>
                    <span>Audience: <span :class="scoreColor(topic.audience_match_score)">{{ topic.audience_match_score }}</span></span>
                    <span class="font-medium">Total: <span :class="scoreColor(topic.total_score)">{{ topic.total_score }}</span></span>
                  </div>
                </div>
                <button
                  class="flex shrink-0 items-center gap-1.5 rounded-lg bg-primary-50 px-3 py-1.5 text-sm font-medium text-primary-700 hover:bg-primary-100 disabled:opacity-50 dark:bg-primary-900/30 dark:text-primary-300"
                  :disabled="generatingDraftId === topic.id"
                  @click="generateDraft(topic)"
                >
                  <Zap class="h-4 w-4" :class="{ 'animate-pulse': generatingDraftId === topic.id }" />
                  {{ generatingDraftId === topic.id ? t('growth.generating') : t('growth.generateDraft') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- DRAFTS TAB -->
        <div v-if="activeTab === 'drafts'" class="flex flex-col gap-4">
          <EmptyState v-if="!drafts.length" :title="t('growth.noDrafts')" :description="t('growth.noDraftsHint')" />

          <div v-else class="flex flex-col gap-3">
            <div
              v-for="draft in drafts"
              :key="draft.id"
              class="cursor-pointer rounded-xl border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-900"
              @click="openDraft(draft)"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusBadge(draft.status)]">{{ draft.status }}</span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">{{ draft.content_type }}</span>
                    <span class="text-xs text-gray-400">Quality: <span :class="scoreColor(draft.quality_score)">{{ draft.quality_score }}</span></span>
                  </div>
                  <p class="mt-1 font-medium text-gray-900 line-clamp-1 dark:text-white">{{ draft.hook }}</p>
                  <p class="mt-0.5 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{{ draft.body }}</p>
                </div>
                <ChevronRight class="h-5 w-5 shrink-0 text-gray-400" />
              </div>
            </div>
          </div>
        </div>

        <!-- CONFIG TAB -->
        <div v-if="activeTab === 'config'" class="max-w-2xl rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
          <div class="flex flex-col gap-5">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.enabled') }}</span>
              <button
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                :class="configForm.enabled ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'"
                @click="configForm.enabled = !configForm.enabled"
              >
                <span
                  class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                  :class="configForm.enabled ? 'translate-x-6' : 'translate-x-1'"
                />
              </button>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.brandName') }}</label>
                <input v-model="configForm.brand_name" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.language') }}</label>
                <select v-model="configForm.language" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">English</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.tone') }}</label>
                <select v-model="configForm.tone" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
                  <option value="friendly">Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="humorous">Humorous</option>
                  <option value="inspirational">Inspirational</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.postsPerDay') }}</label>
                <input v-model.number="configForm.posts_per_day" type="number" min="1" max="20" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.categories') }}</label>
              <input v-model="configForm.content_categories" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" :placeholder="t('growth.categoriesPlaceholder')" />
              <p class="mt-1 text-xs text-gray-400">{{ t('growth.categoriesHint') }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.blockedKeywords') }}</label>
              <input v-model="configForm.blocked_keywords" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" :placeholder="t('growth.blockedPlaceholder')" />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('growth.qualityThreshold') }}: {{ configForm.quality_threshold }}</label>
              <input v-model.number="configForm.quality_threshold" type="range" min="0" max="100" class="mt-2 w-full" />
            </div>

            <div class="flex justify-end">
              <button
                class="rounded-lg bg-primary-600 px-5 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                :disabled="savingConfig"
                @click="saveConfig"
              >
                {{ savingConfig ? t('common.loading') : t('common.save') }}
              </button>
            </div>
          </div>
        </div>

        <!-- INSIGHTS TAB -->
        <div v-if="activeTab === 'insights'">
          <div v-if="!insights" class="text-center py-12 text-gray-400">{{ t('common.noData') }}</div>
          <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div v-for="(val, key) in insights" :key="key" class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
              <p class="text-xs text-gray-400 uppercase tracking-wide">{{ key }}</p>
              <p class="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{{ val }}</p>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- Draft detail modal -->
    <BaseModal v-model="showDraftModal" :title="t('growth.draftDetail')">
      <div v-if="activeDraft" class="flex flex-col gap-4 p-4 max-h-[70vh] overflow-y-auto">
        <div class="flex items-center gap-2">
          <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusBadge(activeDraft.status)]">{{ activeDraft.status }}</span>
          <span class="text-xs text-gray-400">Quality: {{ activeDraft.quality_score }}</span>
        </div>
        <div>
          <p class="text-xs font-medium uppercase text-gray-400">Hook</p>
          <p class="mt-1 text-gray-900 dark:text-white">{{ activeDraft.hook }}</p>
        </div>
        <div>
          <p class="text-xs font-medium uppercase text-gray-400">Body</p>
          <p class="mt-1 whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">{{ activeDraft.body }}</p>
        </div>
        <div v-if="activeDraft.hashtags">
          <p class="text-xs font-medium uppercase text-gray-400">Hashtags</p>
          <p class="mt-1 text-sm text-primary-600">{{ activeDraft.hashtags }}</p>
        </div>
        <div v-if="activeDraft.review_notes">
          <p class="text-xs font-medium uppercase text-gray-400">Review notes</p>
          <p class="mt-1 text-sm text-gray-500">{{ activeDraft.review_notes }}</p>
        </div>
      </div>
      <template v-if="activeDraft && (activeDraft.status === 'pending_review' || activeDraft.status === 'draft')" #footer>
        <div class="flex justify-end gap-2 px-4 pb-4">
          <button
            class="flex items-center gap-1.5 rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400"
            @click="activeDraft && rejectDraft(activeDraft)"
          >
            <XCircle class="h-4 w-4" />{{ t('growth.reject') }}
          </button>
          <button
            class="flex items-center gap-1.5 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            @click="activeDraft && approveDraft(activeDraft)"
          >
            <CheckCircle2 class="h-4 w-4" />{{ t('growth.approve') }}
          </button>
        </div>
      </template>
    </BaseModal>
  </div>
</template>
