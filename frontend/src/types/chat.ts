export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  images?: string[]
}

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messages: Message[]
}

export interface Model {
  id: string
  name: string
  provider: string
}

export interface AgentInfo {
  name: string
  description: string
  capabilities: string[]
}
