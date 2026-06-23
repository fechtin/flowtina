<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Pencil, Trash2, Zap, Loader2, RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { providerService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/services/http'
import type { Provider, ProviderPayload, ProviderTestResult, ProviderType } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()
const { loading: saving, run } = useAsync()

const PROVIDER_TYPES: ProviderType[] = [
  'openai',
  'groq',
  'gemini',
  'claude',
  'openrouter',
  'deepseek',
  'ollama',
  'lmstudio',
  'vllm',
  'custom',
]

// Suggested models per provider. The model field stays editable (datalist), so
// providers with arbitrary model names (ollama, vllm, custom) still accept any value.
const MODEL_PRESETS: Partial<Record<ProviderType, string[]>> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'o3-mini'],
  groq: [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'gemma2-9b-it',
  ],
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  claude: [
    'claude-sonnet-4-20250514',
    'claude-3-5-sonnet-latest',
    'claude-3-5-haiku-latest',
  ],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
}

// Models fetched live from the provider's API (e.g. Groq via its key). When
// present they take precedence over the static presets above.
const dynamicModels = ref<string[]>([])
const loadingModels = ref(false)

const availableModels = computed<string[]>(() => {
  const base = dynamicModels.value.length ? dynamicModels.value : MODEL_PRESETS[form.provider] ?? []
  // Keep the currently-selected model visible even if the API didn't list it.
  if (form.model && !base.includes(form.model)) return [form.model, ...base]
  return base
})

const loading = ref(false)
const providers = ref<Provider[]>([])

const showForm = ref(false)
const showConfirm = ref(false)
const editing = ref<Provider | null>(null)
const deleteId = ref<string | null>(null)

const form = reactive<ProviderPayload>({
  provider: 'openai',
  base_url: '',
  api_key: '',
  model: '',
  temperature: 0.7,
  top_p: 1,
  max_tokens: 2048,
  timeout_seconds: 60,
  system_prompt: '',
  priority: 0,
  enabled: true,
  grounding_enabled: false,
})
const existingMask = ref<string | null>(null)

const testPrompt = ref('Hello, respond with a short greeting.')
const testing = ref(false)
const testResult = ref<ProviderTestResult | null>(null)

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    providers.value = await providerService.list(projectId.value)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)

function resetForm() {
  form.provider = 'openai'
  form.base_url = ''
  form.api_key = ''
  form.model = ''
  form.temperature = 0.7
  form.top_p = 1
  form.max_tokens = 2048
  form.timeout_seconds = 60
  form.system_prompt = ''
  form.priority = 0
  form.enabled = true
  form.grounding_enabled = false
  existingMask.value = null
  testResult.value = null
  testPrompt.value = 'Hello, respond with a short greeting.'
  dynamicModels.value = []
}

// Discover the provider's available models. `silent` skips the empty/no-key
// toast so it can run automatically when the form opens or the provider changes.
async function fetchModels(silent = false) {
  loadingModels.value = true
  try {
    const models = await providerService.listModels({
      provider: form.provider,
      base_url: form.base_url?.trim() || undefined,
      api_key: form.api_key?.trim() || undefined,
    })
    dynamicModels.value = models
    if (models.length && !models.includes(form.model)) form.model = models[0]
    if (!models.length && !silent) toast.error(t('providers.noModels'))
  } catch (err) {
    if (!silent) toast.error(extractErrorMessage(err))
  } finally {
    loadingModels.value = false
  }
}

// Reset discovered models when switching provider, then try to auto-load them.
watch(
  () => form.provider,
  () => {
    dynamicModels.value = []
    if (showForm.value) fetchModels(true)
  },
)

function openCreate() {
  editing.value = null
  resetForm()
  showForm.value = true
  fetchModels(true)
}

function openEdit(p: Provider) {
  editing.value = p
  resetForm()
  form.provider = p.provider
  form.base_url = p.base_url ?? ''
  form.api_key = ''
  form.model = p.model
  form.temperature = p.temperature
  form.top_p = p.top_p
  form.max_tokens = p.max_tokens
  form.timeout_seconds = p.timeout_seconds
  form.system_prompt = p.system_prompt ?? ''
  form.priority = p.priority
  form.enabled = p.enabled
  form.grounding_enabled = p.grounding_enabled ?? false
  existingMask.value = p.api_key_masked ?? null
  showForm.value = true
  fetchModels(true)
}

function buildPayload(): ProviderPayload {
  return {
    provider: form.provider,
    base_url: form.base_url?.trim() || undefined,
    api_key: form.api_key?.trim() || undefined,
    model: form.model,
    temperature: Number(form.temperature),
    top_p: Number(form.top_p),
    max_tokens: Number(form.max_tokens),
    timeout_seconds: Number(form.timeout_seconds),
    system_prompt: form.system_prompt?.trim() || undefined,
    priority: Number(form.priority),
    enabled: form.enabled,
    grounding_enabled: form.grounding_enabled,
  }
}

async function save() {
  if (!projectId.value) return
  const payload = buildPayload()
  const action = editing.value
    ? () => providerService.update(editing.value!.id, payload)
    : () => providerService.create(projectId.value!, payload)
  const ok = await run(action, { successMessage: t('common.saved') })
  if (ok !== undefined) {
    showForm.value = false
    await load()
  }
}

async function toggleEnabled(p: Provider, value: boolean) {
  const ok = await run(() => providerService.update(p.id, { enabled: value }), {
    successMessage: t('common.saved'),
  })
  if (ok !== undefined) await load()
}

function confirmDelete(id: string) {
  deleteId.value = id
  showConfirm.value = true
}

async function doDelete() {
  if (!deleteId.value) return
  const ok = await run(() => providerService.remove(deleteId.value!), {
    successMessage: t('common.deleted'),
  })
  if (ok !== undefined) await load()
}

async function runTest() {
  if (!form.model) {
    toast.error(t('providers.model'))
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const result = await providerService.test({
      provider: form.provider,
      base_url: form.base_url?.trim() || undefined,
      api_key: form.api_key?.trim() || undefined,
      model: form.model,
      prompt: testPrompt.value,
    })
    testResult.value = result
    if (result.success) {
      toast.success(t('providers.testSuccess'))
    } else {
      toast.error(result.error || t('providers.testFailed'))
    }
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('providers.title')">
      <template #actions>
        <button v-if="hasProject" class="btn-primary" @click="openCreate">
          <Plus class="h-4 w-4" /> {{ t('providers.newProvider') }}
        </button>
      </template>
    </PageHeader>

    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <EmptyState v-else-if="!providers.length" :message="t('common.noData')">
      <button class="btn-primary" @click="openCreate">{{ t('providers.newProvider') }}</button>
    </EmptyState>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="p in providers" :key="p.id" class="card flex flex-col p-5">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold capitalize text-gray-900 dark:text-white">{{ p.provider }}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">{{ p.model }}</p>
          </div>
          <ToggleSwitch :model-value="p.enabled" @update:model-value="toggleEnabled(p, $event)" />
        </div>
        <dl class="mt-3 space-y-1 text-xs text-gray-500 dark:text-gray-400">
          <div class="flex justify-between">
            <dt>{{ t('common.priority') }}</dt>
            <dd class="font-medium text-gray-700 dark:text-gray-200">{{ p.priority }}</dd>
          </div>
          <div class="flex justify-between">
            <dt>{{ t('providers.temperature') }}</dt>
            <dd class="font-medium text-gray-700 dark:text-gray-200">{{ p.temperature }}</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="shrink-0 whitespace-nowrap">{{ t('providers.apiKey') }}</dt>
            <dd class="min-w-0 truncate font-mono text-gray-700 dark:text-gray-200" :title="p.api_key_masked || ''">{{ p.api_key_masked || '—' }}</dd>
          </div>
        </dl>
        <div class="mt-4 flex items-center gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
          <button class="btn-ghost flex-1 text-sm" @click="openEdit(p)">
            <Pencil class="h-4 w-4" /> {{ t('common.edit') }}
          </button>
          <button class="btn-ghost text-red-600" @click="confirmDelete(p.id)">
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>

    <BaseModal v-model="showForm" :title="editing ? t('providers.editProvider') : t('providers.newProvider')">
      <form class="space-y-4" @submit.prevent="save">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">{{ t('providers.provider') }}</label>
            <select v-model="form.provider" class="input">
              <option v-for="pt in PROVIDER_TYPES" :key="pt" :value="pt">{{ pt }}</option>
            </select>
          </div>
          <div>
            <div class="flex items-center justify-between">
              <label class="label">{{ t('providers.model') }}</label>
              <button
                type="button"
                class="flex items-center gap-1 text-xs font-medium text-primary-600 hover:underline disabled:opacity-50 dark:text-primary-400"
                :disabled="loadingModels"
                @click="fetchModels(false)"
              >
                <component :is="loadingModels ? Loader2 : RefreshCw" class="h-3 w-3" :class="loadingModels ? 'animate-spin' : ''" />
                {{ t('providers.fetchModels') }}
              </button>
            </div>
            <select v-if="availableModels.length" v-model="form.model" required class="input">
              <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
            </select>
            <input
              v-else
              v-model="form.model"
              required
              class="input"
              autocomplete="off"
            />
          </div>
        </div>

        <div>
          <label class="label">{{ t('providers.baseUrl') }} ({{ t('common.optional') }})</label>
          <input
            v-model="form.base_url"
            class="input"
            placeholder="https://..."
            autocomplete="off"
          />
        </div>

        <div>
          <label class="label">{{ t('providers.apiKey') }} ({{ t('common.optional') }})</label>
          <input
            v-model="form.api_key"
            type="password"
            class="input"
            :placeholder="existingMask || ''"
            autocomplete="new-password"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">{{ t('providers.temperature') }}: {{ form.temperature }}</label>
            <input v-model.number="form.temperature" type="range" min="0" max="2" step="0.1" class="w-full" />
          </div>
          <div>
            <label class="label">{{ t('providers.topP') }}: {{ form.top_p }}</label>
            <input v-model.number="form.top_p" type="range" min="0" max="1" step="0.05" class="w-full" />
          </div>
        </div>

        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="label">{{ t('providers.maxTokens') }}</label>
            <input v-model.number="form.max_tokens" type="number" min="1" class="input" />
          </div>
          <div>
            <label class="label">{{ t('providers.timeout') }}</label>
            <input v-model.number="form.timeout_seconds" type="number" min="1" class="input" />
          </div>
          <div>
            <label class="label">{{ t('common.priority') }}</label>
            <input v-model.number="form.priority" type="number" class="input" />
          </div>
        </div>

        <div>
          <label class="label">{{ t('providers.systemPrompt') }} ({{ t('common.optional') }})</label>
          <textarea v-model="form.system_prompt" rows="3" class="input"></textarea>
        </div>

        <div class="flex items-center gap-2">
          <ToggleSwitch v-model="form.enabled" />
          <span class="text-sm text-gray-600 dark:text-gray-300">{{ t('common.enabled') }}</span>
        </div>

        <div v-if="form.provider === 'gemini'" class="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
          <div class="flex items-center gap-2">
            <ToggleSwitch v-model="form.grounding_enabled" />
            <span class="text-sm text-gray-600 dark:text-gray-300">{{ t('providers.grounding') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ t('providers.groundingHint') }}</p>
        </div>

        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
          <label class="label">{{ t('providers.testPrompt') }}</label>
          <input v-model="testPrompt" class="input" />
          <button type="button" class="btn-secondary mt-2" :disabled="testing" @click="runTest">
            <component :is="testing ? Loader2 : Zap" class="h-4 w-4" :class="testing ? 'animate-spin' : ''" />
            {{ t('providers.testConnection') }}
          </button>
          <div
            v-if="testResult"
            class="mt-3 rounded-md p-2 text-sm"
            :class="testResult.success
              ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
              : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'"
          >
            <p v-if="testResult.success">
              {{ t('providers.latency') }}: {{ testResult.latency_ms }} ms
            </p>
            <p v-if="testResult.success && testResult.output" class="mt-1 whitespace-pre-wrap">
              {{ testResult.output }}
            </p>
            <p v-if="!testResult.success">{{ testResult.error || t('providers.testFailed') }}</p>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-secondary" @click="showForm = false">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ t('common.save') }}</button>
        </div>
      </form>
    </BaseModal>

    <ConfirmDialog v-model="showConfirm" @confirm="doDelete" />
  </div>
</template>
