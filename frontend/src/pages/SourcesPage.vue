<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Trash2, RefreshCw, HelpCircle } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { sourceService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import type { Keyword, RssSource, Topic } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { loading: mutating, run } = useAsync()

type Tab = 'rss' | 'topics' | 'keywords'
const tab = ref<Tab>('rss')

const loading = ref(false)
const showHelp = ref(false)
const rss = ref<RssSource[]>([])
const topics = ref<Topic[]>([])
const keywords = ref<Keyword[]>([])

const rssForm = reactive({ url: '' })
const topicForm = reactive({ topic: '', priority: 1 })
const keywordForm = reactive({ keyword: '', priority: 1 })

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    const pid = projectId.value
    const [r, tp, kw] = await Promise.all([
      sourceService.listRss(pid),
      sourceService.listTopics(pid),
      sourceService.listKeywords(pid),
    ])
    rss.value = r
    topics.value = tp
    keywords.value = kw
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)
watch(tab, () => {
  showHelp.value = false
})

async function sync() {
  if (!projectId.value) return
  const pid = projectId.value
  const result = await run(() => sourceService.sync(pid))
  if (result) {
    toast.success(t('sources.synced', { count: result.collected }))
    await load()
  }
}

async function addRss() {
  if (!projectId.value || !rssForm.url.trim()) return
  const pid = projectId.value
  const ok = await run(() => sourceService.addRss(pid, { url: rssForm.url.trim() }), {
    successMessage: t('common.created'),
  })
  if (ok) {
    rssForm.url = ''
    await load()
  }
}

async function removeRss(id: string) {
  await run(() => sourceService.removeRss(id), { successMessage: t('common.deleted') })
  await load()
}

async function addTopic() {
  if (!projectId.value || !topicForm.topic.trim()) return
  const pid = projectId.value
  const ok = await run(
    () => sourceService.addTopic(pid, { topic: topicForm.topic.trim(), priority: topicForm.priority }),
    { successMessage: t('common.created') },
  )
  if (ok) {
    topicForm.topic = ''
    topicForm.priority = 1
    await load()
  }
}

async function removeTopic(id: string) {
  await run(() => sourceService.removeTopic(id), { successMessage: t('common.deleted') })
  await load()
}

async function addKeyword() {
  if (!projectId.value || !keywordForm.keyword.trim()) return
  const pid = projectId.value
  const ok = await run(
    () => sourceService.addKeyword(pid, { keyword: keywordForm.keyword.trim(), priority: keywordForm.priority }),
    { successMessage: t('common.created') },
  )
  if (ok) {
    keywordForm.keyword = ''
    keywordForm.priority = 1
    await load()
  }
}

async function removeKeyword(id: string) {
  await run(() => sourceService.removeKeyword(id), { successMessage: t('common.deleted') })
  await load()
}

const tabs: { key: Tab; label: string }[] = [
  { key: 'rss', label: 'sources.rss' },
  { key: 'topics', label: 'sources.topics' },
  { key: 'keywords', label: 'sources.keywords' },
]
</script>

<template>
  <div>
    <PageHeader :title="t('sources.title')">
      <template #actions>
        <button class="btn-primary" :disabled="mutating || !hasProject" @click="sync">
          <RefreshCw class="h-4 w-4" /> {{ t('sources.syncNow') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <template v-else>
      <div class="mb-6 flex gap-1 border-b border-gray-200 dark:border-gray-800">
        <button
          v-for="tb in tabs"
          :key="tb.key"
          class="-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors"
          :class="
            tab === tb.key
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          "
          @click="tab = tb.key"
        >
          {{ t(tb.label) }}
        </button>
      </div>

      <LoadingSpinner v-if="loading" :label="t('common.loading')" />

      <!-- RSS -->
      <div v-else-if="tab === 'rss'">
        <form class="mb-4 flex gap-2" @submit.prevent="addRss">
          <input v-model="rssForm.url" :placeholder="t('sources.rssUrl')" required class="input flex-1" />
          <button type="submit" class="btn-primary" :disabled="mutating">
            <Plus class="h-4 w-4" /> {{ t('common.add') }}
          </button>
        </form>
        <EmptyState v-if="!rss.length" :message="t('common.noData')" />
        <ul v-else class="card divide-y divide-gray-100 dark:divide-gray-800">
          <li v-for="item in rss" :key="item.id" class="flex items-center justify-between gap-2 px-4 py-3">
            <span class="min-w-0 truncate text-sm text-gray-900 dark:text-gray-100">{{ item.url }}</span>
            <button class="btn-ghost text-red-600" :disabled="mutating" @click="removeRss(item.id)">
              <Trash2 class="h-4 w-4" />
            </button>
          </li>
        </ul>
      </div>

      <!-- Topics -->
      <div v-else-if="tab === 'topics'">
        <div class="mb-2 flex justify-end">
          <button
            type="button"
            class="btn-ghost text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
            :title="t('common.help')"
            @click="showHelp = !showHelp"
          >
            <HelpCircle class="h-4 w-4" />
          </button>
        </div>
        <div
          v-if="showHelp"
          class="mb-4 rounded-lg border border-primary-100 bg-primary-50 px-4 py-3 text-sm text-gray-600 dark:border-primary-900 dark:bg-primary-950/40 dark:text-gray-300"
        >
          {{ t('sources.topicsHelp') }}
        </div>
        <form class="mb-4 flex gap-2" @submit.prevent="addTopic">
          <input v-model="topicForm.topic" :placeholder="t('sources.topic')" required class="input flex-1" />
          <input
            v-model.number="topicForm.priority"
            type="number"
            min="1"
            :placeholder="t('common.priority')"
            class="input w-28"
          />
          <button type="submit" class="btn-primary" :disabled="mutating">
            <Plus class="h-4 w-4" /> {{ t('common.add') }}
          </button>
        </form>
        <EmptyState v-if="!topics.length" :message="t('common.noData')" />
        <ul v-else class="card divide-y divide-gray-100 dark:divide-gray-800">
          <li v-for="item in topics" :key="item.id" class="flex items-center justify-between gap-2 px-4 py-3">
            <div class="flex min-w-0 items-center gap-2">
              <span class="badge bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300">
                {{ item.priority }}
              </span>
              <span class="min-w-0 truncate text-sm text-gray-900 dark:text-gray-100">{{ item.topic }}</span>
            </div>
            <button class="btn-ghost text-red-600" :disabled="mutating" @click="removeTopic(item.id)">
              <Trash2 class="h-4 w-4" />
            </button>
          </li>
        </ul>
      </div>

      <!-- Keywords -->
      <div v-else>
        <div class="mb-2 flex justify-end">
          <button
            type="button"
            class="btn-ghost text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
            :title="t('common.help')"
            @click="showHelp = !showHelp"
          >
            <HelpCircle class="h-4 w-4" />
          </button>
        </div>
        <div
          v-if="showHelp"
          class="mb-4 rounded-lg border border-primary-100 bg-primary-50 px-4 py-3 text-sm text-gray-600 dark:border-primary-900 dark:bg-primary-950/40 dark:text-gray-300"
        >
          {{ t('sources.keywordsHelp') }}
        </div>
        <form class="mb-4 flex gap-2" @submit.prevent="addKeyword">
          <input v-model="keywordForm.keyword" :placeholder="t('sources.keyword')" required class="input flex-1" />
          <input
            v-model.number="keywordForm.priority"
            type="number"
            min="1"
            :placeholder="t('common.priority')"
            class="input w-28"
          />
          <button type="submit" class="btn-primary" :disabled="mutating">
            <Plus class="h-4 w-4" /> {{ t('common.add') }}
          </button>
        </form>
        <EmptyState v-if="!keywords.length" :message="t('common.noData')" />
        <ul v-else class="card divide-y divide-gray-100 dark:divide-gray-800">
          <li v-for="item in keywords" :key="item.id" class="flex items-center justify-between gap-2 px-4 py-3">
            <div class="flex min-w-0 items-center gap-2">
              <span class="badge bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300">
                {{ item.priority }}
              </span>
              <span class="min-w-0 truncate text-sm text-gray-900 dark:text-gray-100">{{ item.keyword }}</span>
            </div>
            <button class="btn-ghost text-red-600" :disabled="mutating" @click="removeKeyword(item.id)">
              <Trash2 class="h-4 w-4" />
            </button>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
