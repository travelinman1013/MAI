// Re-export from stores for backwards compatibility
export type { Message, ChatSession } from '@/stores/chatStore'

// LLM provider type
export type LLMProvider = 'openai' | 'lmstudio' | 'ollama' | 'llamacpp' | 'auto'

export interface Model {
  id: string
  name: string
  provider?: string
}

export interface AgentInfo {
  name: string
  description: string
  capabilities?: string[]
}

export interface LLMStatus {
  connected: boolean
  model: string | null
  provider: LLMProvider
  availableProviders?: LLMProvider[]
  error?: string | null
  metadata?: Record<string, unknown>
}

// Provider config interface
export interface ProviderConfig {
  type: LLMProvider
  baseUrl: string
  modelName?: string
}

// Provider status interface
export interface ProviderStatus {
  name: LLMProvider
  connected: boolean
  model: string | null
  error: string | null
  baseUrl: string | null
}
