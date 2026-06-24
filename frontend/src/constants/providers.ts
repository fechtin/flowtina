import type { ProviderType } from '@/types'

// Single source of truth for the provider selector, shared by the Providers
// page and global Settings so both stay in sync.
export const PROVIDER_TYPES: ProviderType[] = [
  'openai',
  'groq',
  'gemini',
  'claude',
  'openrouter',
  'deepseek',
  'ollama',
  'lmstudio',
  'vllm',
  'custom',
]

// Suggested models per provider. The model field stays editable (or falls back
// to free text), so providers with arbitrary model names (ollama, vllm, custom)
// still accept any value.
export const MODEL_PRESETS: Partial<Record<ProviderType, string[]>> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'o3-mini'],
  groq: [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'mixtral-8x7b-32768',
    'gemma2-9b-it',
  ],
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  claude: [
    'claude-sonnet-4-20250514',
    'claude-3-5-sonnet-latest',
    'claude-3-5-haiku-latest',
  ],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
}
