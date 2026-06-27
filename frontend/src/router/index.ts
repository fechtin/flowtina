import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/DashboardLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('@/pages/DashboardPage.vue') },
      { path: 'projects', name: 'projects', component: () => import('@/pages/ProjectsPage.vue') },
      { path: 'providers', name: 'providers', component: () => import('@/pages/ProvidersPage.vue') },
      { path: 'prompts', name: 'prompts', component: () => import('@/pages/PromptsPage.vue') },
      { path: 'sources', name: 'sources', component: () => import('@/pages/SourcesPage.vue') },
      { path: 'jobs', name: 'jobs', component: () => import('@/pages/JobsPage.vue') },
      { path: 'posts', name: 'posts', component: () => import('@/pages/PostsPage.vue') },
      { path: 'facebook', name: 'facebook', component: () => import('@/pages/FacebookPage.vue') },
      { path: 'telegram', name: 'telegram', component: () => import('@/pages/TelegramPage.vue') },
      { path: 'growth', name: 'growth', component: () => import('@/pages/GrowthPage.vue') },
      { path: 'video', name: 'video', component: () => import('@/pages/VideoPage.vue') },
      { path: 'logs', name: 'logs', component: () => import('@/pages/LogsPage.vue') },
      { path: 'settings', name: 'settings', component: () => import('@/pages/SettingsPage.vue') },
      { path: 'profile', name: 'profile', component: () => import('@/pages/ProfilePage.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { requiresAuth: false },
    children: [
      { path: 'login', name: 'login', component: () => import('@/pages/LoginPage.vue') },
      { path: 'register', name: 'register', component: () => import('@/pages/RegisterPage.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
