import { http } from './http'
import type {
  AppSettings,
  AppSettingsUpdate,
  AuthTokens,
  DashboardCharts,
  DashboardStats,
  FacebookPage,
  FacebookDiscoveredPage,
  Job,
  JobHistory,
  Keyword,
  LogEntry,
  Post,
  PostStatus,
  Project,
  PromptTemplate,
  Provider,
  ProviderPayload,
  ProviderTestResult,
  RssSource,
  SystemPrompt,
  TelegramConfig,
  Topic,
  User,
} from '@/types'

// ---------- Auth ----------
export const authService = {
  register: (payload: { email: string; password: string; name: string }) =>
    http.post<unknown, AuthTokens>('/auth/register', payload),
  login: (payload: { email: string; password: string }) =>
    http.post<unknown, AuthTokens>('/auth/login', payload),
  logout: () => http.post<unknown, void>('/auth/logout'),
  changePassword: (payload: { old_password: string; new_password: string }) =>
    http.post<unknown, void>('/auth/change-password', payload),
  getProfile: () => http.get<unknown, User>('/auth/profile'),
  updateProfile: (payload: Partial<Pick<User, 'name' | 'language' | 'timezone' | 'avatar'>>) =>
    http.put<unknown, User>('/auth/profile', payload),
}

// ---------- Projects ----------
export const projectService = {
  list: () => http.get<unknown, Project[]>('/projects'),
  create: (payload: { name: string; description: string }) =>
    http.post<unknown, Project>('/projects', payload),
  get: (id: string) => http.get<unknown, Project>(`/projects/${id}`),
  update: (id: string, payload: Partial<{ name: string; description: string; active: boolean }>) =>
    http.put<unknown, Project>(`/projects/${id}`, payload),
  remove: (id: string) => http.delete<unknown, void>(`/projects/${id}`),
}

// ---------- Providers ----------
export const providerService = {
  list: (pid: string) => http.get<unknown, Provider[]>(`/projects/${pid}/providers`),
  create: (pid: string, payload: ProviderPayload) =>
    http.post<unknown, Provider>(`/projects/${pid}/providers`, payload),
  update: (id: string, payload: Partial<ProviderPayload>) =>
    http.put<unknown, Provider>(`/providers/${id}`, payload),
  remove: (id: string) => http.delete<unknown, void>(`/providers/${id}`),
  test: (payload: {
    provider: string
    base_url?: string
    api_key?: string
    model: string
    prompt: string
  }) => http.post<unknown, ProviderTestResult>('/providers/test', payload),
  listModels: (payload: { provider: string; base_url?: string; api_key?: string }) =>
    http.post<unknown, string[]>('/providers/models', payload),
}

// ---------- Prompts ----------
export const promptService = {
  listTemplates: (pid: string) => http.get<unknown, PromptTemplate[]>(`/projects/${pid}/prompts`),
  createTemplate: (
    pid: string,
    payload: Omit<PromptTemplate, 'id' | 'project_id' | 'version' | 'active'> &
      Partial<Pick<PromptTemplate, 'active'>>,
  ) => http.post<unknown, PromptTemplate>(`/projects/${pid}/prompts`, payload),
  listSystem: (pid: string) => http.get<unknown, SystemPrompt[]>(`/projects/${pid}/system-prompts`),
  createSystem: (pid: string, payload: { name: string; content: string }) =>
    http.post<unknown, SystemPrompt>(`/projects/${pid}/system-prompts`, payload),
  updateSystem: (
    id: string,
    payload: Partial<Pick<SystemPrompt, 'name' | 'content' | 'active'>>,
  ) => http.put<unknown, SystemPrompt>(`/system-prompts/${id}`, payload),
  removeSystem: (id: string) => http.delete<unknown, void>(`/system-prompts/${id}`),
  update: (id: string, payload: Partial<PromptTemplate> & Partial<SystemPrompt>) =>
    http.put<unknown, PromptTemplate>(`/prompts/${id}`, payload),
  remove: (id: string) => http.delete<unknown, void>(`/prompts/${id}`),
  render: (payload: { template: string; variables: Record<string, unknown> }) =>
    http.post<unknown, { rendered: string }>('/prompts/render', payload),
}

// ---------- Sources ----------
export const sourceService = {
  listTopics: (pid: string) => http.get<unknown, Topic[]>(`/projects/${pid}/topics`),
  addTopic: (pid: string, payload: { topic: string; priority: number }) =>
    http.post<unknown, Topic>(`/projects/${pid}/topics`, payload),
  removeTopic: (id: string) => http.delete<unknown, void>(`/topics/${id}`),
  listRss: (pid: string) => http.get<unknown, RssSource[]>(`/projects/${pid}/rss`),
  addRss: (pid: string, payload: { url: string }) =>
    http.post<unknown, RssSource>(`/projects/${pid}/rss`, payload),
  removeRss: (id: string) => http.delete<unknown, void>(`/rss/${id}`),
  listKeywords: (pid: string) => http.get<unknown, Keyword[]>(`/projects/${pid}/keywords`),
  addKeyword: (pid: string, payload: { keyword: string; priority: number }) =>
    http.post<unknown, Keyword>(`/projects/${pid}/keywords`, payload),
  removeKeyword: (id: string) => http.delete<unknown, void>(`/keywords/${id}`),
  sync: (pid: string) => http.post<unknown, { collected: number }>(`/projects/${pid}/sources/sync`),
}

// ---------- Posts ----------
export const postService = {
  list: (
    pid: string,
    params: { status?: PostStatus; language?: string; keyword?: string; limit?: number; offset?: number } = {},
  ) => http.get<unknown, Post[]>(`/projects/${pid}/posts`, { params }),
  create: (
    pid: string,
    payload: {
      title?: string
      content: string
      hashtags?: string
      language: string
      status: PostStatus
      image_url?: string | null
    },
  ) => http.post<unknown, Post>(`/projects/${pid}/posts`, payload),
  generate: (
    pid: string,
    payload: { topic?: string; content_type: string; language: string; auto_publish: boolean },
  ) => http.post<unknown, Post[]>(`/projects/${pid}/posts/generate`, payload),
  get: (id: string) => http.get<unknown, Post>(`/posts/${id}`),
  update: (id: string, payload: Partial<Post>) => http.put<unknown, Post>(`/posts/${id}`, payload),
  remove: (id: string) => http.delete<unknown, void>(`/posts/${id}`),
  publish: (id: string, pageId?: string) =>
    http.post<unknown, Post>(`/posts/${id}/publish`, null, {
      params: pageId ? { page_id: pageId } : {},
    }),
  retry: (id: string, pageId?: string) =>
    http.post<unknown, Post>(`/posts/${id}/retry`, null, {
      params: pageId ? { page_id: pageId } : {},
    }),
  uploadImage: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    // Axios 1.x appends the multipart boundary automatically for FormData.
    return http.post<unknown, Post>(`/posts/${id}/image`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  removeImage: (id: string) => http.delete<unknown, Post>(`/posts/${id}/image`),
}

// ---------- Jobs ----------
export const jobService = {
  list: (pid: string) => http.get<unknown, Job[]>(`/projects/${pid}/jobs`),
  create: (
    pid: string,
    payload: {
      name: string
      job_type: string
      cron_expression?: string | null
      interval_seconds?: number | null
      timezone: string
      enabled: boolean
      content_type?: string
      language?: string
      auto_publish?: boolean
      require_approval?: boolean
      facebook_page_id?: string | null
    },
  ) => http.post<unknown, Job>(`/projects/${pid}/jobs`, payload),
  update: (id: string, payload: Partial<Job>) => http.put<unknown, Job>(`/jobs/${id}`, payload),
  remove: (id: string) => http.delete<unknown, void>(`/jobs/${id}`),
  run: (id: string) => http.post<unknown, void>(`/jobs/${id}/run`),
  history: (id: string) => http.get<unknown, JobHistory[]>(`/jobs/${id}/history`),
}

// ---------- Facebook ----------
export const facebookService = {
  listPages: (pid: string) => http.get<unknown, FacebookPage[]>(`/projects/${pid}/facebook/pages`),
  addPage: (pid: string, payload: { page_name: string; page_id: string; access_token: string }) =>
    http.post<unknown, FacebookPage>(`/projects/${pid}/facebook/pages`, payload),
  removePage: (id: string) => http.delete<unknown, void>(`/facebook/pages/${id}`),
  discoverPages: (pid: string, token?: string) =>
    http.post<unknown, FacebookDiscoveredPage[]>(`/projects/${pid}/facebook/discover`, {
      token: token || null,
    }),
  importPages: (pid: string, token?: string, pageIds?: string[]) =>
    http.post<unknown, FacebookPage[]>(`/projects/${pid}/facebook/import`, {
      token: token || null,
      page_ids: pageIds ?? null,
    }),
}

// ---------- Telegram ----------
export const telegramService = {
  getConfig: (pid: string) => http.get<unknown, TelegramConfig>(`/projects/${pid}/telegram/config`),
  saveConfig: (pid: string, payload: { bot_token: string; chat_id: string; enabled: boolean }) =>
    http.post<unknown, TelegramConfig>(`/projects/${pid}/telegram/config`, payload),
  test: (pid: string, payload: { message: string }) =>
    http.post<unknown, { success: boolean }>(`/projects/${pid}/telegram/test`, payload),
}

// ---------- Dashboard ----------
export const dashboardService = {
  stats: (pid: string) => http.get<unknown, DashboardStats>(`/projects/${pid}/dashboard/stats`),
  charts: (pid: string) => http.get<unknown, DashboardCharts>(`/projects/${pid}/dashboard/charts`),
  recentPosts: (pid: string) => http.get<unknown, Post[]>(`/projects/${pid}/dashboard/recent-posts`),
}

// ---------- Settings ----------
export const settingsService = {
  get: () => http.get<unknown, AppSettings>('/settings'),
  update: (payload: AppSettingsUpdate) => http.put<unknown, AppSettings>('/settings', payload),
}

// ---------- Logs ----------
export const logService = {
  list: (params: { level?: string; module?: string; limit?: number } = {}) =>
    http.get<unknown, LogEntry[]>('/logs', { params }),
}
