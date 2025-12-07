// Re-export from stores for backwards compatibility
export type { Message, ChatSession } from '@/stores/chatStore'

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
}
