<script setup lang="ts">
import { Menu } from 'lucide-vue-next'
import ProjectSwitcher from './ProjectSwitcher.vue'
import ThemeToggle from './ThemeToggle.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

defineEmits<{ toggleSidebar: [] }>()
</script>

<template>
  <header
    class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-200 bg-white/80 px-4 backdrop-blur dark:border-gray-800 dark:bg-gray-900/80"
  >
    <div class="flex items-center gap-3">
      <button
        class="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden"
        @click="$emit('toggleSidebar')"
      >
        <Menu class="h-5 w-5" />
      </button>
      <ProjectSwitcher />
    </div>
    <div class="flex items-center gap-1.5">
      <LanguageSwitcher />
      <ThemeToggle />
      <ProfileMenu />
    </div>
  </header>
</template>
