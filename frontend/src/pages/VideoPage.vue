<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Video, Cpu, Plus, XCircle, RefreshCw, ExternalLink,
} from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { videoService, facebookService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import type { FacebookPage, VideoJob, GPUInstance } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()

type Tab = 'jobs' | 'gpu'
const activeTab = ref<Tab>('jobs')

const pages = ref<FacebookPage[]>([])
const selectedPageId = ref('')

const jobs = ref<VideoJob[]>([])
const gpuInstances = ref<GPUInstance[]>([])

const loading = ref(false)
const showCreateModal = ref(false)
const creating = ref(false)
const cleaningUp = ref(false)

const form = ref({
  title: '',
  script: '',
  voice_id: 'vi-VN-HoaiMyNeural',
  language: 'vi',
  avatar_image_url: '',
})

const voiceOptions = [
  { value: 'vi-VN-HoaiMyNeural', label: 'Hoài My (Vi, Female)' },
  { value: 'vi-VN-NamMinhNeural', label: 'Nam Minh (Vi, Male)' },
  { value: 'en-US-JennyNeural', label: 'Jenny (En, Female)' },
  { value: 'en-US-GuyNeural', label: 'Guy (En, Male)' },
]

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

async function loadJobs() {
  if (!selectedPageId.value) return
  loading.value = true
  try {
    jobs.value = await videoService.listJobs(selectedPageId.value)
  } catch {
    jobs.value = []
  } finally {
    loading.value = false
  }
}

async function loadGPU() {
  try {
    gpuInstances.value = await videoService.listGPUInstances()
  } catch {
    gpuInstances.value = []
  }
}

async function createJob() {
  if (!form.value.title || !form.value.script) return
  creating.value = true
  try {
    const job = await videoService.createJob(selectedPageId.value, {
      title: form.value.title,
      script: form.value.script,
      voice_id: form.value.voice_id,
      language: form.value.language,
      avatar_image_url: form.value.avatar_image_url || undefined,
    })
    jobs.value.unshift(job)
    showCreateModal.value = false
    form.value = { title: '', script: '', voice_id: 'vi-VN-HoaiMyNeural', language: 'vi', avatar_image_url: '' }
    toast.success(t('video.jobCreated'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

async function cancelJob(job: VideoJob) {
  try {
    const updated = await videoService.cancelJob(job.id)
    const idx = jobs.value.findIndex(j => j.id === job.id)
    if (idx !== -1) jobs.value[idx] = updated
    toast.success(t('video.jobCancelled'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  }
}

async function cleanupGPU() {
  cleaningUp.value = true
  try {
    const result = await videoService.cleanupGPU()
    toast.success(t('video.gpuCleaned', { count: (result as { cleaned: number }).cleaned }))
    await loadGPU()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    cleaningUp.value = false
  }
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    waiting_gpu: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    starting_gpu: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    uploading: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    processing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    downloading: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    published: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    cancelled: 'bg-gray-100 text-gray-400',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

function isActive(status: string) {
  return ['pending', 'waiting_gpu', 'starting_gpu', 'uploading', 'processing', 'downloading'].includes(status)
}

function fmtDuration(secs: number | null) {
  if (!secs) return '—'
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

const tabs = [
  { key: 'jobs' as Tab, label: 'video.tabs.jobs', icon: Video },
  { key: 'gpu' as Tab, label: 'video.tabs.gpu', icon: Cpu },
]

onMounted(() => { loadPages(); loadGPU() })
watch(selectedPageId, loadJobs)
watch(projectId, () => { selectedPageId.value = ''; loadPages() })
watch(activeTab, (t) => { if (t === 'gpu') loadGPU() })
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <PageHeader :title="t('video.title')" :subtitle="t('video.subtitle')" />

    <NoProjectNotice v-if="!hasProject" />

    <template v-else>
      <!-- Page selector -->
      <div class="flex items-center gap-3">
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.page') }}</label>
        <select
          v-model="selectedPageId"
          class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
        >
          <option value="" disabled>{{ t('video.selectPage') }}</option>
          <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.page_name }}</option>
        </select>
      </div>

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

      <!-- JOBS TAB -->
      <div v-if="activeTab === 'jobs'" class="flex flex-col gap-4">
        <div v-if="!selectedPageId" class="rounded-xl border border-dashed border-gray-300 p-12 text-center text-gray-400 dark:border-gray-700">
          {{ t('video.selectPageFirst') }}
        </div>

        <template v-else>
          <div class="flex justify-end">
            <button
              class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              @click="showCreateModal = true"
            >
              <Plus class="h-4 w-4" />
              {{ t('video.createJob') }}
            </button>
          </div>

          <LoadingSpinner v-if="loading" class="mx-auto" />
          <EmptyState v-else-if="!jobs.length" :title="t('video.noJobs')" :description="t('video.noJobsHint')" />

          <div v-else class="flex flex-col gap-3">
            <div
              v-for="job in jobs"
              :key="job.id"
              class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusBadge(job.status)]">
                      {{ job.status }}
                      <span v-if="isActive(job.status)" class="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                    </span>
                    <span class="text-xs text-gray-400">{{ job.language }} · {{ job.voice_id }}</span>
                    <span v-if="job.duration_seconds" class="text-xs text-gray-400">{{ fmtDuration(job.duration_seconds) }}</span>
                  </div>
                  <p class="mt-1 font-medium text-gray-900 dark:text-white">{{ job.title }}</p>
                  <p class="mt-0.5 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{{ job.script }}</p>
                  <p v-if="job.error_message" class="mt-1 text-xs text-red-500">{{ job.error_message }}</p>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <a
                    v-if="job.output_url"
                    :href="job.output_url"
                    target="_blank"
                    class="flex items-center gap-1 rounded-lg bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-300"
                  >
                    <ExternalLink class="h-4 w-4" />{{ t('video.viewVideo') }}
                  </a>
                  <button
                    v-if="isActive(job.status)"
                    class="flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400"
                    @click="cancelJob(job)"
                  >
                    <XCircle class="h-4 w-4" />{{ t('common.cancel') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- GPU TAB -->
      <div v-if="activeTab === 'gpu'" class="flex flex-col gap-4">
        <div class="flex justify-end">
          <button
            class="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300"
            :disabled="cleaningUp"
            @click="cleanupGPU"
          >
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': cleaningUp }" />
            {{ t('video.cleanupGPU') }}
          </button>
        </div>

        <EmptyState v-if="!gpuInstances.length" :title="t('video.noGPU')" :description="t('video.noGPUHint')" />

        <div v-else class="flex flex-col gap-3">
          <div
            v-for="inst in gpuInstances"
            :key="inst.id"
            class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
          >
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-gray-900 dark:text-white">{{ inst.provider }} · {{ inst.instance_id }}</p>
                <p class="text-sm text-gray-500">{{ inst.ip_address ?? '—' }}</p>
              </div>
              <div class="text-right">
                <span :class="['rounded-full px-2 py-0.5 text-xs font-medium', statusBadge(inst.status)]">{{ inst.status }}</span>
                <p class="mt-1 text-xs text-gray-400">${{ inst.cost_per_hour ?? '?' }}/hr</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Create Job Modal -->
    <BaseModal v-model="showCreateModal" :title="t('video.createJob')">
      <div class="flex flex-col gap-4 p-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.jobTitle') }}</label>
          <input v-model="form.title" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" :placeholder="t('video.jobTitlePlaceholder')" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.script') }}</label>
          <textarea v-model="form.script" rows="6" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" :placeholder="t('video.scriptPlaceholder')" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.voice') }}</label>
            <select v-model="form.voice_id" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option v-for="v in voiceOptions" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.language') }}</label>
            <select v-model="form.language" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('video.avatarUrl') }} <span class="text-gray-400">({{ t('common.optional') }})</span></label>
          <input v-model="form.avatar_image_url" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" placeholder="https://..." />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2 px-4 pb-4">
          <button class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300" @click="showCreateModal = false">{{ t('common.cancel') }}</button>
          <button
            class="rounded-lg bg-primary-600 px-5 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            :disabled="creating || !form.title || !form.script"
            @click="createJob"
          >
            {{ creating ? t('common.loading') : t('video.createJob') }}
          </button>
        </div>
      </template>
    </BaseModal>
  </div>
</template>
