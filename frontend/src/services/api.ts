import { useSettingsStore } from '@/stores'

// ============================================================================
// Types
// ============================================================================

export interface AgentRunRequest {
  user_input: string
  session_id?: string
  user_id?: string
  images?: string[]
  config?: Record<string, unknown>
}

export interface AgentRunResponse {
  success: boolean
  agent_name: string
  session_id?: string
  result: {
    data: {
      role: string
      content: string
    }
  }
  execution_time_ms: number
}

export interface AgentStreamChunk {
  content: string
  done: boolean
}

export interface LLMStatusResponse {
  provider: string
  connected: boolean
  model?: string | null
  model_name?: string | null
  error?: string | null
  available_providers?: string[]
  metadata?: Record<string, unknown>
}

export interface StreamChatOptions {
  agentName?: string
  sessionId?: string
  images?: string[]
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the API base URL from settings store
 * Handles both relative URLs (proxied) and absolute URLs
 */
function getApiBaseUrl(): string {
  const { apiBaseUrl } = useSettingsStore.getState()
  // Handle relative URLs
  if (apiBaseUrl.startsWith('/')) {
    return `${window.location.origin}${apiBaseUrl}`
  }
  return apiBaseUrl
}

// ============================================================================
// Agent Execution API
// ============================================================================

/**
 * Non-streaming agent execution
 * @param agentName - Name of the agent to run
 * @param request - Agent execution request
 * @returns Agent response with result
 */
export async function runAgent(
  agentName: string,
  request: AgentRunRequest
): Promise<AgentRunResponse> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/agents/run/${agentName}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }))
    throw new Error(error.detail?.message || error.message || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Streaming agent execution with SSE (async generator)
 * @param agentName - Name of the agent to run
 * @param request - Agent execution request
 * @yields Stream chunks with content and done flag
 */
export async function* streamAgent(
  agentName: string,
  request: AgentRunRequest
): AsyncGenerator<AgentStreamChunk, void, unknown> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/agents/stream/${agentName}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }))
    throw new Error(error.detail?.message || error.message || `HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data && data !== '[DONE]') {
            try {
              const chunk: AgentStreamChunk = JSON.parse(data)
              yield chunk
              if (chunk.done) return
            } catch {
              // If not valid JSON but has content, yield as plain text
              if (data.trim()) {
                yield { content: data, done: false }
              }
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Legacy callback-based streaming for backward compatibility
 * @deprecated Use streamAgent async generator instead
 */
export async function streamChat(
  message: string,
  onChunk: (chunk: string) => void,
  options: StreamChatOptions = {}
): Promise<void> {
  const { agentName = 'chat_agent', sessionId, images } = options

  const request: AgentRunRequest = {
    user_input: message,
    session_id: sessionId,
    images,
  }

  for await (const chunk of streamAgent(agentName, request)) {
    if (chunk.content) {
      onChunk(chunk.content)
    }
  }
}

// ============================================================================
// LLM Status API
// ============================================================================

/**
 * Get LLM provider status
 * @param provider - Optional provider to check (e.g., 'mlx', 'lmstudio', 'ollama')
 * @returns LLM status with connection state and available providers
 */
export async function getLLMStatus(provider?: string): Promise<LLMStatusResponse> {
  const baseUrl = getApiBaseUrl()
  const url = provider
    ? `${baseUrl}/agents/llm-status?provider=${encodeURIComponent(provider)}`
    : `${baseUrl}/agents/llm-status`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  return response.json()
}

// ============================================================================
// Agents API
// ============================================================================

/**
 * Get list of available agents
 * @returns Array of agent info objects
 */
export async function getAgents(): Promise<{ name: string; description: string }[]> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/agents/`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  const data = await response.json()
  // Backend returns { success, agents, count } - extract the array
  return Array.isArray(data) ? data : (data.agents || [])
}

// ============================================================================
// Models API
// ============================================================================

/**
 * Get list of available models
 * @returns Array of model info objects
 */
export async function getModels(): Promise<{ id: string; name: string }[]> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/models/`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

// ============================================================================
// Conversation History API
// ============================================================================

/**
 * Get conversation history for a session
 * @param sessionId - Session identifier
 * @returns Conversation history with messages
 */
export async function getConversationHistory(
  sessionId: string
): Promise<{ messages: { role: string; content: string }[] }> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/agents/history/${sessionId}`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * Clear conversation history for a session
 * @param sessionId - Session identifier
 */
export async function clearConversationHistory(sessionId: string): Promise<void> {
  const baseUrl = getApiBaseUrl()
  const response = await fetch(`${baseUrl}/agents/history/${sessionId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
}
