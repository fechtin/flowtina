<script setup lang="ts">
import { X } from 'lucide-vue-next'

defineProps<{ modelValue: boolean; title?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @keydown.esc="close"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close" />
        <div
          class="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-800 dark:bg-gray-900"
        >
          <div
            class="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-5 py-4 dark:border-gray-800 dark:bg-gray-900"
          >
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">{{ title }}</h3>
            <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" @click="close">
              <X class="h-5 w-5" />
            </button>
          </div>
          <div class="p-5">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
