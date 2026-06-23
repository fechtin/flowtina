<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
defineProps<{ label?: string }>()
</script>

<template>
  <div class="flex items-center justify-center gap-2 py-12 text-gray-400">
    <Loader2 class="h-5 w-5 animate-spin" />
    <span v-if="label" class="text-sm">{{ label }}</span>
  </div>
</template>
