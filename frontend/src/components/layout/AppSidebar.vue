<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  LayoutDashboard,
  FolderKanban,
  Cpu,
  FileText,
  Rss,
  CalendarClock,
  Newspaper,
  Facebook,
  Send,
  ScrollText,
  Settings,
  X,
  TrendingUp,
  Video,
} from 'lucide-vue-next'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()

const links = [
  { name: 'dashboard', to: '/', icon: LayoutDashboard, label: 'nav.dashboard' },
  { name: 'projects', to: '/projects', icon: FolderKanban, label: 'nav.projects' },
  { name: 'providers', to: '/providers', icon: Cpu, label: 'nav.providers' },
  { name: 'prompts', to: '/prompts', icon: FileText, label: 'nav.prompts' },
  { name: 'sources', to: '/sources', icon: Rss, label: 'nav.sources' },
  { name: 'jobs', to: '/jobs', icon: CalendarClock, label: 'nav.jobs' },
  { name: 'posts', to: '/posts', icon: Newspaper, label: 'nav.posts' },
  { name: 'facebook', to: '/facebook', icon: Facebook, label: 'nav.facebook' },
  { name: 'telegram', to: '/telegram', icon: Send, label: 'nav.telegram' },
  { name: 'growth', to: '/growth', icon: TrendingUp, label: 'nav.growth' },
  { name: 'video', to: '/video', icon: Video, label: 'nav.video' },
  { name: 'logs', to: '/logs', icon: ScrollText, label: 'nav.logs' },
  { name: 'settings', to: '/settings', icon: Settings, label: 'nav.settings' },
]
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-30 bg-black/50 lg:hidden"
    @click="emit('close')"
  />
  <aside
    class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform dark:border-gray-800 dark:bg-gray-900 lg:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="flex h-16 items-center justify-between border-b border-gray-200 px-5 dark:border-gray-800">
      <div class="flex items-center gap-2">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 font-bold text-white">F</div>
        <div>
          <p class="text-sm font-bold text-gray-900 dark:text-white">{{ t('app.name') }}</p>
          <p class="text-[10px] text-gray-400">{{ t('app.tagline') }}</p>
        </div>
      </div>
      <button class="text-gray-400 lg:hidden" @click="emit('close')">
        <X class="h-5 w-5" />
      </button>
    </div>
    <nav class="flex-1 space-y-1 overflow-y-auto p-3">
      <RouterLink
        v-for="link in links"
        :key="link.name"
        :to="link.to"
        class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
        active-class="!bg-primary-50 !text-primary-700 dark:!bg-primary-950 dark:!text-primary-300"
        exact-active-class="!bg-primary-50 !text-primary-700 dark:!bg-primary-950 dark:!text-primary-300"
        @click="emit('close')"
      >
        <component :is="link.icon" class="h-5 w-5" />
        {{ t(link.label) }}
      </RouterLink>
    </nav>
  </aside>
</template>
