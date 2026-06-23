<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

const sidebarOpen = ref(false)
const auth = useAuthStore()
const projectStore = useProjectStore()

onMounted(async () => {
  if (!auth.user) {
    try {
      await auth.fetchProfile()
    } catch {
      // Interceptor handles auth failure / redirect.
    }
  }
  if (!projectStore.projects.length) {
    await projectStore.fetchProjects().catch(() => undefined)
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
    <div class="lg:pl-64">
      <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <main class="mx-auto max-w-7xl p-4 sm:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
