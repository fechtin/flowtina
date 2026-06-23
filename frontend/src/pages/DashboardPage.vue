<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  FileText,
  CheckCircle2,
  XCircle,
  Percent,
  DollarSign,
  Coins,
} from 'lucide-vue-next'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import LineChart from '@/components/ui/LineChart.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import NoProjectNotice from '@/components/ui/NoProjectNotice.vue'
import { dashboardService } from '@/services'
import { useCurrentProject } from '@/composables/useCurrentProject'
import { extractErrorMessage } from '@/services/http'
import { useToastStore } from '@/stores/toast'
import { formatCurrency, formatNumber, formatPercent, truncate } from '@/utils/format'
import type { DashboardCharts, DashboardStats, Post } from '@/types'

const { t } = useI18n()
const toast = useToastStore()
const { projectId, hasProject } = useCurrentProject()

const loading = ref(false)
const stats = ref<DashboardStats | null>(null)
const charts = ref<DashboardCharts>({ labels: [], posts: [] })
const recent = ref<Post[]>([])

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    const pid = projectId.value
    const [s, c, r] = await Promise.all([
      dashboardService.stats(pid),
      dashboardService.charts(pid),
      dashboardService.recentPosts(pid),
    ])
    stats.value = s
    charts.value = c
    recent.value = r
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)
</script>

<template>
  <div>
    <PageHeader :title="t('dashboard.title')" />
    <NoProjectNotice v-if="!hasProject" />
    <LoadingSpinner v-else-if="loading" :label="t('common.loading')" />
    <template v-else>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          :label="t('dashboard.postsToday')"
          :value="formatNumber(stats?.posts_today ?? 0)"
          :icon="FileText"
        />
        <StatCard
          :label="t('dashboard.publishedToday')"
          :value="formatNumber(stats?.published_today ?? 0)"
          :icon="CheckCircle2"
          accent="bg-green-50 text-green-600 dark:bg-green-950 dark:text-green-300"
        />
        <StatCard
          :label="t('dashboard.failedToday')"
          :value="formatNumber(stats?.failed_today ?? 0)"
          :icon="XCircle"
          accent="bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300"
        />
        <StatCard
          :label="t('dashboard.successRate')"
          :value="formatPercent(stats?.success_rate ?? 0)"
          :icon="Percent"
          accent="bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-300"
        />
        <StatCard
          :label="t('dashboard.aiCost')"
          :value="formatCurrency(stats?.total_cost ?? 0)"
          :icon="DollarSign"
          accent="bg-purple-50 text-purple-600 dark:bg-purple-950 dark:text-purple-300"
        />
        <StatCard
          :label="t('dashboard.tokens')"
          :value="formatNumber(stats?.total_tokens ?? 0)"
          :icon="Coins"
          accent="bg-teal-50 text-teal-600 dark:bg-teal-950 dark:text-teal-300"
        />
      </div>

      <div class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="card p-5 lg:col-span-2">
          <h2 class="mb-4 text-base font-semibold text-gray-900 dark:text-white">
            {{ t('dashboard.postsPerDay') }}
          </h2>
          <LineChart
            v-if="charts.labels.length"
            :labels="charts.labels"
            :values="charts.posts"
            :name="t('nav.posts')"
          />
          <EmptyState v-else :message="t('common.noData')" />
        </div>

        <div class="card p-5">
          <h2 class="mb-4 text-base font-semibold text-gray-900 dark:text-white">
            {{ t('dashboard.recentPosts') }}
          </h2>
          <EmptyState v-if="!recent.length" :message="t('common.noData')" />
          <ul v-else class="space-y-3">
            <li
              v-for="p in recent"
              :key="p.id"
              class="flex items-start justify-between gap-2 border-b border-gray-100 pb-3 last:border-0 dark:border-gray-800"
            >
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                  {{ p.title || truncate(p.content, 40) }}
                </p>
                <p class="truncate text-xs text-gray-400">{{ truncate(p.content, 60) }}</p>
              </div>
              <StatusBadge :status="p.status" :label="t(`posts.${p.status}`)" />
            </li>
          </ul>
          <RouterLink to="/posts" class="mt-4 block text-center text-sm font-medium text-primary-600 hover:underline">
            {{ t('nav.posts') }}
          </RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>
