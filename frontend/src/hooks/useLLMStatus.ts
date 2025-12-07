import { useState, useEffect, useCallback } from 'react'
import { getLLMStatus } from '@/services/api'
import { useSettingsStore } from '@/stores'
import type { LLMStatus, LLMProvider } from '@/types/chat'

interface UseLLMStatusReturn {
  status: LLMStatus
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useLLMStatus(pollInterval = 30000): UseLLMStatusReturn {
  const llmProvider = useSettingsStore((state) => state.llmProvider)
  const [status, setStatus] = useState<LLMStatus>({
    connected: false,
    model: null,
    provider: llmProvider,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setError(null)
      // Pass the selected provider to get status for that specific provider
      const data = await getLLMStatus(llmProvider !== 'auto' ? llmProvider : undefined)
      setStatus({
        connected: data?.connected ?? false,
        model: data?.model_name || data?.model || null,
        provider: (data?.provider as LLMProvider) || llmProvider,
        availableProviders: data?.available_providers as LLMProvider[],
        error: data?.error || null,
        metadata: data?.metadata,
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch LLM status'))
      setStatus(prev => ({ ...prev, connected: false, error: 'Connection failed' }))
    } finally {
      setIsLoading(false)
    }
  }, [llmProvider])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, pollInterval)
    return () => clearInterval(interval)
  }, [fetchStatus, pollInterval])

  return { status, isLoading, error, refresh: fetchStatus }
}
