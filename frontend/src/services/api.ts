const API_BASE = '/api/v1'

export interface StreamChatOptions {
  agentName?: string
  sessionId?: string
  images?: string[]
}

export async function streamChat(
  message: string,
  onChunk: (chunk: string) => void,
  options: StreamChatOptions = {}
): Promise<void> {
  const { agentName = 'chat', sessionId, images } = options

  const response = await fetch(`${API_BASE}/agents/stream/${agentName}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      images,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value, { stream: true })
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)
          if (parsed.content) {
            onChunk(parsed.content)
          }
        } catch {
          // If not JSON, treat as plain text chunk
          if (data.trim()) {
            onChunk(data)
          }
        }
      }
    }
  }
}

export async function getAgents(): Promise<{ name: string; description: string }[]> {
  const response = await fetch(`${API_BASE}/agents/`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  const data = await response.json()
  // Backend returns { success, agents, count } - extract the array
  return Array.isArray(data) ? data : (data.agents || [])
}

export async function getModels(): Promise<{ id: string; name: string }[]> {
  const response = await fetch(`${API_BASE}/models/`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export async function getLLMStatus(): Promise<{ connected: boolean; model: string | null }> {
  const response = await fetch(`${API_BASE}/agents/llm-status`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export async function getConversationHistory(
  sessionId: string
): Promise<{ messages: { role: string; content: string }[] }> {
  const response = await fetch(`${API_BASE}/agents/history/${sessionId}`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export async function clearConversationHistory(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/agents/history/${sessionId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
}
