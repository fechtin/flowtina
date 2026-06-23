<script setup lang="ts">
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from 'lucide-vue-next'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const icons = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const styles = {
  success: 'border-green-500/30 bg-green-50 text-green-800 dark:bg-green-950/60 dark:text-green-200',
  error: 'border-red-500/30 bg-red-50 text-red-800 dark:bg-red-950/60 dark:text-red-200',
  info: 'border-primary-500/30 bg-primary-50 text-primary-800 dark:bg-primary-950/60 dark:text-primary-200',
  warning: 'border-amber-500/30 bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200',
}
</script>

<template>
  <div class="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="t in toast.toasts"
        :key="t.id"
        class="pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur"
        :class="styles[t.type]"
      >
        <component :is="icons[t.type]" class="mt-0.5 h-5 w-5 shrink-0" />
        <p class="flex-1 text-sm">{{ t.message }}</p>
        <button class="shrink-0 opacity-60 hover:opacity-100" @click="toast.dismiss(t.id)">
          <X class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
