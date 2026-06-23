<script setup lang="ts">
import { computed } from 'vue'
import type { PostStatus, LogLevel } from '@/types'

const props = defineProps<{ status: PostStatus | LogLevel | string; label?: string }>()

const classMap: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  scheduled: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  published: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  archived: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
  debug: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  info: 'bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  error: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  critical: 'bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const cls = computed(() => classMap[props.status] ?? classMap.draft)
</script>

<template>
  <span class="badge" :class="cls">{{ label ?? status }}</span>
</template>
