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
const testMessage = ref('Hello from Flowtina')

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
          <input v-model="form.bot_token" type="password" class="input" />
        </div>
        <div>
          <label class="label">{{ t('telegram.chatId') }}</label>
          <input v-model="form.chat_id" class="input" />
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
