import { useState, useEffect, useCallback } from 'react'
import { getLLMStatus } from '@/services/api'

export interface LLMStatus {
  connected: boolean
  model?: string | null
  error?: string
}

interface UseLLMStatusReturn {
  status: LLMStatus
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useLLMStatus(pollInterval = 30000): UseLLMStatusReturn {
  const [status, setStatus] = useState<LLMStatus>({ connected: false })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setError(null)
      const data = await getLLMStatus()
      setStatus({
        connected: data?.connected ?? false,
        model: data?.model,
        error: undefined,
      })
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch LLM status'))
      setStatus({ connected: false, error: 'Connection failed' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, pollInterval)
    return () => clearInterval(interval)
  }, [fetchStatus, pollInterval])

  return { status, isLoading, error, refresh: fetchStatus }
}
