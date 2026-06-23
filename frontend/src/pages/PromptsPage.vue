<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Pencil, Trash2, Play } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { promptService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import type { PromptTemplate, SystemPrompt } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { loading: saving, run } = useAsync()

const tab = ref<'templates' | 'system'>('templates')

const loading = ref(false)
const templates = ref<PromptTemplate[]>([])
const systemPrompts = ref<SystemPrompt[]>([])

// ----- Template editor state -----
const showTemplateForm = ref(false)
const editingTemplate = ref<PromptTemplate | null>(null)
const templateForm = reactive({
  name: '',
  type: '',
  template: '',
  language: 'en',
  active: true,
})
const variablesJson = ref('{}')
const rendered = ref('')
const rendering = ref(false)

// ----- System prompt editor state -----
const showSystemForm = ref(false)
const editingSystem = ref<SystemPrompt | null>(null)
const systemForm = reactive({ name: '', content: '', active: true })

// ----- Delete state -----
const showConfirm = ref(false)
const deleteId = ref<string | null>(null)

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    const pid = projectId.value
    const [tpls, sys] = await Promise.all([
      promptService.listTemplates(pid),
      promptService.listSystem(pid),
    ])
    templates.value = tpls
    systemPrompts.value = sys
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)

// ----- Templates -----
function openCreateTemplate() {
  editingTemplate.value = null
  templateForm.name = ''
  templateForm.type = ''
  templateForm.template = ''
  templateForm.language = 'en'
  templateForm.active = true
  variablesJson.value = '{}'
  rendered.value = ''
  showTemplateForm.value = true
}

function openEditTemplate(tpl: PromptTemplate) {
  editingTemplate.value = tpl
  templateForm.name = tpl.name
  templateForm.type = tpl.type
  templateForm.template = tpl.template
  templateForm.language = tpl.language
  templateForm.active = tpl.active
  variablesJson.value = '{}'
  rendered.value = ''
  showTemplateForm.value = true
}

async function saveTemplate() {
  if (!projectId.value) return
  const action = editingTemplate.value
    ? () => promptService.update(editingTemplate.value!.id, { ...templateForm })
    : () =>
        promptService.createTemplate(projectId.value!, {
          name: templateForm.name,
          type: templateForm.type,
          template: templateForm.template,
          language: templateForm.language,
          active: templateForm.active,
        })
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok !== undefined) {
    showTemplateForm.value = false
    await load()
  }
}

async function renderPreview() {
  let variables: Record<string, unknown>
  try {
    variables = JSON.parse(variablesJson.value)
  } catch {
    toast.error(t('prompts.variables'))
    return
  }
  rendering.value = true
  try {
    const result = await promptService.render({ template: templateForm.template, variables })
    rendered.value = result.rendered
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    rendering.value = false
  }
}

// ----- System prompts -----
function openCreateSystem() {
  editingSystem.value = null
  systemForm.name = ''
  systemForm.content = ''
  systemForm.active = true
  showSystemForm.value = true
}

function openEditSystem(sp: SystemPrompt) {
  editingSystem.value = sp
  systemForm.name = sp.name
  systemForm.content = sp.content
  systemForm.active = sp.active
  showSystemForm.value = true
}

async function saveSystem() {
  if (!projectId.value) return
  const action = async (): Promise<void> => {
    if (editingSystem.value) {
      await promptService.updateSystem(editingSystem.value.id, {
        name: systemForm.name,
        content: systemForm.content,
        active: systemForm.active,
      })
    } else {
      await promptService.createSystem(projectId.value!, {
        name: systemForm.name,
        content: systemForm.content,
      })
    }
  }
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok !== undefined) {
    showSystemForm.value = false
    await load()
  }
}

// ----- Delete (shared) -----
function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  const id = deleteId.value
  const remove = tab.value === 'system' ? promptService.removeSystem : promptService.remove
  const ok = await run(() => remove(id), { successMessage: t('common.deleted') })
  if (ok !== undefined) await load()
}
</script>

<template>
  <div>
    <PageHeader :title="t('prompts.title')">
      <template #actions>
        <button v-if="hasProject && tab === 'templates'" class="btn-primary" @click="openCreateTemplate">
          <Plus class="h-4 w-4" /> {{ t('prompts.newTemplate') }}
        </button>
        <button v-else-if="hasProject" class="btn-primary" @click="openCreateSystem">
          <Plus class="h-4 w-4" /> {{ t('common.create') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <template v-else>
      <div class="mb-6 flex gap-1 border-b border-gray-200 dark:border-gray-800">
        <button
          class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
          :class="tab === 'templates'
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'"
          @click="tab = 'templates'"
        >
          {{ t('prompts.templates') }}
        </button>
        <button
          class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
          :class="tab === 'system'
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'"
          @click="tab = 'system'"
        >
          {{ t('prompts.systemPrompts') }}
        </button>
      </div>

      <LoadingSpinner v-if="loading" :label="t('common.loading')" />

      <!-- Templates tab -->
      <template v-else-if="tab === 'templates'">
        <EmptyState v-if="!templates.length" :message="t('common.noData')">
          <button class="btn-primary" @click="openCreateTemplate">{{ t('prompts.newTemplate') }}</button>
        </EmptyState>
        <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="tpl in templates" :key="tpl.id" class="card flex flex-col p-5">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white">{{ tpl.name }}</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  {{ tpl.type }} · {{ tpl.language }} · v{{ tpl.version }}
                </p>
              </div>
              <span
                class="badge"
                :class="tpl.active
                  ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-800'"
              >
                {{ tpl.active ? t('common.enabled') : t('common.disabled') }}
              </span>
            </div>
            <p class="mt-2 line-clamp-3 flex-1 font-mono text-xs text-gray-500 dark:text-gray-400">
              {{ tpl.template }}
            </p>
            <div class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
              <button class="btn-ghost flex-1 text-sm" @click="openEditTemplate(tpl)">
                <Pencil class="h-4 w-4" /> {{ t('common.edit') }}
              </button>
              <button class="btn-ghost text-red-600" @click="confirmDelete(tpl.id)">
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- System prompts tab -->
      <template v-else>
        <EmptyState v-if="!systemPrompts.length" :message="t('common.noData')">
          <button class="btn-primary" @click="openCreateSystem">{{ t('common.create') }}</button>
        </EmptyState>
        <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="sp in systemPrompts" :key="sp.id" class="card flex flex-col p-5">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white">{{ sp.name }}</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">v{{ sp.version }}</p>
              </div>
              <span
                class="badge"
                :class="sp.active
                  ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-800'"
              >
                {{ sp.active ? t('common.enabled') : t('common.disabled') }}
              </span>
            </div>
            <p class="mt-2 line-clamp-3 flex-1 text-xs text-gray-500 dark:text-gray-400">
              {{ sp.content }}
            </p>
            <div class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
              <button class="btn-ghost flex-1 text-sm" @click="openEditSystem(sp)">
                <Pencil class="h-4 w-4" /> {{ t('common.edit') }}
              </button>
              <button class="btn-ghost text-red-600" @click="confirmDelete(sp.id)">
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- Template modal -->
    <BaseModal
      v-model="showTemplateForm"
      :title="editingTemplate ? t('prompts.editTemplate') : t('prompts.newTemplate')"
    >
      <form class="space-y-4" @submit.prevent="saveTemplate">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">{{ t('common.name') }}</label>
            <input v-model="templateForm.name" required class="input" />
          </div>
          <div>
            <label class="label">{{ t('prompts.type') }}</label>
            <input v-model="templateForm.type" required class="input" />
          </div>
        </div>
        <div>
          <label class="label">{{ t('common.language') }}</label>
          <select v-model="templateForm.language" class="input">
            <option value="en">en</option>
            <option value="vi">vi</option>
          </select>
        </div>
        <div>
          <label class="label">{{ t('prompts.template') }}</label>
          <textarea v-model="templateForm.template" rows="6" required class="input font-mono text-sm"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <ToggleSwitch v-model="templateForm.active" />
          <span class="text-sm text-gray-600 dark:text-gray-300">{{ t('common.enabled') }}</span>
        </div>

        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
          <label class="label">{{ t('prompts.variables') }}</label>
          <textarea v-model="variablesJson" rows="3" class="input font-mono text-sm"></textarea>
          <button type="button" class="btn-secondary mt-2" :disabled="rendering" @click="renderPreview">
            <Play class="h-4 w-4" /> {{ t('prompts.renderPreview') }}
          </button>
          <div v-if="rendered" class="mt-3">
            <label class="label">{{ t('prompts.rendered') }}</label>
            <pre
              class="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-200"
            >{{ rendered }}</pre>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showTemplateForm = false">
            {{ t('common.cancel') }}
          </button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <!-- System prompt modal -->
    <BaseModal v-model="showSystemForm" :title="editingSystem ? t('common.edit') : t('common.create')">
      <form class="space-y-4" @submit.prevent="saveSystem">
        <div>
          <label class="label">{{ t('common.name') }}</label>
          <input v-model="systemForm.name" required class="input" />
        </div>
        <div>
          <label class="label">{{ t('prompts.content') }}</label>
          <textarea v-model="systemForm.content" rows="8" required class="input font-mono text-sm"></textarea>
        </div>
        <div v-if="editingSystem" class="flex items-center gap-2">
          <ToggleSwitch v-model="systemForm.active" />
          <span class="text-sm text-gray-600 dark:text-gray-300">{{ t('common.enabled') }}</span>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showSystemForm = false">
            {{ t('common.cancel') }}
          </button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
