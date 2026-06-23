<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Pencil, Trash2, Play, History } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { jobService, facebookService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import { formatDate } from '@/utils/format'
import {
  buildCron,
  defaultSchedule,
  monthNames,
  parseCron,
  weekdayNames,
  type Frequency,
  type ScheduleForm,
} from '@/utils/schedule'
import type { Job, JobHistory, FacebookPage } from '@/types'

const CONTENT_TYPES = ['short_post', 'long_post', 'news', 'seo', 'marketing', 'educational', 'question', 'quote']
const FREQUENCIES: Frequency[] = ['hourly', 'daily', 'weekly', 'monthly', 'yearly', 'interval', 'custom']

const { t, locale } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { loading: mutating, run } = useAsync()

const loading = ref(false)
const jobs = ref<Job[]>([])
const pages = ref<FacebookPage[]>([])

const showForm = ref(false)
const showConfirm = ref(false)
const showHistory = ref(false)
const editing = ref<Job | null>(null)
const deleteId = ref<string | null>(null)
const historyLoading = ref(false)
const historyRows = ref<JobHistory[]>([])

const form = reactive({
  name: '',
  job_type: 'generate_content',
  timezone: 'UTC',
  enabled: true,
  content_type: 'short_post',
  language: 'en',
  auto_publish: false,
  require_approval: false,
  facebook_page_id: '' as string,
})
const schedule = reactive<ScheduleForm>(defaultSchedule())

const weekdays = computed(() => weekdayNames(locale.value))
const months = computed(() => monthNames(locale.value))

const columns = [
  { key: 'name', label: t('common.name') },
  { key: 'job_type', label: t('jobs.jobType') },
  { key: 'enabled', label: t('common.enabled') },
  { key: 'schedule', label: t('jobs.cron') },
  { key: 'last_run_at', label: t('jobs.lastRun') },
  { key: 'next_run_at', label: t('jobs.nextRun') },
  { key: 'actions', label: t('common.actions'), class: 'text-right' },
]

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    jobs.value = await jobService.list(projectId.value)
    pages.value = await facebookService.listPages(projectId.value).catch(() => [])
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)

function applySchedule(s: ScheduleForm) {
  Object.assign(schedule, s)
}

function describeSchedule(job: Job): string {
  if (job.interval_seconds) return t('jobs.scheduleDesc.interval', { seconds: job.interval_seconds })
  if (!job.cron_expression) return '—'
  const s = parseCron(job.cron_expression)
  const params = {
    time: s.time,
    minute: s.time.split(':')[1],
    day: weekdays.value[s.dayOfWeek] ?? '',
    dom: s.dayOfMonth,
    month: months.value[s.month - 1] ?? '',
  }
  if (s.frequency === 'custom') return job.cron_expression
  return t(`jobs.scheduleDesc.${s.frequency}`, params)
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.job_type = 'generate_content'
  form.timezone = 'UTC'
  form.enabled = true
  form.content_type = 'short_post'
  form.language = 'en'
  form.auto_publish = false
  form.require_approval = false
  form.facebook_page_id = ''
  applySchedule(defaultSchedule())
  showForm.value = true
}

function openEdit(job: Job) {
  editing.value = job
  form.name = job.name
  form.job_type = job.job_type
  form.timezone = job.timezone || 'UTC'
  form.enabled = job.enabled
  form.content_type = job.content_type || 'short_post'
  form.language = job.language || 'en'
  form.auto_publish = job.auto_publish
  form.require_approval = job.require_approval
  form.facebook_page_id = job.facebook_page_id ?? ''
  if (job.interval_seconds) {
    applySchedule({ ...defaultSchedule(), frequency: 'interval', intervalSeconds: job.interval_seconds })
  } else {
    applySchedule(parseCron(job.cron_expression ?? ''))
  }
  showForm.value = true
}

async function save() {
  if (!projectId.value) return
  const pid = projectId.value
  if (form.auto_publish && !form.facebook_page_id) {
    toast.error(t('jobs.selectPageRequired'))
    return
  }
  const cron = buildCron(schedule)
  if (schedule.frequency === 'custom' && !cron) {
    toast.error(t('jobs.cronRequired'))
    return
  }
  const payload = {
    name: form.name,
    job_type: form.job_type,
    timezone: form.timezone || 'UTC',
    enabled: form.enabled,
    content_type: form.content_type,
    language: form.language,
    auto_publish: form.auto_publish,
    require_approval: form.auto_publish ? form.require_approval : false,
    facebook_page_id: form.auto_publish ? form.facebook_page_id || null : null,
    ...(cron === null
      ? { interval_seconds: schedule.intervalSeconds, cron_expression: null }
      : { cron_expression: cron, interval_seconds: null }),
  }
  const action = editing.value
    ? () => jobService.update(editing.value!.id, payload)
    : () => jobService.create(pid, payload)
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok) {
    showForm.value = false
    await load()
  }
}

async function toggleEnabled(job: Job, enabled: boolean) {
  await run(() => jobService.update(job.id, { enabled }), { successMessage: t('common.saved') })
  await load()
}

async function runNow(job: Job) {
  const ok = await run(() => jobService.run(job.id))
  if (ok !== undefined) {
    toast.success(t('jobs.triggered'))
    await load()
  }
}

async function openHistory(job: Job) {
  showHistory.value = true
  historyRows.value = []
  historyLoading.value = true
  try {
    historyRows.value = await jobService.history(job.id)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    historyLoading.value = false
  }
}

function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  await run(() => jobService.remove(deleteId.value!), { successMessage: t('common.deleted') })
  await load()
}
</script>

<template>
  <div>
    <PageHeader :title="t('jobs.title')">
      <template #actions>
        <button class="btn-primary" :disabled="!hasProject" @click="openCreate">
          <Plus class="h-4 w-4" /> {{ t('jobs.newJob') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <EmptyState v-else-if="!jobs.length" :message="t('common.noData')">
      <button class="btn-primary" @click="openCreate">{{ t('jobs.newJob') }}</button>
    </EmptyState>

    <DataTable v-else :columns="columns" :rows="jobs">
      <template #cell-name="{ row }">
        <span class="font-medium text-gray-900 dark:text-gray-100">{{ row.name }}</span>
      </template>
      <template #cell-enabled="{ row }">
        <ToggleSwitch :model-value="row.enabled" :disabled="mutating" @update:model-value="toggleEnabled(row, $event)" />
      </template>
      <template #cell-schedule="{ row }">
        <span class="text-xs text-gray-600 dark:text-gray-300">{{ describeSchedule(row) }}</span>
      </template>
      <template #cell-last_run_at="{ row }">
        <span class="text-xs text-gray-500">{{ formatDate(row.last_run_at) }}</span>
      </template>
      <template #cell-next_run_at="{ row }">
        <span class="text-xs text-gray-500">{{ formatDate(row.next_run_at) }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-1">
          <button class="btn-ghost" :disabled="mutating" :title="t('common.runNow')" @click="runNow(row)">
            <Play class="h-4 w-4" />
          </button>
          <button class="btn-ghost" :title="t('jobs.history')" @click="openHistory(row)">
            <History class="h-4 w-4" />
          </button>
          <button class="btn-ghost" :title="t('common.edit')" @click="openEdit(row)">
            <Pencil class="h-4 w-4" />
          </button>
          <button class="btn-ghost text-red-600" :title="t('common.delete')" @click="confirmDelete(row.id)">
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </template>
    </DataTable>

    <!-- Create / Edit -->
    <BaseModal v-model="showForm" :title="editing ? t('jobs.editJob') : t('jobs.newJob')">
      <form class="space-y-4" @submit.prevent="save">
        <div>
          <label class="label">{{ t('common.name') }}</label>
          <input v-model="form.name" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('jobs.jobType') }}</label>
          <input v-model="form.job_type" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('jobs.frequency') }}</label>
          <select v-model="schedule.frequency" class="input">
            <option v-for="f in FREQUENCIES" :key="f" :value="f">{{ t(`jobs.freq.${f}`) }}</option>
          </select>
        </div>

        <div v-if="schedule.frequency === 'interval'">
          <label class="label">{{ t('jobs.interval') }}</label>
          <input v-model.number="schedule.intervalSeconds" type="number" min="1" required class="input" />
        </div>
        <div v-else-if="schedule.frequency === 'custom'">
          <label class="label">{{ t('jobs.cron') }}</label>
          <input v-model="schedule.cron" placeholder="0 * * * *" required class="input" />
          <p class="mt-1 text-xs text-gray-500">{{ t('jobs.cronHint') }}</p>
        </div>
        <template v-else>
          <div class="grid gap-3" :class="schedule.frequency === 'hourly' ? 'grid-cols-1' : 'grid-cols-2'">
            <div v-if="schedule.frequency === 'weekly'">
              <label class="label">{{ t('jobs.dayOfWeek') }}</label>
              <select v-model.number="schedule.dayOfWeek" class="input">
                <option v-for="(d, i) in weekdays" :key="i" :value="i">{{ d }}</option>
              </select>
            </div>
            <div v-if="schedule.frequency === 'monthly' || schedule.frequency === 'yearly'">
              <label class="label">{{ t('jobs.dayOfMonth') }}</label>
              <select v-model.number="schedule.dayOfMonth" class="input">
                <option v-for="n in 31" :key="n" :value="n">{{ n }}</option>
              </select>
            </div>
            <div v-if="schedule.frequency === 'yearly'">
              <label class="label">{{ t('jobs.month') }}</label>
              <select v-model.number="schedule.month" class="input">
                <option v-for="(m, i) in months" :key="i" :value="i + 1">{{ m }}</option>
              </select>
            </div>
            <div>
              <label class="label">{{ schedule.frequency === 'hourly' ? t('jobs.minute') : t('jobs.time') }}</label>
              <input v-model="schedule.time" type="time" required class="input" />
              <p v-if="schedule.frequency === 'hourly'" class="mt-1 text-xs text-gray-500">{{ t('jobs.minuteHint') }}</p>
            </div>
          </div>
        </template>

        <div v-if="schedule.frequency !== 'interval'">
          <label class="label">{{ t('jobs.timezone') }}</label>
          <input v-model="form.timezone" class="input" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">{{ t('jobs.contentType') }}</label>
            <select v-model="form.content_type" class="input">
              <option v-for="ct in CONTENT_TYPES" :key="ct" :value="ct">{{ ct }}</option>
            </select>
          </div>
          <div>
            <label class="label">{{ t('jobs.language') }}</label>
            <select v-model="form.language" class="input">
              <option value="en">English</option>
              <option value="vi">Tiếng Việt</option>
            </select>
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          <div class="flex items-center gap-3">
            <ToggleSwitch v-model="form.auto_publish" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('jobs.autoPublish') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500">{{ t('jobs.autoPublishHint') }}</p>

          <div v-if="form.auto_publish" class="mt-3 space-y-3">
            <div>
              <label class="label">{{ t('jobs.facebookPage') }}</label>
              <select v-model="form.facebook_page_id" class="input" required>
                <option value="" disabled>{{ t('jobs.selectPage') }}</option>
                <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.page_name }}</option>
              </select>
              <p v-if="!pages.length" class="mt-1 text-xs text-amber-600">{{ t('jobs.noPages') }}</p>
            </div>
            <div class="flex items-center gap-3">
              <ToggleSwitch v-model="form.require_approval" />
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ t('jobs.requireApproval') }}</span>
            </div>
            <p class="text-xs text-gray-500">{{ t('jobs.requireApprovalHint') }}</p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <ToggleSwitch v-model="form.enabled" />
          <span class="text-sm text-gray-700 dark:text-gray-300">{{ t('common.enabled') }}</span>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showForm = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary" :disabled="mutating">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <!-- History -->
    <BaseModal v-model="showHistory" :title="t('jobs.history')">
      <LoadingSpinner v-if="historyLoading" :label="t('common.loading')" />
      <EmptyState v-else-if="!historyRows.length" :message="t('common.noData')" />
      <table v-else class="w-full text-left text-sm">
        <thead class="border-b border-gray-200 text-xs uppercase text-gray-500 dark:border-gray-800">
          <tr>
            <th class="py-2 pr-3 font-medium">{{ t('common.status') }}</th>
            <th class="py-2 pr-3 font-medium">{{ t('jobs.lastRun') }}</th>
            <th class="py-2 pr-3 font-medium">{{ t('logs.message') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
          <tr v-for="h in historyRows" :key="h.id">
            <td class="py-2 pr-3"><StatusBadge :status="h.status" /></td>
            <td class="py-2 pr-3 text-xs text-gray-500">{{ formatDate(h.started_at) }}</td>
            <td class="py-2 pr-3 text-xs text-gray-500">{{ h.message || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <div class="mt-6 flex justify-end">
        <button class="btn-secondary" @click="showHistory = false">{{ t('common.close') }}</button>
      </div>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
