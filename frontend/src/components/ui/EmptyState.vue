<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
defineProps<{ message?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
    <div class="rounded-full bg-gray-100 p-4 dark:bg-gray-800">
      <Inbox class="h-8 w-8 text-gray-400" />
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400">{{ message }}</p>
    <slot />
  </div>
</template>
