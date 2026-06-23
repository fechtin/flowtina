<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'

defineProps<{ modelValue: boolean; message?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; confirm: [] }>()
const { t } = useI18n()

function confirm() {
  emit('confirm')
  emit('update:modelValue', false)
}
</script>

<template>
  <BaseModal :model-value="modelValue" :title="t('common.confirm')" @update:model-value="emit('update:modelValue', $event)">
    <div class="flex items-start gap-3">
      <div class="rounded-full bg-red-100 p-2 dark:bg-red-950">
        <AlertTriangle class="h-5 w-5 text-red-600 dark:text-red-400" />
      </div>
      <p class="pt-1 text-sm text-gray-600 dark:text-gray-300">
        {{ message || t('common.confirmDelete') }}
      </p>
    </div>
    <div class="mt-6 flex justify-end gap-2">
      <button class="btn-secondary" @click="emit('update:modelValue', false)">{{ t('common.cancel') }}</button>
      <button class="btn-danger" @click="confirm">{{ t('common.delete') }}</button>
    </div>
  </BaseModal>
</template>
