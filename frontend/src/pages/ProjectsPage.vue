<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Pencil, Trash2, CheckCircle2, Circle } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { useProjectStore } from '@/stores/project'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import { formatDateShort } from '@/utils/format'
import type { Project } from '@/types'

const { t } = useI18n()
const projectStore = useProjectStore()
const toast = useToastStore()
const { loading, run } = useAsync()

const showForm = ref(false)
const showConfirm = ref(false)
const editing = ref<Project | null>(null)
const deleteId = ref<string | null>(null)
const form = reactive({ name: '', description: '' })

onMounted(async () => {
  if (!projectStore.projects.length) {
    await run(() => projectStore.fetchProjects())
  }
})

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  showForm.value = true
}

function openEdit(p: Project) {
  editing.value = p
  form.name = p.name
  form.description = p.description
  showForm.value = true
}

async function save() {
  const action = async (): Promise<Project> => {
    if (editing.value) {
      return await projectStore.updateProject(editing.value.id, { ...form })
    }
    return await projectStore.createProject(form.name, form.description)
  }
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok !== undefined) showForm.value = false
}

function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  await run(() => projectStore.deleteProject(deleteId.value!), { successMessage: t('common.deleted') })
}

function selectProject(id: string) {
  projectStore.select(id)
  toast.info(t('projects.selectProject'))
}
</script>

<template>
  <div>
    <PageHeader :title="t('projects.title')">
      <template #actions>
        <button class="btn-primary" @click="openCreate">
          <Plus class="h-4 w-4" /> {{ t('projects.newProject') }}
        </button>
      </template>
    </PageHeader>

    <LoadingSpinner v-if="loading && !projectStore.projects.length" />
    <EmptyState v-else-if="!projectStore.projects.length" :message="t('projects.noProjects')">
      <button class="btn-primary" @click="openCreate">{{ t('projects.newProject') }}</button>
    </EmptyState>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="p in projectStore.projects"
        :key="p.id"
        class="card flex flex-col p-5 transition-shadow hover:shadow-md"
        :class="p.id === projectStore.currentProjectId ? 'ring-2 ring-primary-500' : ''"
      >
        <div class="flex items-start justify-between">
          <h3 class="font-semibold text-gray-900 dark:text-white">{{ p.name }}</h3>
          <span
            class="badge"
            :class="p.active ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800'"
          >
            {{ p.active ? t('projects.active') : t('common.disabled') }}
          </span>
        </div>
        <p class="mt-2 line-clamp-2 flex-1 text-sm text-gray-500 dark:text-gray-400">
          {{ p.description || '—' }}
        </p>
        <p class="mt-3 text-xs text-gray-400">{{ formatDateShort(p.created_at) }}</p>
        <div class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
          <button
            class="btn-ghost flex-1 text-sm"
            @click="selectProject(p.id)"
          >
            <component :is="p.id === projectStore.currentProjectId ? CheckCircle2 : Circle" class="h-4 w-4" />
            {{ t('projects.selectProject') }}
          </button>
          <button class="btn-ghost" @click="openEdit(p)"><Pencil class="h-4 w-4" /></button>
          <button class="btn-ghost text-red-600" @click="confirmDelete(p.id)"><Trash2 class="h-4 w-4" /></button>
        </div>
      </div>
    </div>

    <BaseModal v-model="showForm" :title="editing ? t('projects.editProject') : t('projects.newProject')">
      <form class="space-y-4" @submit.prevent="save">
        <div>
          <label class="label">{{ t('common.name') }}</label>
          <input v-model="form.name" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('common.description') }}</label>
          <textarea v-model="form.description" rows="3" class="input"></textarea>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showForm = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary" :disabled="loading">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
