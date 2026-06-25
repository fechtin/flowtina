export interface ApiSuccess<T> {
  success: true
  message: string
  data: T
}

export interface ApiError {
  success: false
  error: {
    code: string
    message: string
  }
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export interface User {
  id: string
  email: string
  name: string
  language: string
  timezone: string
  is_admin: boolean
  active: boolean
  avatar?: string | null
}

export interface Project {
  id: string
  user_id: string
  name: string
  description: string
  active: boolean
  created_at: string
  updated_at: string
}

export type ProviderType =
  | 'openai'
  | 'groq'
  | 'gemini'
  | 'claude'
  | 'openrouter'
  | 'deepseek'
  | 'ollama'
  | 'lmstudio'
  | 'vllm'
  | 'custom'

export interface Provider {
  id: string
  project_id: string
  provider: ProviderType
  base_url?: string | null
  api_key_masked?: string | null
  model: string
  temperature: number
  top_p: number
  max_tokens: number
  timeout_seconds: number
  system_prompt?: string | null
  priority: number
  enabled: boolean
  grounding_enabled?: boolean
  created_at?: string
  updated_at?: string
}

export interface ProviderPayload {
  provider: ProviderType
  base_url?: string
  api_key?: string
  model: string
  temperature: number
  top_p: number
  max_tokens: number
  timeout_seconds: number
  system_prompt?: string
  priority: number
  enabled: boolean
  grounding_enabled: boolean
}

export interface ProviderTestResult {
  success: boolean
  latency_ms: number
  output?: string
  error?: string
}

export interface PromptTemplate {
  id: string
  project_id?: string
  name: string
  type: string
  template: string
  language: string
  version: number
  active: boolean
}

export interface SystemPrompt {
  id: string
  project_id?: string
  name: string
  content: string
  version: number
  active: boolean
}

export interface Topic {
  id: string
  project_id?: string
  topic: string
  priority: number
}

export interface RssSource {
  id: string
  project_id?: string
  url: string
}

export interface Keyword {
  id: string
  project_id?: string
  keyword: string
  priority: number
}

export type PostStatus =
  | 'draft'
  | 'pending_approval'
  | 'scheduled'
  | 'published'
  | 'failed'
  | 'archived'

export interface Post {
  id: string
  project_id: string
  title: string
  content: string
  hashtags: string | null
  language: string
  status: PostStatus
  quality_score: number
  publish_at?: string | null
  published_at?: string | null
  created_by_ai: boolean
  version: number
  error_message?: string | null
  facebook_page_id?: string | null
  image_url?: string | null
  has_uploaded_image?: boolean
  created_at: string
  updated_at: string
}

export interface Job {
  id: string
  project_id: string
  name: string
  job_type: string
  cron_expression?: string | null
  interval_seconds?: number | null
  timezone: string
  enabled: boolean
  content_type: string
  language: string
  auto_publish: boolean
  require_approval: boolean
  facebook_page_id?: string | null
  last_run_at?: string | null
  next_run_at?: string | null
}

export interface JobHistory {
  id: string
  job_id: string
  status: string
  started_at: string
  finished_at?: string | null
  message?: string | null
}

export interface FacebookPage {
  id: string
  project_id?: string
  page_name: string
  page_id: string
  access_token?: string
  instagram_user_id?: string | null
  instagram_username?: string | null
  publish_facebook?: boolean
  publish_instagram?: boolean
  auto_like_comments?: boolean
  auto_reply_comments?: boolean
  auto_reply_messages?: boolean
  reply_persona?: string | null
  engage_interval_minutes?: number
  engage_max_actions?: number
  last_engaged_at?: string | null
}

export interface FacebookPlatformUpdate {
  publish_facebook?: boolean
  publish_instagram?: boolean
}

export interface FacebookDiscoveredPage {
  page_id: string
  page_name: string
  already_connected: boolean
}

export interface FacebookEngagementUpdate {
  auto_like_comments?: boolean
  auto_reply_comments?: boolean
  auto_reply_messages?: boolean
  reply_persona?: string | null
  engage_interval_minutes?: number
  engage_max_actions?: number
}

export interface FacebookComment {
  id: string
  page_id: string
  facebook_post_id: string
  comment_id: string
  commenter_name?: string | null
  message?: string | null
  liked: boolean
  replied: boolean
  reply_text?: string | null
  status: string
  error_message?: string | null
  processed_at?: string | null
  created_at?: string
}

export interface TelegramConfig {
  id?: string
  project_id?: string
  bot_token: string
  chat_id: string
  enabled: boolean
}

export interface DashboardStats {
  posts_today: number
  published_today: number
  failed_today: number
  success_rate: number
  total_posts: number
  total_tokens: number
  total_cost: number
  facebook_pages: number
  active_jobs: number
}

export interface DashboardCharts {
  labels: string[]
  posts: number[]
}

export interface AppSettings {
  theme: string
  language: string
  timezone: string
  default_provider: string
  default_model: string
  default_base_url?: string | null
  daily_budget: number
  retry_count: number
  random_delay_seconds: number
  telegram_chat_id?: string | null
  telegram_enabled?: boolean
  // Read-only flags from the API indicating a secret is stored (secrets are never returned).
  default_api_key_set?: boolean
  telegram_bot_token_set?: boolean
}

// Write-only secrets sent on save; only included when the user types a new value.
export interface AppSettingsUpdate extends Partial<AppSettings> {
  default_api_key?: string
  telegram_bot_token?: string
}

export type LogLevel = 'debug' | 'info' | 'warning' | 'error' | 'critical'

export interface LogEntry {
  id: string
  level: LogLevel
  module: string
  message: string
  created_at: string
}
