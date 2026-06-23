<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ label: string; value: string | number; icon: Component; accent?: string }>()
</script>

<template>
  <div class="card flex items-center gap-4 p-5">
    <div
      class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl"
      :class="accent ?? 'bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-300'"
    >
      <component :is="icon" class="h-6 w-6" />
    </div>
    <div class="min-w-0">
      <p class="truncate text-sm text-gray-500 dark:text-gray-400">{{ label }}</p>
      <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ value }}</p>
    </div>
  </div>
</template>
