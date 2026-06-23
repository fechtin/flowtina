<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save, Send } from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { telegramService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { useAsync } from '@/composables/useAsync'

const { t } = useI18n()
const { projectId, hasProject } = useCurrentProject()
const { run } = useAsync()

const loading = ref(false)
const form = reactive({ bot_token: '', chat_id: '', enabled: false })
const errors = reactive({ bot_token: '', chat_id: '' })
const testMessage = ref('Hello from Flowtina')

const BOT_TOKEN_RE = /^\d+:[A-Za-z0-9_-]+$/
const CHAT_ID_RE = /^-?\d+$/

function validate(): boolean {
  errors.bot_token = BOT_TOKEN_RE.test(form.bot_token.trim()) ? '' : t('telegram.botTokenInvalid')
  errors.chat_id = CHAT_ID_RE.test(form.chat_id.trim()) ? '' : t('telegram.chatIdInvalid')
  return !errors.bot_token && !errors.chat_id
}

async function load() {
  if (!projectId.value) return
  loading.value = true
  const config = await run(() => telegramService.getConfig(projectId.value!), { silentError: true })
  if (config) {
    form.bot_token = config.bot_token ?? ''
    form.chat_id = config.chat_id ?? ''
    form.enabled = config.enabled ?? false
  }
  loading.value = false
}

onMounted(load)
watch(projectId, load)

async function save() {
  if (!projectId.value) return
  if (!validate()) return
  await run(
    () => telegramService.saveConfig(projectId.value!, { ...form }),
    { successMessage: t('telegram.configSaved') },
  )
}

async function sendTest() {
  if (!projectId.value) return
  await run(
    () => telegramService.test(projectId.value!, { message: testMessage.value }),
    { successMessage: t('telegram.sent') },
  )
}
</script>

<template>
  <div>
    <PageHeader :title="t('telegram.title')" />

    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <div v-else class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <form class="card space-y-4 p-5" @submit.prevent="save">
        <div>
          <label class="label">{{ t('telegram.botToken') }}</label>
          <input
            v-model="form.bot_token"
            type="password"
            class="input"
            :class="{ 'border-red-500 focus:ring-red-500': errors.bot_token }"
            @input="errors.bot_token = ''"
          />
          <p v-if="errors.bot_token" class="mt-1 text-xs text-red-500">{{ errors.bot_token }}</p>
          <p v-else class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ t('telegram.botTokenHint') }}</p>
        </div>
        <div>
          <label class="label">{{ t('telegram.chatId') }}</label>
          <input
            v-model="form.chat_id"
            inputmode="numeric"
            placeholder="123456789"
            class="input"
            :class="{ 'border-red-500 focus:ring-red-500': errors.chat_id }"
            @input="errors.chat_id = ''"
          />
          <p v-if="errors.chat_id" class="mt-1 text-xs text-red-500">{{ errors.chat_id }}</p>
          <p v-else class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ t('telegram.chatIdHint') }}</p>
        </div>
        <div class="flex items-center justify-between">
          <span class="label mb-0">{{ t('common.enabled') }}</span>
          <ToggleSwitch v-model="form.enabled" />
        </div>
        <div class="flex justify-end pt-2">
          <button type="submit" class="btn-primary">
            <Save class="h-4 w-4" /> {{ t('common.save') }}
          </button>
        </div>
      </form>

      <div class="card space-y-4 p-5">
        <h2 class="text-base font-semibold text-gray-900 dark:text-white">
          {{ t('telegram.sendTest') }}
        </h2>
        <div>
          <label class="label">{{ t('telegram.testMessage') }}</label>
          <textarea v-model="testMessage" rows="4" class="input"></textarea>
        </div>
        <div class="flex justify-end">
          <button class="btn-secondary" @click="sendTest">
            <Send class="h-4 w-4" /> {{ t('telegram.sendTest') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
