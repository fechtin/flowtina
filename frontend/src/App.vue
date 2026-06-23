<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import ToastContainer from '@/components/ui/ToastContainer.vue'

// Initialize settings store early so theme/language apply on boot.
useSettingsStore()
</script>

<template>
  <RouterView />
  <ToastContainer />
</template>
